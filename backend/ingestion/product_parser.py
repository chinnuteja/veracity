"""Parse raw Shopify product JSON into clean, structured product objects."""

import re
from bs4 import BeautifulSoup

from backend.models.schemas import CleanProduct


STORE_URL = "https://bluetea.co.in"


def strip_html(html_string: str | None) -> str:
    """Remove HTML tags and clean up whitespace from Shopify body_html."""
    if not html_string:
        return ""
    soup = BeautifulSoup(html_string, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    # Collapse multiple spaces/newlines
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_product(raw: dict) -> CleanProduct:
    """Convert a raw Shopify product dict into a CleanProduct."""
    # Get the first available variant for pricing
    variants = raw.get("variants", [])
    first_variant = variants[0] if variants else {}

    price = 0.0
    try:
        price = float(first_variant.get("price", "0"))
    except (ValueError, TypeError):
        price = 0.0

    compare_at_price = None
    try:
        cap = first_variant.get("compare_at_price")
        if cap:
            compare_at_price = float(cap)
    except (ValueError, TypeError):
        pass

    # Get first image URL
    images = raw.get("images", [])
    image_url = images[0]["src"] if images else ""

    # Build the product URL
    handle = raw.get("handle", "")
    url = f"{STORE_URL}/products/{handle}" if handle else ""

    # Check availability
    available = any(v.get("available", False) for v in variants)

    # Get SKU from first variant
    sku = first_variant.get("sku", "") or ""

    # Clean the title (remove emoji prefixes like 🎁)
    title = raw.get("title", "").strip()
    title = re.sub(r"^[🎁🌿💙✨☕]+\s*", "", title).strip()

    return CleanProduct(
        shopify_id=raw["id"],
        variant_id=first_variant.get("id"),
        title=title,
        handle=handle,
        description=strip_html(raw.get("body_html")),
        price=price,
        compare_at_price=compare_at_price,
        tags=raw.get("tags", []),
        product_type=raw.get("product_type", ""),
        vendor=raw.get("vendor", ""),
        sku=sku,
        available=available,
        image_url=image_url,
        url=url,
    )


def parse_all_products(raw_products: list[dict]) -> list[CleanProduct]:
    """Parse a list of raw Shopify products into CleanProduct objects."""
    products = []
    skipped = 0
    for raw in raw_products:
        product = parse_product(raw)
        # Skip free gift products (price = 0) — they clutter the graph
        if product.price <= 0 and "freebie" in " ".join(product.tags).lower():
            skipped += 1
            continue
        products.append(product)

    print(f"  Parsed {len(products)} products ({skipped} freebies skipped)")
    return products
