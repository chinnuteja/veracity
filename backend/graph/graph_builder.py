"""Build the Knowledge Graph in Neo4j from parsed products and extracted attributes."""

from backend.models.schemas import CleanProduct, ExtractedAttributes
from backend.graph.neo4j_client import neo4j_client


# Color mapping for node types (used in visualization)
NODE_COLORS = {
    "Product": "#6366F1",       # Indigo
    "Ingredient": "#F59E0B",    # Amber
    "HealthBenefit": "#10B981", # Emerald
    "HealthConcern": "#F43F5E", # Rose
    "Occasion": "#0EA5E9",      # Sky
    "Category": "#8B5CF6",      # Purple
    "UseCase": "#EC4899",       # Pink
}


def _normalize(text: str) -> str:
    """Normalize a string for consistent node naming."""
    return text.strip().title()


def create_constraints(client=None):
    """Create uniqueness constraints for efficient MERGE operations."""
    c = client or neo4j_client
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.shopify_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (h:HealthBenefit) REQUIRE h.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:HealthConcern) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Occasion) REQUIRE o.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (cat:Category) REQUIRE cat.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (u:UseCase) REQUIRE u.name IS UNIQUE",
    ]
    for q in constraints:
        c.run_write(q)
    print("  ✓ Constraints created")


def build_product_node(product: CleanProduct, client=None):
    """Create a Product node in Neo4j."""
    c = client or neo4j_client
    c.run_write(
        """
        MERGE (p:Product {shopify_id: $shopify_id})
        SET p.title = $title,
            p.handle = $handle,
            p.description = $description,
            p.price = $price,
            p.compare_at_price = $compare_at_price,
            p.product_type = $product_type,
            p.vendor = $vendor,
            p.sku = $sku,
            p.available = $available,
            p.image_url = $image_url,
            p.url = $url,
            p.tags = $tags
        """,
        {
            "shopify_id": product.shopify_id,
            "title": product.title,
            "handle": product.handle,
            "description": product.description[:500],  # Truncate for Neo4j
            "price": product.price,
            "compare_at_price": product.compare_at_price,
            "product_type": product.product_type,
            "vendor": product.vendor,
            "sku": product.sku,
            "available": product.available,
            "image_url": product.image_url,
            "url": product.url,
            "tags": product.tags,
        },
    )


def build_attribute_nodes_and_edges(
    product: CleanProduct,
    attributes: ExtractedAttributes,
    client=None,
):
    """Create attribute nodes and connect them to the product."""
    c = client or neo4j_client
    sid = product.shopify_id

    # Ingredients → CONTAINS
    for ingredient in attributes.ingredients:
        name = _normalize(ingredient)
        if len(name) < 2:
            continue
        c.run_write(
            """
            MATCH (p:Product {shopify_id: $sid})
            MERGE (i:Ingredient {name: $name})
            MERGE (p)-[:CONTAINS]->(i)
            """,
            {"sid": sid, "name": name},
        )

    # Health Benefits → HELPS_WITH
    for benefit in attributes.health_benefits:
        name = _normalize(benefit)
        if len(name) < 3:
            continue
        c.run_write(
            """
            MATCH (p:Product {shopify_id: $sid})
            MERGE (h:HealthBenefit {name: $name})
            MERGE (p)-[:HELPS_WITH]->(h)
            """,
            {"sid": sid, "name": name},
        )

    # Health Concerns → ADDRESSES
    for concern in attributes.health_concerns:
        name = _normalize(concern)
        if len(name) < 3:
            continue
        c.run_write(
            """
            MATCH (p:Product {shopify_id: $sid})
            MERGE (c:HealthConcern {name: $name})
            MERGE (p)-[:ADDRESSES]->(c)
            """,
            {"sid": sid, "name": name},
        )

    # Occasions → IDEAL_FOR
    for occasion in attributes.usage_occasions:
        name = _normalize(occasion)
        if len(name) < 3:
            continue
        c.run_write(
            """
            MATCH (p:Product {shopify_id: $sid})
            MERGE (o:Occasion {name: $name})
            MERGE (p)-[:IDEAL_FOR]->(o)
            """,
            {"sid": sid, "name": name},
        )

    # Use Cases → USED_FOR
    for use_case in attributes.use_cases:
        name = _normalize(use_case)
        if len(name) < 3:
            continue
        c.run_write(
            """
            MATCH (p:Product {shopify_id: $sid})
            MERGE (u:UseCase {name: $name})
            MERGE (p)-[:USED_FOR]->(u)
            """,
            {"sid": sid, "name": name},
        )

    # Category from product_type or tags
    if product.product_type:
        cat_name = _normalize(product.product_type)
        c.run_write(
            """
            MATCH (p:Product {shopify_id: $sid})
            MERGE (cat:Category {name: $name})
            MERGE (p)-[:IN_CATEGORY]->(cat)
            """,
            {"sid": sid, "name": cat_name},
        )


def build_cross_product_edges(client=None):
    """
    Create relationship edges BETWEEN products based on shared attributes.
    These are the edges that DON'T exist in Shopify — the "discovered" relationships.
    """
    c = client or neo4j_client

    # SHARES_INGREDIENT: Products sharing 2+ ingredients
    print("  Building SHARES_INGREDIENT edges...")
    c.run_write(
        """
        MATCH (p1:Product)-[:CONTAINS]->(i:Ingredient)<-[:CONTAINS]-(p2:Product)
        WHERE p1.shopify_id < p2.shopify_id
        WITH p1, p2, count(i) AS shared_count, collect(i.name) AS shared_ingredients
        WHERE shared_count >= 2
        MERGE (p1)-[r:SHARES_INGREDIENT]->(p2)
        SET r.count = shared_count, r.ingredients = shared_ingredients
        """
    )

    # ALTERNATIVE_TO: Products addressing the same health concern
    print("  Building ALTERNATIVE_TO edges...")
    c.run_write(
        """
        MATCH (p1:Product)-[:ADDRESSES]->(c:HealthConcern)<-[:ADDRESSES]-(p2:Product)
        WHERE p1.shopify_id < p2.shopify_id AND p1.price <> p2.price
        WITH p1, p2, collect(c.name) AS shared_concerns
        MERGE (p1)-[r:ALTERNATIVE_TO]->(p2)
        SET r.shared_concerns = shared_concerns
        """
    )

    # PAIRS_WELL_WITH: Products with complementary use cases (different concerns but same occasion)
    print("  Building PAIRS_WELL_WITH edges...")
    c.run_write(
        """
        MATCH (p1:Product)-[:IDEAL_FOR]->(o:Occasion)<-[:IDEAL_FOR]-(p2:Product)
        WHERE p1.shopify_id < p2.shopify_id
        AND NOT (p1)-[:ALTERNATIVE_TO]-(p2)
        AND NOT (p1)-[:SHARES_INGREDIENT]-(p2)
        WITH p1, p2, collect(o.name) AS shared_occasions
        MERGE (p1)-[r:PAIRS_WELL_WITH]->(p2)
        SET r.shared_occasions = shared_occasions
        """
    )


def build_full_graph(
    products: list[CleanProduct],
    attributes: list[ExtractedAttributes],
    client=None,
):
    """
    Build the complete knowledge graph:
    1. Clear existing data
    2. Create constraints
    3. Create product nodes
    4. Create attribute nodes + edges
    5. Create cross-product relationship edges
    """
    c = client or neo4j_client
    c.connect()

    print("\n🔨 Building Knowledge Graph...")
    print("=" * 50)

    # Step 1: Clear
    c.clear_graph()

    # Step 2: Constraints
    create_constraints(c)

    # Step 3 & 4: Products + attributes
    attrs_by_id = {a.shopify_id: a for a in attributes}

    for i, product in enumerate(products):
        print(f"  [{i + 1}/{len(products)}] {product.title[:50]}...")
        build_product_node(product, c)

        if product.shopify_id in attrs_by_id:
            build_attribute_nodes_and_edges(product, attrs_by_id[product.shopify_id], c)

    # Step 5: Cross-product edges
    print("\n  Building cross-product relationship edges...")
    build_cross_product_edges(c)

    # Stats
    stats = c.get_stats()
    print(f"\n{'=' * 50}")
    print(f"✅ Knowledge Graph Built!")
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Total edges: {stats['total_edges']}")
    print(f"   Nodes by type: {stats['nodes_by_type']}")
    print(f"   Edges by type: {stats['edges_by_type']}")
    print(f"{'=' * 50}")

    return stats
