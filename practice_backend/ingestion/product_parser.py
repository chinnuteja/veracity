"""
Product Parser for Helio Veracity Practice Rewrite.
Cleans raw Shopify JSON and prepares it for the AI Extractor.
"""

import re
from bs4 import BeautifulSoup
from practice_backend.models.schemas import CleanProduct

STORE_URL = "https://bluetea.co.in"

def strip_html(html_string: str | None) -> str:
    """
    Remove HTML tags and clean up whitespace from descriptions.
    In Java, this would be a manual Regex loop; here we use BeautifulSoup.
    """
    if not html_string:
        return ""
        
    soup = BeautifulSoup(html_string, "html.parser")
    # separator=" " ensures words don't get stuck together when tags vanish
    text = soup.get_text(separator=" ", strip=True)
    
    # Collapse multiple spaces or newlines into a single space
    return re.sub(r"\s+", " ", text).strip()

def parse_product(raw: dict) -> CleanProduct:
    """
    Transforms a single raw Shopify product dictionary into a CleanProduct object.
    Identifies the primary price, cleans the title, and strips HTML.
    """
    # 1. Clean the Title
    # Removes common emojis used by this brand in titles
    title = raw.get("title", "").strip()
    title = re.sub(r"^[🎁🌿💙✨☕]+\s*", "", title).strip()

    # 2. Get the Price
    # We look at the first available variant for the base price
    variants = raw.get("variants", [])
    raw_price = variants[0].get("price", "0.0") if variants else "0.0"
    try:
        price = float(raw_price)
    except:
        price = 0.0

    # 3. Get the Image
    images = raw.get("images", [])
    image_url = images[0]["src"] if images else ""

    # 4. Construct the Pydantic Object
    return CleanProduct(
        shopify_id=raw["id"],
        title=title,
        description=strip_html(raw.get("body_html", "")),
        tags=raw.get("tags", []),
        product_type=raw.get("product_type", ""),
        price=price,
        image_url=image_url
    )

def parse_all_products(raw_products: list[dict]) -> list[CleanProduct]:
    """
    Loops through the entire raw catalog and returns a list of cleaned products.
    """
    cleaned_list = [parse_product(p) for p in raw_products]
    print(f"  [OK] Cleaned {len(cleaned_list)} products.")
    return cleaned_list
