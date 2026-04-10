"""GraphRAG query endpoint — compares flat search vs graph-aware search."""

import os
import json
from typing import TypedDict, List, Dict, Any
from fastapi import APIRouter
from dotenv import load_dotenv
from pathlib import Path

# LangGraph & LangChain ecosystem
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from backend.graph.neo4j_client import neo4j_client
from backend.models.schemas import QueryRequest, QueryResponse, ProductRecommendation

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

router = APIRouter()

# ==========================================
# LANGGRAPH: State & Nodes
# ==========================================
class RouterState(TypedDict):
    query: str
    query_type: str
    product_mentions: List[str]
    intent: Dict[str, Any]

def get_azure_chat_llm():
    return AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        temperature=0
    )

def supervisor_node(state: RouterState) -> RouterState:
    llm = get_azure_chat_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an intelligent web store dispatcher. Classify the user query.\n"
                   "- If the user is specifically searching for a branded product name or exact tea (e.g. 'Acid Ease', 'Gut Cleanse'), output exactly: branded_product\n"
                   "- If the user is asking a discovery question about symptoms, occasions, or generic ingredients (e.g. 'what helps digestion?', 'tea for sleep'), output exactly: semantic_discovery\n"
                   "Output NOTHING ELSE."),
        ("user", "{query}")
    ])
    response = llm.invoke(prompt.format_messages(query=state["query"]))
    return {"query_type": response.content.strip()[:20], "intent": {}, "product_mentions": []}

def lexical_node(state: RouterState) -> RouterState:
    """Invoked when the user just wants a specific product. Bypasses the heavy hallucination-prone intent extraction."""
    # Since the supervisor confirmed it's a branded search, we use the raw query for direct lexical matching.
    return {"product_mentions": [state["query"].strip()], "intent": {}}

def semantic_node(state: RouterState) -> RouterState:
    """Invoked for generic discovery to traverse the graph."""
    llm = get_azure_chat_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a graph parameter extractor. Extract semantic attributes from the user's query.\n"
                   "Return ONLY a JSON object with these fields (use empty lists if not applicable):\n"
                   '{{"health_concerns": [], "ingredients": [], "occasions": [], "use_cases": []}}'),
        ("user", "{query}")
    ])
    response = llm.invoke(prompt.format_messages(query=state["query"]))
    
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].replace("```json", "").replace("```", "").strip()
        
    try:
        intent = json.loads(content)
    except json.JSONDecodeError:
        intent = {"health_concerns": [], "ingredients": [], "occasions": [], "use_cases": []}
        
    return {"intent": intent, "product_mentions": []}

def build_intent_graph():
    workflow = StateGraph(RouterState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("lexical", lexical_node)
    workflow.add_node("semantic", semantic_node)
    
    workflow.set_entry_point("supervisor")
    
    def route_query(state: RouterState):
        if "branded" in state["query_type"].lower():
            return "lexical"
        return "semantic"
        
    workflow.add_conditional_edges("supervisor", route_query, {
        "lexical": "lexical",
        "semantic": "semantic"
    })
    
    workflow.add_edge("lexical", END)
    workflow.add_edge("semantic", END)
    
    return workflow.compile()

# Compile the graph globally
intent_graph = build_intent_graph()


# ==========================================
# SEARCH PROCESSORS
# ==========================================
def flat_search(query: str) -> list[ProductRecommendation]:
    """Simulated flat RAG search — basic text matching against product titles and descriptions."""
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
    GraphRAG search — routes via LangGraph intent state machine,
    traverses the knowledge graph, and returns graph-scored products.
    """
    # Step 1: Execute LangGraph
    state = intent_graph.invoke({"query": query})
    query_type = state.get("query_type", "unknown")
    intent = state.get("intent", {})
    pms = state.get("product_mentions", [])
    
    graph_path_parts = [f"Query: '{query}'"]
    graph_path_parts.append(f"LangGraph execution: {query_type} path")
    graph_path_parts.append(f"Extracted parameters: intent={intent}, lexical={pms}")

    # Step 2: Build dynamic Cypher query
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

    # Build dynamic WHERE clause to ensure hybrid retrieval
    where_conditions = []
    if intent.get("health_concerns") or intent.get("ingredients") or intent.get("occasions") or intent.get("use_cases"):
        where_conditions.append("size(ingredients) > 0 OR size(concerns) > 0")
        
    for pm in pms:
        pm_clean = pm.replace("'", "\\'") # Safety
        where_conditions.append(f"toLower(p.title) CONTAINS toLower('{pm_clean}')")
        
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " OR ".join(where_conditions)

    # Always get context graph components
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
        {where_clause}
        RETURN p.title AS title, p.price AS price, p.url AS url,
               p.image_url AS image_url,
               ingredients, pairings, concerns, benefits
        LIMIT 15
    """

    results = neo4j_client.run_query(full_query)

    if not results:
        graph_path_parts.append("No matches found, falling back")
        results = neo4j_client.run_query(
            """
            MATCH (p:Product)
            RETURN p.title AS title, p.price AS price, p.url AS url,
                   p.image_url AS image_url,
                   [] AS ingredients, [] AS pairings, [] AS concerns, [] AS benefits
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

        # Hybrid Lexical Scoring Boost
        for pm in pms:
            if pm.lower() in r["title"].lower():
                score += 50  # Overrides semantic logic
                reasons.insert(0, f"★ Exact product match: '{pm}'")

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
