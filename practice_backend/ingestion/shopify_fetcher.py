"""
Shopify Product Fetcher for Helio Veracity Practice Rewrite.
This module handles the extraction of raw data from the Shopify public API.
"""

import json
import httpx
from pathlib import Path
import asyncio

# Target Store Configuration
STORE_URL = "https://bluetea.co.in"
PRODUCTS_PER_PAGE = 250  # Shopify's API maximum
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

async def fetch_all_products(store_url: str = STORE_URL, limit: int = 50) -> list[dict]:
    """
    Fetches raw product data from the Shopify /products.json endpoint.
    Includes pagination logic to handle large catalogs.
    """
    all_products = []
    page = 1

    # 'async with' ensures the HTTP client is closed after use
    async with httpx.AsyncClient(timeout=30.0) as client:
        while len(all_products) < limit:
            url = f"{store_url}/products.json?limit={PRODUCTS_PER_PAGE}&page={page}"
            print(f"  [HTTP] Fetching page {page}: {url}")

            response = await client.get(url)
            # Standard error handling (detects 404, 500, etc.)
            response.raise_for_status()

            data = response.json()
            products = data.get("products", [])

            if not products:
                # No more products left to fetch
                break

            all_products.extend(products)
            page += 1

    # Return exactly what was requested
    result = all_products[:limit]
    print(f"  [OK] Successfully harvested {len(result)} products.")
    return result

def save_raw_products(products: list[dict], filename: str = "bluetea_raw.json") -> Path:
    """
    Saves the list of dictionaries to a local JSON file.
    This acts as our local cache for debugging and testing.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        # json.dump converts Python list/dict into a JSON string
        json.dump(products, f, ensure_ascii=False, indent=2)
        
    print(f"  [FILE] Saved raw data to {filepath}")
    return filepath

def load_raw_products(filename: str = "bluetea_raw.json") -> list[dict]:
    """Loads previously saved raw data."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"No cached data found at {filepath}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
