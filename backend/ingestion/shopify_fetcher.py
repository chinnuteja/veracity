"""Fetch product data from a Shopify store's public products.json endpoint."""

import json
import httpx
from pathlib import Path

from backend.models.schemas import CleanProduct


STORE_URL = "https://bluetea.co.in"
PRODUCTS_PER_PAGE = 250  # Shopify max
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


async def fetch_all_products(store_url: str = STORE_URL, limit: int = 50) -> list[dict]:
    """
    Fetch products from the Shopify public /products.json endpoint.
    Paginates until we have `limit` products or no more pages.
    """
    all_products = []
    page = 1

    async with httpx.AsyncClient(timeout=30.0) as client:
        while len(all_products) < limit:
            url = f"{store_url}/products.json?limit={PRODUCTS_PER_PAGE}&page={page}"
            print(f"  Fetching page {page}: {url}")

            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            products = data.get("products", [])

            if not products:
                break

            all_products.extend(products)
            page += 1

    # Trim to requested limit
    all_products = all_products[:limit]
    print(f"  Fetched {len(all_products)} products from {store_url}")
    return all_products


def save_raw_products(products: list[dict], filename: str = "bluetea_raw.json") -> Path:
    """Save raw product JSON to data directory for caching/reproducibility."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(products)} products to {filepath}")
    return filepath


def load_raw_products(filename: str = "bluetea_raw.json") -> list[dict]:
    """Load previously cached raw product JSON."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"No cached data at {filepath}. Run fetch first.")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
