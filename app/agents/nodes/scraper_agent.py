"""
Scraper Agent Node - Real Playwright Integration

Scrapes product pages using Playwright with LLM-based extraction.
"""

from typing import Dict, Any
from app.services.playwright_service import scrape_product_page
import re


async def scraper_agent_node(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scrape product page using Playwright
    
    Args:
        state: Current agent state
        task: Task configuration with 'query' or 'from_task'
        
    Returns:
        Scraped product data
    """
    # Determine URL to scrape
    url = None
    
    # Check if URL is in task query
    if task.get("query"):
        query = task["query"]
        # Check if it's a URL
        url_pattern = r"(https?://[^\s]+)"
        match = re.search(url_pattern, query)
        if match:
            url = match.group(1)
    
    # Check if referencing previous task
    if not url and task.get("from_task"):
        from_task_ref = task["from_task"]
        task_results = state.get("task_results", {})
        
        # Parse task reference (e.g., "task:0")
        if ":" in from_task_ref:
            task_idx = from_task_ref.split(":")[1]
            prev_result = task_results.get(task_idx, {})
            
            # Get URL from previous task with optional index
            if "product_urls" in prev_result and isinstance(prev_result["product_urls"], list):
                urls = prev_result["product_urls"]
                # Check if task specifies an index
                url_index = task.get("url_index", 0)
                if 0 <= url_index < len(urls):
                    url = urls[url_index]
                else:
                    # Fallback to first if index out of bounds
                    url = urls[0] if urls else None
            else:
                # Fallback to single URL
                url = prev_result.get("primary_url") or prev_result.get("url")
    
    if not url:
        print("[Scraper Agent] No URL to scrape")
        state["agent_status"] = "error"
        state["agent_message"] = "No URL provided for scraping"
        return {"error": "No URL provided"}
    
    print(f"[Scraper Agent] Scraping URL: {url}")
    
    # Emit scraping start status
    state["agent_status"] = "scraping"
    state["agent_message"] = f"Scraping product page: {url}"
    
    try:
        # Scrape the product page
        product_data = await scrape_product_page(url, use_llm_extraction=True)
        
        product_title = product_data.get('title', 'Unknown Product')
        print(f"[Scraper Agent] Scraped: {product_title}")
        
        # Emit scraping completion status
        state["agent_status"] = "completed"
        state["agent_message"] = f"Extracted data for: {product_title}"
        
        return {
            "product_data": product_data,
            "url": url,
            "product_title": product_title
        }
        
    except Exception as e:
        print(f"[Scraper Agent] Error: {e}")
        
        # Emit error status
        state["agent_status"] = "error"
        state["agent_message"] = f"Scraping failed: {str(e)}"
        
        return {
            "product_data": None,
            "url": url,
            "error": str(e)
        }
