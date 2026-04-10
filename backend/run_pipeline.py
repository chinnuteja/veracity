"""Run the full ingestion pipeline: Fetch → Parse → Extract → Build Graph."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ingestion.shopify_fetcher import fetch_all_products, save_raw_products, load_raw_products
from backend.ingestion.product_parser import parse_all_products
from backend.graph.attribute_extractor import extract_all_attributes
from backend.graph.graph_builder import build_full_graph


async def main():
    print("\n" + "=" * 60)
    print("🚀 HELIO VERACITY LAYER — Full Ingestion Pipeline")
    print("=" * 60)

    # Step 1: Fetch products
    print("\n📦 Step 1: Fetching products from Blue Tea Shopify store...")
    try:
        raw_products = load_raw_products()
        print(f"  Using cached data ({len(raw_products)} products)")
    except FileNotFoundError:
        raw_products = await fetch_all_products("https://bluetea.co.in", limit=50)
        save_raw_products(raw_products)

    # Step 2: Parse and clean
    print("\n🧹 Step 2: Parsing and cleaning product data...")
    clean_products = parse_all_products(raw_products)

    print(f"\n  Sample products:")
    for p in clean_products[:5]:
        print(f"    • {p.title} — ₹{p.price} — tags: {p.tags[:3]}")
        if p.description:
            print(f"      desc: {p.description[:100]}...")

    # Step 3: Extract attributes via Azure OpenAI
    print("\n🧠 Step 3: Extracting semantic attributes via Azure OpenAI...")
    attributes = extract_all_attributes(clean_products, use_cache=True)

    print(f"\n  Sample extractions:")
    for a in attributes[:3]:
        matching_product = next((p for p in clean_products if p.shopify_id == a.shopify_id), None)
        name = matching_product.title if matching_product else f"ID:{a.shopify_id}"
        print(f"    • {name}")
        print(f"      Ingredients: {a.ingredients[:5]}")
        print(f"      Benefits: {a.health_benefits[:3]}")
        print(f"      Concerns: {a.health_concerns[:3]}")

    # Step 4: Build the knowledge graph
    print("\n🔨 Step 4: Building Knowledge Graph in Neo4j...")
    stats = build_full_graph(clean_products, attributes)

    print("\n" + "=" * 60)
    print("✅ Pipeline complete!")
    print(f"   Products: {len(clean_products)}")
    print(f"   Graph nodes: {stats['total_nodes']}")
    print(f"   Graph edges: {stats['total_edges']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
