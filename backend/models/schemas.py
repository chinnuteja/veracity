"""Pydantic models for the Helio Veracity Layer."""

from pydantic import BaseModel, Field
from typing import Optional


class CleanProduct(BaseModel):
    """A cleaned, structured product parsed from Shopify raw JSON."""
    shopify_id: int
    variant_id: Optional[int] = None
    title: str
    handle: str
    description: str = ""
    price: float = 0.0
    compare_at_price: Optional[float] = None
    tags: list[str] = Field(default_factory=list)
    product_type: str = ""
    vendor: str = ""
    sku: str = ""
    available: bool = True
    image_url: str = ""
    url: str = ""


class ExtractedAttributes(BaseModel):
    """Semantic attributes extracted by LLM from a product."""
    shopify_id: int
    ingredients: list[str] = Field(default_factory=list)
    health_benefits: list[str] = Field(default_factory=list)
    health_concerns: list[str] = Field(default_factory=list)
    taste_profile: list[str] = Field(default_factory=list)
    caffeine_free: bool = True
    usage_occasions: list[str] = Field(default_factory=list)
    dietary_tags: list[str] = Field(default_factory=list)
    target_audience: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    """A node in the visualization graph."""
    id: str
    label: str
    type: str
    color: str
    size: float = 4.0
    metadata: dict = Field(default_factory=dict)


class GraphLink(BaseModel):
    """An edge in the visualization graph."""
    source: str
    target: str
    type: str
    color: str = "#666"
    label: str = ""


class GraphData(BaseModel):
    """Full graph data for react-force-graph."""
    nodes: list[GraphNode]
    links: list[GraphLink]


class QueryRequest(BaseModel):
    """A user query for the GraphRAG endpoint."""
    query: str
    mode: str = "graph"  # "graph" or "flat"


class ProductRecommendation(BaseModel):
    """A single product recommendation from the query engine."""
    title: str
    price: float
    url: str
    image_url: str = ""
    reasoning: str = ""
    ingredients: list[str] = Field(default_factory=list)
    pairings: list[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    """Response from the query endpoint."""
    mode: str
    query: str
    results: list[ProductRecommendation]
    graph_path: str = ""  # Human-readable graph traversal path
