"""
Real Search Service using Tavily API

Replaces mock search with actual web search capabilities.
"""

from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from app.config import settings
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
    Extract product URLs from search results
    
    Args:
        search_results: List of Tavily search results
        
    Returns:
        List of product URLs
    """
    urls = []
    
    for result in search_results:
        url = result.get("url")
        if url and is_product_url(url):
            urls.append(url)
    
    return urls


def is_product_url(url: str) -> bool:
    """
    Check if URL is likely a product page
    
    Args:
        url: URL to check
        
    Returns:
        True if likely a product page
    """
    import re
    
    # Common product URL patterns
    product_patterns = [
        r"amazon\.com/.*/(dp|gp/product)/",
        r"bestbuy\.com/site/",
        r"walmart\.com/ip/",
        r"target\.com/p/",
        r"ebay\.com/itm/",
    ]
    
    for pattern in product_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    
    return False
