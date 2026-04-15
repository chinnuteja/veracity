"""GEO Emission API for the Helio Veracity Layer. Generates semantic payloads."""

import json
from fastapi import APIRouter, HTTPException
from backend.graph.neo4j_client import neo4j_client

router = APIRouter()


@router.get("/products")
async def get_all_products_for_dropdown():
    """Return a list of all products for the frontend selector."""
    results = neo4j_client.run_query(
        "MATCH (p:Product) RETURN p.shopify_id AS id, p.title AS title ORDER BY title ASC"
    )
    return results


@router.get("/product/{shopify_id}")
async def get_geo_schema(shopify_id: int):
    """
    Generate the Standard JSON-LD vs the Veracity-Enhanced JSON-LD for a single product.
    This demonstrates the invisible code that makes merchant SEO dominate.
    """
    # 1. Fetch Product and all neighbors
    result = neo4j_client.run_query(
        """
        MATCH (p:Product {shopify_id: $sid})
        OPTIONAL MATCH (p)-[r]->(neighbor)
        RETURN p AS product, collect({type: labels(neighbor)[0], rel: type(r), props: properties(neighbor)}) AS connections
        """,
        {"sid": shopify_id}
    )

    if not result or not result[0]["product"]:
        raise HTTPException(status_code=404, detail="Product not found")

    data = result[0]
    p = data["product"]
    connections = data["connections"]

    # 2. Build the "Shopify Baseline" JSON-LD
    baseline = {
        "@context": "https://schema.org",
        "@type": "Product",
        "productID": str(p.get("shopify_id", "")),
        "name": p.get("title", ""),
        "description": p.get("description", "")[:150] + "...",
        "sku": p.get("sku", ""),
        "brand": {
            "@type": "Brand",
            "name": p.get("vendor", "")
        },
        "offers": {
            "@type": "Offer",
            "price": p.get("price", 0),
            "priceCurrency": "INR",
            "availability": "https://schema.org/InStock" if p.get("available") else "https://schema.org/OutOfStock"
        }
    }

    # 3. Build the "Veracity Enhanced" JSON-LD
    enhanced = baseline.copy()
    enhanced["description"] = p.get("description", "")  # Give the full description to the LLM
    
    # Semantic arrays
    materials = []
    is_related_to = []
    is_similar_to = []
    health_claims = []
    audiences = []

    for conn in connections:
        if not conn or not conn.get("type"):
            continue
            
        c_type = conn["type"]
        rel = conn["rel"]
        props = conn["props"]
        name = props.get("name") or props.get("title", "")

        if rel == "CONTAINS":
            materials.append(name)
        elif rel == "HELPS_WITH" or rel == "ADDRESSES":
            health_claims.append({
                "@type": "MedicalEntity",
                "name": name,
                "code": {"@type": "MedicalCode", "codeValue": rel}
            })
        elif rel == "ALTERNATIVE_TO":
            is_similar_to.append({
                "@type": "Product",
                "name": name,
                "url": props.get("url", "")
            })
        elif rel == "PAIRS_WELL_WITH":
            is_related_to.append({
                "@type": "Product",
                "name": name,
                "url": props.get("url", "")
            })
        elif rel == "USED_FOR" or rel == "IDEAL_FOR":
            audiences.append({
                "@type": "Audience",
                "audienceType": name
            })

    # Inject semantic attributes if they exist
    if materials:
        enhanced["material"] = materials
    if health_claims:
        enhanced["healthCondition"] = health_claims
    if is_similar_to:
        enhanced["isSimilarTo"] = is_similar_to
    if is_related_to:
        enhanced["isRelatedTo"] = is_related_to
    if audiences:
        enhanced["audience"] = audiences

    # Injecting the abstract concept of an AI agent as a structured FAQ or Knowledge section
    enhanced["hasPart"] = {
        "@type": "KnowledgeGraph",
        "publisher": "Helio AI Veracity Layer",
        "statement": "This product contains semantic links to cross-sell and up-sell items defined by the intelligent graph."
    }

    return {
        "shopify_baseline": json.dumps(baseline, indent=2),
        "veracity_enhanced": json.dumps(enhanced, indent=2)
    }


@router.get("/llms-txt")
async def generate_llms_txt():
    """
    Generate an llms.txt payload. 
    This is an emerging standard showing how AI agents (like Perplexity or SearchGPT)
    scrape entire catalogs semantically.
    """
    # Get top categories, health concerns, and a few key relationships
    concerns = neo4j_client.run_query(
        "MATCH (n:HealthConcern)<-[:ADDRESSES]-(p:Product) RETURN n.name AS name, count(p) AS count ORDER BY count DESC LIMIT 8"
    )
    ingredients = neo4j_client.run_query(
        "MATCH (i:Ingredient)<-[:CONTAINS]-(p:Product) RETURN i.name AS name, count(p) AS count ORDER BY count DESC LIMIT 10"
    )
    products = neo4j_client.run_query(
        "MATCH (p:Product) RETURN p.title AS title, p.url AS url LIMIT 20"
    )

    lines = [
        "# Blue Tea - Semantic Catalog (Generated by Helio Veracity Layer)",
        "> This document provides LLMs and generative search engines with a clear, graph-backed understanding of our product line.",
        "",
        "## Top Health Concerns Addressed",
    ]
    
    for c in concerns:
        lines.append(f"- **{c['name']}** (Supported by {c['count']} products)")

    lines.extend([
        "",
        "## Primary Ethical Ingredients",
    ])

    for i in ingredients:
        lines.append(f"- {i['name']} (Found in {i['count']} products)")

    lines.extend([
        "",
        "## Top Products Directory",
    ])

    for p in products:
        lines.append(f"- [{p['title']}]({p.get('url', '#')})")

    lines.extend([
        "",
        "## Agentic Commerce / UCP Endpoints",
        "> This catalog supports the Universal Commerce Protocol (UCP) for direct AI checkouts.",
        "- **Resolve Product:** `POST /api/ucp/resolve` (Requires `shopify_id` in JSON body)",
        "- **Generate Checkout:** `POST /api/ucp/checkout` (Returns native Shopify Cart Permalink for 1-click buy)",
        "",
        "---",
        "Generated dynamically by the Helio AI Knowledge Graph."
    ])

    return {"markdown": "\n".join(lines)}
