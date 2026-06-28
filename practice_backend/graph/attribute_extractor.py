"""
Attribute Extractor for Helio Veracity Practice Rewrite.
Uses Azure OpenAI to turn raw product text into semantic Graph data.
"""

import json
import os
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv

# Importing our 'Contract'
from practice_backend.models.schemas import CleanProduct, ExtractedAttributes

load_dotenv()

# The "Manual" for the AI - This defines our Knowledge Graph structure
EXTRACTION_PROMPT = """
You are a product data scientist specialized in herbal teas and Ayurveda.
Given the product details below, extract semantic attributes as a JSON object.

Product Title: {title}
Product Description: {description}
Tags: {tags}

Your output MUST be a valid JSON object with these keys:
- "ingredients": [list of herbs, flowers, or spices mentioned]
- "health_benefits": [specific benefits like 'Boosts immunity', 'Calms anxiety']
- "health_concerns": [issues it addresses like 'Sleep', 'Weight', 'Skin']
- "taste_profile": [flavor notes: 'floral', 'spicy', 'citrus']
- "caffeine_free": boolean (true/false)
- "usage_occasions": [when to drink: 'Before bed', 'After meals']

NOTE: 
1. If the description is missing, infer the ingredients from the Title. 
2. Standardize names: use 'Ginger', not 'Fresh Indian Ginger Root'.
3. Return ONLY the JSON object. No markdown code fences and no text.
"""

def get_azure_client() -> AzureOpenAI:
    """
    Initializes the Azure OpenAI client using environment variables.
    Think of this as establishing the 'API Session'.
    """
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

def extract_attributes_for_product(
    client: AzureOpenAI, 
    product: CleanProduct
) -> ExtractedAttributes:
    """
    Processes a single product. 
    It injects product data into the template, calls the LLM, and parses the JSON.
    """
    # Filling in the placeholders in our EXTRACTION_PROMPT
    prompt = EXTRACTION_PROMPT.format(
        title=product.title,
        description=product.description or "(No description available)",
        tags=", ".join(product.tags) if product.tags else "None"
    )

    # Calling the LLM (gpt-4o-mini)
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You are a professional tea data analyst. Return ONLY JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1, # Keep it factual, not creative
        max_tokens=800
    )

    # Extracting the text content
    content = response.choices[0].message.content.strip()
    
    # We use json.loads to turn the string back into a Python object
    try:
        attrs = json.loads(content)
        # We use **attrs to 'unpack' the dictionary into our Pydantic schema
        return ExtractedAttributes(shopify_id=product.shopify_id, **attrs)
    except Exception as e:
        print(f"  [ERROR] Failed to parse attributes for {product.title}: {e}")
        return ExtractedAttributes(shopify_id=product.shopify_id)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

def extract_all_attributes(
    products: list[CleanProduct], 
    use_cache: bool = True
) -> list[ExtractedAttributes]:
    """
    Orchestrates the extraction process for all products.
    Includes a caching layer to avoid redundant and expensive LLM calls.
    """
    cache_path = DATA_DIR / "extracted_attributes.json"

    # Step 1: Check the Cache
    if use_cache and cache_path.exists():
        print(f"  [CACHE] Found existing intelligence at {cache_path}. Loading...")
        with open(cache_path, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
        return [ExtractedAttributes(**item) for item in cached_data]

    # Step 2: Call the Brain for each product
    print(f"  [AI] No cache found. Extracting intelligence for {len(products)} products...")
    client = get_azure_client()
    all_attributes = []
    
    for product in products:
        print(f"  [AI] Analyzing: {product.title}...")
        results = extract_attributes_for_product(client, product)
        all_attributes.append(results)

    # Step 3: Save results to Cache
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        # model_dump() is a Pydantic method that turns the object into a simple Dict
        json.dump([a.model_dump() for a in all_attributes], f, ensure_ascii=False, indent=2)
    
    print(f"  [CACHE] Intelligence saved for future use.")
    return all_attributes
