from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from app.services import search_service, playwright_service
from pydantic import BaseModel

router = APIRouter(
    prefix="/debug",
    tags=["debug"]
)

class SearchRequest(BaseModel):
    query: str
    max_results: int = 5

@router.post("/search")
async def debug_search(request: SearchRequest) -> Dict[str, Any]:
    """
    Debug endpoint to search using Tavily API directly.
    """
    try:
        results = await search_service.search_products(
            query=request.query,
            max_results=request.max_results
        )
        return {
            "query": request.query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ScrapeRequest(BaseModel):
    url: str

@router.post("/scrape")
async def debug_scrape(request: ScrapeRequest) -> Dict[str, Any]:
    """
    Debug endpoint to scrape a URL using Playwright directly.
    """
    try:
        # Use scrape_product_page from playwright_service
        # Note: The service function is scrape_product_page, not scrape_product
        result = await playwright_service.scrape_product_page(request.url)
        return {
            "url": request.url,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
