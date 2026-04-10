"""FastAPI application for the Helio Veracity Layer MVP."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.graph_data import router as graph_router
from backend.api.query_router import router as query_router
from backend.api.geo_router import router as geo_router
from backend.graph.neo4j_client import neo4j_client
from backend.ingestion.shopify_fetcher import (
    fetch_all_products,
    save_raw_products,
    load_raw_products,
)
from backend.ingestion.product_parser import parse_all_products
from backend.graph.attribute_extractor import extract_all_attributes
from backend.graph.graph_builder import build_full_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to Neo4j on startup, close on shutdown."""
    neo4j_client.connect()
    yield
    neo4j_client.close()


app = FastAPI(
    title="Helio Veracity Layer",
    description="Semantic Product Knowledge Graph for Shopify — GEO-Optimized AI Infrastructure",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(graph_router, prefix="/api", tags=["Graph"])
app.include_router(query_router, prefix="/api", tags=["Query"])
app.include_router(geo_router, prefix="/api/geo", tags=["GEO-Emission"])


@app.get("/")
async def root():
    return {
        "name": "Helio Veracity Layer",
        "status": "running",
        "description": "Semantic Knowledge Graph + GEO Engine for Shopify",
    }


@app.post("/api/ingest")
async def run_ingestion_pipeline(
    store_url: str = "https://bluetea.co.in",
    product_limit: int = 50,
    use_cache: bool = True,
):
    """
    Run the full ingestion pipeline:
    1. Fetch products from Shopify
    2. Parse and clean product data
    3. Extract semantic attributes via Azure OpenAI
    4. Build the knowledge graph in Neo4j
    """
    print("\n" + "=" * 60)
    print("🚀 HELIO VERACITY LAYER — Ingestion Pipeline")
    print("=" * 60)

    # Step 1: Fetch
    print("\n📦 Step 1: Fetching products from Shopify...")
    try:
        raw_products = load_raw_products()
        print(f"  Using cached data ({len(raw_products)} products)")
    except FileNotFoundError:
        raw_products = await fetch_all_products(store_url, product_limit)
        save_raw_products(raw_products)

    # Step 2: Parse
    print("\n🧹 Step 2: Parsing and cleaning product data...")
    clean_products = parse_all_products(raw_products)

    # Step 3: Extract attributes
    print("\n🧠 Step 3: Extracting semantic attributes via Azure OpenAI...")
    attributes = extract_all_attributes(clean_products, use_cache=use_cache)

    # Step 4: Build graph
    print("\n🔨 Step 4: Building Knowledge Graph in Neo4j...")
    stats = build_full_graph(clean_products, attributes)

    return {
        "status": "success",
        "products_fetched": len(raw_products),
        "products_parsed": len(clean_products),
        "attributes_extracted": len(attributes),
        "graph_stats": stats,
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        node_count = neo4j_client.get_node_count()
        return {
            "status": "healthy",
            "neo4j": "connected",
            "graph_nodes": node_count,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "neo4j": str(e),
        }
