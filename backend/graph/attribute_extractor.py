"""Extract semantic attributes from products using Azure OpenAI GPT-4o."""

import json
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv
import os

from backend.models.schemas import CleanProduct, ExtractedAttributes

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

EXTRACTION_PROMPT = """You are analyzing a product from an herbal tea e-commerce store called Blue Tea (India).
Given the product data below, extract structured semantic attributes.

Product Title: {title}
Product Description: {description}
Tags: {tags}
Product Type: {product_type}
Price: ₹{price}

Extract the following as a JSON object. Be thorough — infer from context where the description is sparse.
For a tea product with no description, infer likely ingredients and benefits from the product title.

{{
  "ingredients": ["list every ingredient, herb, spice, or flower mentioned or implied"],
  "health_benefits": ["specific health benefits like 'Reduces bloating', 'Boosts metabolism'"],
  "health_concerns": ["health issues this product addresses: 'Digestive issues', 'Weight management', 'Skin health'"],
  "taste_profile": ["flavor descriptors: 'earthy', 'floral', 'spicy', 'minty', 'citrusy'"],
  "caffeine_free": true or false,
  "usage_occasions": ["when to drink: 'Morning routine', 'After meals', 'Before bed', 'Post-workout'"],
  "dietary_tags": ["keto-friendly', 'vegan', 'sugar-free', etc."],
  "target_audience": ["who benefits most: 'Weight-conscious adults', 'People with acidity', 'Fitness enthusiasts'"],
  "use_cases": ["broader use cases: 'Daily detox', 'Weight loss journey', 'Stress relief', 'Gift giving'"]
}}

Return ONLY the JSON object, no markdown formatting, no explanation."""


def get_azure_client() -> AzureOpenAI:
    """Initialize Azure OpenAI client from environment variables."""
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def extract_attributes_for_product(
    client: AzureOpenAI,
    product: CleanProduct,
    deployment: str = None,
) -> ExtractedAttributes:
    """Use Azure OpenAI to extract semantic attributes from a single product."""
    deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    prompt = EXTRACTION_PROMPT.format(
        title=product.title,
        description=product.description or "(No description available)",
        tags=", ".join(product.tags) if product.tags else "(No tags)",
        product_type=product.product_type or "(Not specified)",
        price=product.price,
    )

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are a product data analyst specializing in herbal teas and wellness products. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,  # Low temperature for consistent extraction
        max_tokens=800,
    )

    content = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    try:
        attrs = json.loads(content)
    except json.JSONDecodeError:
        print(f"  ⚠ Failed to parse JSON for '{product.title}', using defaults")
        attrs = {}

    return ExtractedAttributes(
        shopify_id=product.shopify_id,
        ingredients=attrs.get("ingredients", []),
        health_benefits=attrs.get("health_benefits", []),
        health_concerns=attrs.get("health_concerns", []),
        taste_profile=attrs.get("taste_profile", []),
        caffeine_free=attrs.get("caffeine_free", True),
        usage_occasions=attrs.get("usage_occasions", []),
        dietary_tags=attrs.get("dietary_tags", []),
        target_audience=attrs.get("target_audience", []),
        use_cases=attrs.get("use_cases", []),
    )


def extract_all_attributes(
    products: list[CleanProduct],
    use_cache: bool = True,
) -> list[ExtractedAttributes]:
    """
    Extract attributes for all products. Caches results to avoid re-calling the API.
    """
    cache_path = DATA_DIR / "extracted_attributes.json"

    # Try loading from cache first
    if use_cache and cache_path.exists():
        print("  Loading cached extracted attributes...")
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        return [ExtractedAttributes(**item) for item in cached]

    print(f"  Extracting attributes for {len(products)} products via Azure OpenAI...")
    client = get_azure_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    all_attributes = []
    for i, product in enumerate(products):
        print(f"  [{i + 1}/{len(products)}] Extracting: {product.title[:60]}...")
        try:
            attrs = extract_attributes_for_product(client, product, deployment)
            all_attributes.append(attrs)
        except Exception as e:
            print(f"  ⚠ Error extracting '{product.title}': {e}")
            all_attributes.append(ExtractedAttributes(shopify_id=product.shopify_id))

    # Cache results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump([a.model_dump() for a in all_attributes], f, ensure_ascii=False, indent=2)
    print(f"  Saved extracted attributes to {cache_path}")

    return all_attributes
