"""
Real Search Service using Tavily API

Replaces mock search with actual web search capabilities.
"""

from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from app.config import settings
from app.services.serpapi_service import (
    amazon_product_url,
    extract_asin,
    search_amazon_products,
    serpapi_enabled,
    should_use_amazon_search,
)
import asyncio


async def search_products(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for products using Tavily API
    
    Args:
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        List of search result dictionaries with url, title, content
        
    Raises:
        ValueError: If TAVILY_API_KEY is not configured
    """
    if should_use_amazon_search(query) and serpapi_enabled():
        try:
            return await search_amazon_products(query, max_results=max_results)
        except Exception as e:
            print(f"[Search Service] SerpAPI Amazon search failed, falling back to Tavily: {e}")

    if not settings.TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY is required but not configured")
    
    try:
        # Create Tavily client
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        
        # Run search in executor (Tavily client is synchronous)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_domains=["amazon.com", "bestbuy.com", "walmart.com", "target.com", "ebay.com"]
            )
        )
        
        # Extract results
        results = response.get("results", [])
        
        print(f"[Search Service] Found {len(results)} results for: {query}")
        
        return results
        
    except Exception as e:
        print(f"[Search Service] Error searching with Tavily: {e}")
        raise


async def search_product_reviews(product_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search for product reviews
    
    Args:
        product_name: Product name to search reviews for
        max_results: Maximum number of reviews
        
    Returns:
        List of review search results
    """
    if not settings.TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY is required but not configured")
    
    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        
        # Search for reviews
        query = f"{product_name} reviews ratings customer feedback"
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results
            )
        )
        
        results = response.get("results", [])
        
        print(f"[Search Service] Found {len(results)} review sources for: {product_name}")
        
        return results
        
    except Exception as e:
        print(f"[Search Service] Error searching reviews: {e}")
        raise


async def extract_product_urls(search_results: List[Dict[str, Any]]) -> List[str]:
    """
    Extract product URLs from search results.

    First tries to find strict individual product pages (e.g. /dp/ on Amazon).
    If none are found, falls back to accepting any URL from known e-commerce
    domains so the scraper always has something to work with.

    Args:
        search_results: List of Tavily search results

    Returns:
        List of product URLs
    """
    strict_urls = []
    fallback_urls = []

    known_domains = [
        "amazon.com", "bestbuy.com", "walmart.com", "target.com", "ebay.com"
    ]

    for result in search_results:
        url = result.get("url")
        asin = result.get("asin") or extract_asin(url or "")
        if asin:
            strict_urls.append(amazon_product_url(asin))
            continue

        if not url:
            continue
        if is_product_url(url):
            strict_urls.append(url)
        elif any(domain in url for domain in known_domains):
            fallback_urls.append(url)

    if strict_urls:
        return strict_urls

    # Fallback: return any URL from a known e-commerce domain
    print("[Search Service] No strict product URLs found — falling back to e-commerce domain URLs")
    return fallback_urls


def is_product_url(url: str) -> bool:
    """
    Check if URL is a specific product page (strict match).

    Args:
        url: URL to check

    Returns:
        True if URL points to a specific product page
    """
    import re

    product_patterns = [
        r"amazon\.com/.*/dp/",
        r"amazon\.com/dp/",
        r"amazon\.com/gp/product/",
        r"bestbuy\.com/site/",
        r"walmart\.com/ip/",
        r"walmart\.com/search",
        r"target\.com/p/",
        r"target\.com/s\?",
        r"ebay\.com/itm/",
        r"ebay\.com/sch/",
    ]

    for pattern in product_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True

    return False
