"""GraphRAG query endpoint — compares flat search vs graph-aware search."""

import os
import json
from fastapi import APIRouter
from openai import AzureOpenAI
from dotenv import load_dotenv
from pathlib import Path

from backend.graph.neo4j_client import neo4j_client
from backend.models.schemas import QueryRequest, QueryResponse, ProductRecommendation

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

router = APIRouter()


def get_azure_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def extract_query_intent(query: str) -> dict:
    """Use LLM to extract intent entities from a natural language query."""
    client = get_azure_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a query parser for a herbal tea store. Extract structured intent from the user's query. "
                    "Return ONLY a JSON object with these fields (use empty lists if not applicable):\n"
                    '{"health_concerns": [], "ingredients": [], "occasions": [], "use_cases": [], "price_preference": null}'
                ),
            },
            {"role": "user", "content": query},
        ],
        temperature=0.0,
        max_tokens=300,
    )

    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"health_concerns": [], "ingredients": [], "occasions": [], "use_cases": []}


def flat_search(query: str) -> list[ProductRecommendation]:
    """
    Simulated flat RAG search — basic text matching against product titles and descriptions.
    This represents what a standard vector search returns (simplified for demo).
    """
    query_lower = query.lower()
    keywords = query_lower.split()

    results = neo4j_client.run_query(
        """
        MATCH (p:Product)
        RETURN p.title AS title, p.price AS price, p.url AS url,
               p.image_url AS image_url, p.description AS description,
               p.tags AS tags
        """
    )

    scored_results = []
    for r in results:
        score = 0
        text = f"{r['title']} {r.get('description', '')} {' '.join(r.get('tags', []))}".lower()
        for kw in keywords:
            if kw in text:
                score += 1
        if score > 0:
            scored_results.append((score, r))

    scored_results.sort(key=lambda x: -x[0])
    top = scored_results[:5]

    return [
        ProductRecommendation(
            title=r["title"],
            price=r["price"] or 0,
            url=r["url"] or "",
            image_url=r.get("image_url", ""),
            reasoning=f"Matched {score} keyword(s) from your query.",
            ingredients=[],
            pairings=[],
        )
        for score, r in top
    ]


def graph_search(query: str) -> tuple[list[ProductRecommendation], str]:
    """
    GraphRAG search — extracts intent, traverses the knowledge graph,
    returns products with relationship-based reasoning.
    """
    # Step 1: Extract intent
    intent = extract_query_intent(query)
    graph_path_parts = [f"Query: '{query}'"]
    graph_path_parts.append(f"Extracted intent: {json.dumps(intent)}")

    # Step 2: Build dynamic Cypher query based on extracted intent
    cypher_parts = ["MATCH (p:Product)"]
    where_clauses = []
    optional_matches = []

    # Match health concerns
    if intent.get("health_concerns"):
        for concern in intent["health_concerns"]:
            optional_matches.append(
                f"OPTIONAL MATCH (p)-[:ADDRESSES]->(hc:HealthConcern) WHERE toLower(hc.name) CONTAINS toLower('{concern}')"
            )

    # Match ingredients
    if intent.get("ingredients"):
        for ingredient in intent["ingredients"]:
            optional_matches.append(
                f"OPTIONAL MATCH (p)-[:CONTAINS]->(ing:Ingredient) WHERE toLower(ing.name) CONTAINS toLower('{ingredient}')"
            )

    # Match occasions
    if intent.get("occasions"):
        for occasion in intent["occasions"]:
            optional_matches.append(
                f"OPTIONAL MATCH (p)-[:IDEAL_FOR]->(occ:Occasion) WHERE toLower(occ.name) CONTAINS toLower('{occasion}')"
            )

    # Match use cases
    if intent.get("use_cases"):
        for use_case in intent["use_cases"]:
            optional_matches.append(
                f"OPTIONAL MATCH (p)-[:USED_FOR]->(uc:UseCase) WHERE toLower(uc.name) CONTAINS toLower('{use_case}')"
            )

    # Always get ingredients and pairings for context
    full_query = f"""
        MATCH (p:Product)
        {chr(10).join(optional_matches)}
        OPTIONAL MATCH (p)-[:CONTAINS]->(all_ing:Ingredient)
        OPTIONAL MATCH (p)-[:PAIRS_WELL_WITH]-(paired:Product)
        OPTIONAL MATCH (p)-[:ADDRESSES]->(all_hc:HealthConcern)
        OPTIONAL MATCH (p)-[:HELPS_WITH]->(all_hb:HealthBenefit)
        WITH p,
             collect(DISTINCT all_ing.name) AS ingredients,
             collect(DISTINCT paired.title) AS pairings,
             collect(DISTINCT all_hc.name) AS concerns,
             collect(DISTINCT all_hb.name) AS benefits
        WHERE size(ingredients) > 0 OR size(concerns) > 0
        RETURN p.title AS title, p.price AS price, p.url AS url,
               p.image_url AS image_url,
               ingredients, pairings, concerns, benefits
        LIMIT 10
    """

    results = neo4j_client.run_query(full_query)

    if not results:
        graph_path_parts.append("No graph matches found, falling back to all products")
        results = neo4j_client.run_query(
            """
            MATCH (p:Product)
            OPTIONAL MATCH (p)-[:CONTAINS]->(ing:Ingredient)
            OPTIONAL MATCH (p)-[:ADDRESSES]->(hc:HealthConcern)
            RETURN p.title AS title, p.price AS price, p.url AS url,
                   p.image_url AS image_url,
                   collect(DISTINCT ing.name) AS ingredients,
                   [] AS pairings,
                   collect(DISTINCT hc.name) AS concerns,
                   [] AS benefits
            LIMIT 5
            """
        )

    # Step 3: Score results based on intent match
    scored = []
    for r in results:
        score = 0
        reasons = []

        for concern in intent.get("health_concerns", []):
            for c in r.get("concerns", []):
                if concern.lower() in c.lower():
                    score += 3
                    reasons.append(f"Addresses '{c}'")

        for ingredient in intent.get("ingredients", []):
            for ing in r.get("ingredients", []):
                if ingredient.lower() in ing.lower():
                    score += 2
                    reasons.append(f"Contains '{ing}'")

        for benefit in r.get("benefits", []):
            score += 0.5
            if len(reasons) < 4:
                reasons.append(f"Helps with '{benefit}'")

        if r.get("pairings"):
            reasons.append(f"Pairs well with: {', '.join(r['pairings'][:3])}")

        scored.append((score, r, reasons))

    scored.sort(key=lambda x: -x[0])
    top = scored[:5]

    recommendations = []
    for score, r, reasons in top:
        reasoning = " | ".join(reasons[:4]) if reasons else "Related product in the catalog"
        recommendations.append(
            ProductRecommendation(
                title=r["title"],
                price=r["price"] or 0,
                url=r["url"] or "",
                image_url=r.get("image_url", ""),
                reasoning=reasoning,
                ingredients=r.get("ingredients", [])[:8],
                pairings=r.get("pairings", [])[:3],
            )
        )

    graph_path = " → ".join(graph_path_parts)
    return recommendations, graph_path


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Query the product catalog using either flat search or GraphRAG.
    This is the key demo endpoint showing the GraphRAG advantage.
    """
    if request.mode == "flat":
        results = flat_search(request.query)
        return QueryResponse(
            mode="flat",
            query=request.query,
            results=results,
            graph_path="Simple keyword matching against product text",
        )
    else:
        results, graph_path = graph_search(request.query)
        return QueryResponse(
            mode="graph",
            query=request.query,
            results=results,
            graph_path=graph_path,
        )
