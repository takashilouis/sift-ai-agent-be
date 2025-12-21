from tavily import TavilyClient
from app.config import settings
from typing import List, Dict, Any

class TavilyService:
    def __init__(self):
        if not settings.TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY is required but not configured")
        self.client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search the web using Tavily API
        """
        try:
            response = self.client.search(
                query=query,
                search_depth="advanced",
                include_images=True,
                max_results=max_results
            )
            return response.get("results", [])
        except Exception as e:
            print(f"[Tavily Service] Error searching: {e}")
            return []
