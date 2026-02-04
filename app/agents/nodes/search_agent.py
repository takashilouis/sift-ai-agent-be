"""
Search Agent Node - Real Tavily Integration

Searches for products using Tavily API based on task configuration.
"""

from typing import Dict, Any
from app.services.search_service import search_products, extract_product_urls


async def search_agent_node(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for products using Tavily API
    
    Args:
        state: Current agent state
        task: Task configuration with 'query'
        
    Returns:
        Search results (list of URLs and metadata)
    """
    query = task.get("query", state.get("query", ""))
    
    print(f"[Search Agent] Searching for: {query}")
    
    # Emit search start status
    state["agent_status"] = "searching"
    state["agent_message"] = f"Searching web for: {query}"
    
    try:
        # Perform search using Tavily
        search_results = await search_products(query, max_results=5)
        
        # Extract product URLs
        urls = await extract_product_urls(search_results)
        
        print(f"[Search Agent] Found {len(urls)} product URLs")
        
        # Emit search completion status
        state["agent_status"] = "completed"
        state["agent_message"] = f"Found {len(urls)} product URLs"
        
        return {
            "search_results": search_results,
            "product_urls": urls,
            "primary_url": urls[0] if urls else None,
            "results_count": len(urls)
        }
        
    except Exception as e:
        print(f"[Search Agent] Error: {e}")
        
        # Emit error status
        state["agent_status"] = "error"
        state["agent_message"] = f"Search failed: {str(e)}"
        
        return {
            "search_results": [],
            "product_urls": [],
            "primary_url": None,
            "error": str(e)
        }
