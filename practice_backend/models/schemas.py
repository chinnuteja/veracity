"""
Pydantic schemas for the Helio Veracity Layer.
These act as the 'Data Contracts' between different layers of our system.
"""

from pydantic import BaseModel, Field
from typing import List, Optional

class CleanProduct(BaseModel):
    """
    The output of our Fetcher. 
    Think of this as a DTO for raw Shopify data.
    """
    shopify_id: int
    title: str
    description: Optional[str] = None
    tags: List[str] = []
    product_type: Optional[str] = None
    price: float = 0.0
    image_url: Optional[str] = None

class ExtractedAttributes(BaseModel):
    """
    The output of our AI Brain. 
    These are the semantic 'gems' we will turn into Graph Nodes.
    """
    shopify_id: int
    ingredients: List[str] = Field(default_factory=list)
    health_benefits: List[str] = Field(default_factory=list)
    health_concerns: List[str] = Field(default_factory=list)
    taste_profile: List[str] = Field(default_factory=list)
    caffeine_free: bool = True
    usage_occasions: List[str] = Field(default_factory=list)
    dietary_tags: List[str] = Field(default_factory=list)
    target_audience: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
