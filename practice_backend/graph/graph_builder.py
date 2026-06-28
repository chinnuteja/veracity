"""
Graph Builder for Helio Veracity Practice Rewrite.
Weaves together cleaned product data and AI attributes into a Neo4j Knowledge Graph.
"""

from practice_backend.models.schemas import CleanProduct, ExtractedAttributes
from practice_backend.graph.neo4j_client import neo4j_client

def _normalize(text: str) -> str:
    """Standardize names (e.g. 'GINGER' -> 'Ginger')."""
    return text.strip().title()

def create_constraints():
    """
    Creates uniqueness constraints in Neo4j.
    Crucial for preventing duplicate 'Ginger' or 'Product' nodes.
    """
    queries = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.shopify_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (b:Benefit) REQUIRE b.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concern) REQUIRE c.name IS UNIQUE"
    ]
    for q in queries:
        neo4j_client.run_write(q)
    print("  [OK] Graph constraints initialized.")

def build_product_node(product: CleanProduct):
    """
    Creates or updates a Product node in the graph.
    Uses MERGE to ensure idempotency (running twice doesn't duplicate).
    """
    query = """
    MERGE (p:Product {shopify_id: $shopify_id})
    SET p.title = $title,
        p.description = $description,
        p.price = $price,
        p.image_url = $image_url,
        p.tags = $tags
    """
    neo4j_client.run_write(query, {
        "shopify_id": product.shopify_id,
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "image_url": product.image_url,
        "tags": product.tags
    })

def build_attribute_nodes_and_edges(
    product: CleanProduct, 
    attributes: ExtractedAttributes
):
    """
    Connects the product to its semantic attributes.
    This creates the 'Intelligence Web' around each product.
    """
    sid = product.shopify_id

    # Weave Ingredients
    for ingredient in attributes.ingredients:
        name = _normalize(ingredient)
        if not name: continue
        neo4j_client.run_write(
            """
            MATCH (p:Product {shopify_id: $sid})
            MERGE (i:Ingredient {name: $name})
            MERGE (p)-[:HAS_INGREDIENT]->(i)
            """,
            {"sid": sid, "name": name}
        )

    # Weave Health Benefits
    for benefit in attributes.health_benefits:
        name = _normalize(benefit)
        if not name: continue
        neo4j_client.run_write(
            """
            MATCH (p:Product {shopify_id: $sid})
            MERGE (b:Benefit {name: $name})
            MERGE (p)-[:PROVIDES_BENEFIT]->(b)
            """,
            {"sid": sid, "name": name}
        )

    # Weave Health Concerns
    for concern in attributes.health_concerns:
        name = _normalize(concern)
        if not name: continue
        neo4j_client.run_write(
            """
            MATCH (p:Product {shopify_id: $sid})
            MERGE (c:Concern {name: $name})
            MERGE (p)-[:ADDRESSES_CONCERN]->(c)
            """,
            {"sid": sid, "name": name}
        )

def build_cross_product_edges():
    """
    Discovers relationships BETWEEN products based on shared attributes.
    This creates the 'Intelligence' that makes our shop unique.
    """
    print("  [DISCOVERY] Building relationships between similar products...")
    neo4j_client.run_write("""
        MATCH (p1:Product)-[:HAS_INGREDIENT]->(i:Ingredient)<-[:HAS_INGREDIENT]-(p2:Product)
        WHERE p1.shopify_id < p2.shopify_id
        WITH p1, p2, count(i) AS shared_count, collect(i.name) AS names
        WHERE shared_count >= 2
        MERGE (p1)-[r:SHARES_INGREDIENTS]->(p2)
        SET r.count = shared_count, r.ingredients = names
    """)

def build_full_graph(products: list[CleanProduct], attributes: list[ExtractedAttributes]):
    """
    The 'Manager' function. 
    It clears the graph and rebuilds everything from the cleaned data.
    """
    print("\n🔨 Starting Knowledge Graph Build...")
    neo4j_client.connect()
    
    # 1. Reset and Constraints
    neo4j_client.clear_graph()
    create_constraints()
    
    # 2. Build the world product-by-product
    attr_map = {a.shopify_id: a for a in attributes}
    
    for i, product in enumerate(products):
        print(f"  [{i+1}/{len(products)}] Building: {product.title}")
        build_product_node(product)
        
        if product.shopify_id in attr_map:
            build_attribute_nodes_and_edges(product, attr_map[product.shopify_id])

    # 3. Discover hidden relationships
    build_cross_product_edges()
    print("\n✅ Knowledge Graph Build Complete!")
