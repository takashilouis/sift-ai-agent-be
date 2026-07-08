"""
SerpAPI integration for Amazon-specific product discovery and product data.

Tavily remains useful for broad web research, but Amazon search/product pages are
better handled through a structured provider that returns ASINs and normalized
product metadata.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs
import re

import httpx

from app.config import settings


SERPAPI_BASE_URL = "https://serpapi.com/search.json"
ASIN_PATTERN = re.compile(r"\bB[0-9A-Z]{9}\b", re.IGNORECASE)


def serpapi_enabled() -> bool:
    return bool(settings.SERPAPI_API_KEY)


def should_use_amazon_search(query: str) -> bool:
    query_lower = query.lower()
    return (
        "amazon" in query_lower
        or "asin" in query_lower
        or extract_asin(query) is not None
        or "amazon.com" in query_lower
    )


def extract_asin(value: str) -> Optional[str]:
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.netloc and "amazon." in parsed.netloc:
        path_patterns = [
            r"/dp/([A-Z0-9]{10})",
            r"/gp/product/([A-Z0-9]{10})",
            r"/product/([A-Z0-9]{10})",
        ]
        for pattern in path_patterns:
            match = re.search(pattern, parsed.path, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        query_asin = parse_qs(parsed.query).get("asin")
        if query_asin:
            return query_asin[0].upper()

    match = ASIN_PATTERN.search(value.upper())
    return match.group(0).upper() if match else None


def is_amazon_url_or_asin(value: str) -> bool:
    return bool(extract_asin(value) or "amazon." in value.lower())


def amazon_product_url(asin: str) -> str:
    return f"https://www.amazon.com/dp/{asin}"


async def search_amazon_products(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    if not settings.SERPAPI_API_KEY:
        raise ValueError("SERPAPI_API_KEY is required for Amazon search")

    params = {
        "engine": "amazon",
        "amazon_domain": settings.SERPAPI_AMAZON_DOMAIN,
        "k": query,
        "api_key": settings.SERPAPI_API_KEY,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(SERPAPI_BASE_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    organic_results = payload.get("organic_results") or []
    results: List[Dict[str, Any]] = []

    for item in organic_results[:max_results]:
        asin = item.get("asin") or extract_asin(item.get("link", ""))
        if not asin:
            continue

        link = item.get("link") or amazon_product_url(asin)
        price = _format_price(item.get("price")) or item.get("price") or item.get("extracted_price")
        rating = _parse_float(item.get("rating"))
        reviews = _parse_int(item.get("reviews") or item.get("reviews_total"))

        results.append({
            "title": item.get("title") or f"Amazon product {asin}",
            "url": link,
            "link": link,
            "content": _search_result_content(item, price, rating, reviews),
            "source": "serpapi_amazon_search",
            "asin": asin,
            "thumbnail": item.get("thumbnail"),
            "image": item.get("thumbnail"),
            "price": price,
            "rating": rating,
            "reviews": reviews,
            "position": item.get("position"),
        })

    print(f"[SerpAPI Service] Found {len(results)} Amazon ASIN results for: {query}")
    return results


async def get_amazon_product(asin_or_url: str) -> Dict[str, Any]:
    if not settings.SERPAPI_API_KEY:
        raise ValueError("SERPAPI_API_KEY is required for Amazon product lookup")

    asin = extract_asin(asin_or_url)
    if not asin:
        raise ValueError(f"Could not extract Amazon ASIN from: {asin_or_url}")

    params = {
        "engine": "amazon_product",
        "amazon_domain": settings.SERPAPI_AMAZON_DOMAIN,
        "asin": asin,
        "api_key": settings.SERPAPI_API_KEY,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(SERPAPI_BASE_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    product = payload.get("product_results") or {}
    if not product:
        raise ValueError(f"SerpAPI returned no product_results for ASIN {asin}")

    mapped_product = map_amazon_product_response(product, asin)
    print(f"[SerpAPI Service] Loaded Amazon product {asin}: {mapped_product.get('title')}")
    return mapped_product


def map_amazon_product_response(product: Dict[str, Any], asin: str) -> Dict[str, Any]:
    images = _extract_images(product)
    categories = product.get("categories") or []
    features = (
        product.get("feature_bullets")
        or product.get("feature")
        or product.get("features")
        or []
    )
    if isinstance(features, str):
        features = [features]

    product_information = product.get("product_information") or {}
    brand = product.get("brand") or product_information.get("Brand")
    category = " > ".join(categories) if isinstance(categories, list) else categories
    price = _format_price(product.get("price")) or _format_price(product.get("buybox_winner", {}).get("price"))

    return {
        "url": product.get("link") or amazon_product_url(asin),
        "title": product.get("title"),
        "price": price,
        "rating": _parse_float(product.get("rating")),
        "review_count": _parse_int(
            product.get("reviews_total")
            or product.get("ratings_total")
            or product.get("review_count")
        ),
        "features": features[:8],
        "description": product.get("description") or product.get("product_description"),
        "availability": product.get("availability") or product.get("stock"),
        "brand": brand,
        "category": category,
        "images": images[:10],
        "reviews": _extract_reviews(product),
        "asin": asin,
        "source": "serpapi_amazon_product",
    }


def _extract_images(product: Dict[str, Any]) -> List[str]:
    images: List[str] = []

    for key in ("images", "media"):
        value = product.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    images.append(item)
                elif isinstance(item, dict):
                    image_url = item.get("link") or item.get("url") or item.get("thumbnail")
                    if image_url:
                        images.append(image_url)

    for key in ("main_image", "thumbnail"):
        value = product.get(key)
        if value:
            images.append(value)

    return list(dict.fromkeys(images))


def _extract_reviews(product: Dict[str, Any]) -> List[str]:
    reviews = product.get("top_reviews") or product.get("reviews") or []
    if not isinstance(reviews, list):
        return []

    extracted_reviews = []
    for review in reviews[:5]:
        if isinstance(review, str):
            extracted_reviews.append(review)
        elif isinstance(review, dict):
            text = review.get("body") or review.get("text") or review.get("snippet") or review.get("title")
            if text:
                extracted_reviews.append(text)

    return extracted_reviews


def _format_price(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return f"${value}"
    if isinstance(value, dict):
        return value.get("raw") or value.get("text") or value.get("price")
    return None


def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            match = re.search(r"\d+(?:\.\d+)?", value)
            return float(match.group(0)) if match else None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            match = re.search(r"[\d,]+", value)
            return int(match.group(0).replace(",", "")) if match else None
        return int(value)
    except (TypeError, ValueError):
        return None


def _search_result_content(
    item: Dict[str, Any],
    price: Optional[str],
    rating: Optional[float],
    reviews: Optional[int],
) -> str:
    details = []
    if price:
        details.append(f"Price: {price}")
    if rating:
        details.append(f"Rating: {rating}/5")
    if reviews:
        details.append(f"Reviews: {reviews}")
    if item.get("delivery"):
        details.append(f"Delivery: {item['delivery']}")

    return " | ".join(details) or item.get("title", "")
