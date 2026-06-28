"""Universal Commerce Protocol (UCP) API Endpoints.
This router provides endpoints that allow AI Agents (like Google Gemini)
to securely interact with our merchant's catalog and execute transactions.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.graph.neo4j_client import neo4j_client


router = APIRouter()

class UCPResolveRequest(BaseModel):
    shopify_id: int

class UCPResolveResponse(BaseModel):
    available: bool
    price: float
    currency: str = "INR"
    checkout_url: Optional[str] = None
    message: str = ""

@router.post("/resolve", response_model=UCPResolveResponse)
async def ucp_resolve(request: UCPResolveRequest):
    """
    UCP Resolve Phase: The AI Agent asks if a product is available and what the exact price is.
    """
    result = neo4j_client.run_query(
        """
        MATCH (p:Product {shopify_id: $sid})
        RETURN p.price AS price, p.available AS available, p.variant_id AS variant_id, p.url AS url
        """,
        {"sid": request.shopify_id}
    )

    if not result:
        raise HTTPException(status_code=404, detail="Product not found in UCP registry.")

    p = result[0]
    
    # Extract base store URL from the product's URL
    store_url = p.get("url", "").split("/products/")[0] if "/products/" in p.get("url", "") else ""
    
    # Generate the Shopify Cart Permalink if available
    checkout_url = f"{store_url}/cart/{p['variant_id']}:1" if p.get("variant_id") and store_url else store_url

    return UCPResolveResponse(
        available=p.get("available", False),
        price=p.get("price", 0.0),
        checkout_url=checkout_url,
        message="Product resolved for direct AI checkout." if p.get("variant_id") else "Variant ID missing, fallback to store URL."
    )

@router.post("/checkout")
async def ucp_checkout(request: UCPResolveRequest):
    """
    UCP Checkout Phase: The AI Agent explicitly requests a checkout link to present to the user.
    """
    result = neo4j_client.run_query(
        """
        MATCH (p:Product {shopify_id: $sid})
        RETURN p.variant_id AS variant_id, p.title AS title, p.url AS url
        """,
        {"sid": request.shopify_id}
    )

    if not result:
        raise HTTPException(status_code=404, detail="Product not found in UCP registry.")

    p = result[0]
    variant_id = p.get("variant_id")
    
    if not variant_id:
         raise HTTPException(status_code=400, detail="Product variant ID missing, cannot create 1-click cart.")

    store_url = p.get("url", "").split("/products/")[0] if "/products/" in p.get("url", "") else ""
    
    # Shopify Cart Permalink Structure: store_url/cart/variant_id:quantity
    cart_url = f"{store_url}/cart/{variant_id}:1" if store_url else ""
    
    return {
        "status": "success",
        "action": "redirect",
        "url": cart_url,
        "message": f"Proceeding to secure checkout for {p.get('title')}"
    }
