"""API endpoint to serve graph data for the react-force-graph visualization."""

from fastapi import APIRouter
from backend.graph.neo4j_client import neo4j_client
from backend.graph.graph_builder import NODE_COLORS
from backend.models.schemas import GraphData, GraphNode, GraphLink

router = APIRouter()

# Edge colors by relationship type
EDGE_COLORS = {
    "CONTAINS": "#F59E0B88",
    "HELPS_WITH": "#10B98188",
    "ADDRESSES": "#F43F5E88",
    "IDEAL_FOR": "#0EA5E988",
    "IN_CATEGORY": "#8B5CF688",
    "USED_FOR": "#EC489988",
    "SHARES_INGREDIENT": "#EF4444",
    "ALTERNATIVE_TO": "#F97316",
    "PAIRS_WELL_WITH": "#22D3EE",
}


@router.get("/graph", response_model=GraphData)
async def get_full_graph():
    """Return the full knowledge graph in react-force-graph format."""
    # Fetch all nodes
    node_records = neo4j_client.run_query(
        """
        MATCH (n)
        RETURN
            id(n) AS neo4j_id,
            labels(n)[0] AS label_type,
            properties(n) AS props
        """
    )

    # Fetch all edges
    edge_records = neo4j_client.run_query(
        """
        MATCH (a)-[r]->(b)
        RETURN
            id(a) AS source_id,
            id(b) AS target_id,
            type(r) AS rel_type,
            properties(r) AS props
        """
    )

    # Build nodes
    nodes = []
    for record in node_records:
        neo4j_id = record["neo4j_id"]
        label_type = record["label_type"]
        props = record["props"]

        # Determine display label
        if label_type == "Product":
            display_label = props.get("title", "Unknown Product")
            size = 10.0
            node_id = f"product_{props.get('shopify_id', neo4j_id)}"
        else:
            display_label = props.get("name", "Unknown")
            size = 5.0
            node_id = f"{label_type.lower()}_{display_label.lower().replace(' ', '_')}"

        nodes.append(GraphNode(
            id=node_id,
            label=display_label,
            type=label_type,
            color=NODE_COLORS.get(label_type, "#999"),
            size=size,
            metadata={
                "neo4j_id": neo4j_id,
                **{k: v for k, v in props.items()
                   if k not in ("description",) and not isinstance(v, (list,))},
                # Include lists separately to avoid issues
                "tags": props.get("tags", []),
            },
        ))

    # Build a neo4j_id → node_id mapping for edges
    id_map = {}
    for record, node in zip(node_records, nodes):
        id_map[record["neo4j_id"]] = node.id

    # Build links
    links = []
    for record in edge_records:
        source = id_map.get(record["source_id"])
        target = id_map.get(record["target_id"])
        rel_type = record["rel_type"]

        if source and target:
            links.append(GraphLink(
                source=source,
                target=target,
                type=rel_type,
                color=EDGE_COLORS.get(rel_type, "#66666688"),
                label=rel_type.replace("_", " ").title(),
            ))

    return GraphData(nodes=nodes, links=links)


@router.get("/graph/stats")
async def get_graph_stats():
    """Return graph statistics."""
    stats = neo4j_client.get_stats()

    # Count cross-product edges specifically (these are the "discovered" ones)
    cross_product_types = ["SHARES_INGREDIENT", "ALTERNATIVE_TO", "PAIRS_WELL_WITH"]
    discovered_edges = sum(
        stats["edges_by_type"].get(t, 0) for t in cross_product_types
    )

    return {
        **stats,
        "discovered_relationships": discovered_edges,
        "node_colors": NODE_COLORS,
    }


@router.get("/product/{shopify_id}")
async def get_product_with_neighbors(shopify_id: int):
    """Get a product and all its graph neighbors."""
    result = neo4j_client.run_query(
        """
        MATCH (p:Product {shopify_id: $sid})
        OPTIONAL MATCH (p)-[r]->(related)
        RETURN p AS product,
               collect({
                   node: related,
                   label: labels(related)[0],
                   relationship: type(r),
                   props: properties(related)
               }) AS neighbors
        """,
        {"sid": shopify_id},
    )

    if not result:
        return {"error": "Product not found"}

    record = result[0]
    product_props = dict(record["product"])
    neighbors = []

    for n in record["neighbors"]:
        if n["node"] is not None:
            neighbors.append({
                "type": n["label"],
                "relationship": n["relationship"],
                "name": n["props"].get("name") or n["props"].get("title", "Unknown"),
                "props": {k: v for k, v in n["props"].items() if not isinstance(v, list)},
            })

    return {
        "product": product_props,
        "neighbors": neighbors,
        "neighbor_count": len(neighbors),
    }
