from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any


class ResearchResponse(BaseModel):
    """Schema for streaming research response"""
    step: str = Field(..., description="Current step in the research workflow")
    state: Dict[str, Any] = Field(..., description="Current state of the research")
    
    class Config:
        json_schema_extra = {
            "example": {
                "step": "planner",
                "state": {
                    "query": "Apple AirPods 4",
                    "plan": {
                        "intent": "product_research",
                        "tasks": [...]
                    }
                }
            }
        }


class FinalResearchReport(BaseModel):
    """Final compiled research report"""
    query: str
    plan: Optional[Dict[str, Any]] = None
    task_results: Dict[str, Any] = Field(default_factory=dict)
    final_report: Optional[str] = None
    error: Optional[str] = None
    
    # Legacy fields for backward compatibility
    url: Optional[str] = None
    product_data: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    sentiment: Optional[Dict[str, Any]] = None
    comparison: Optional[str] = None
    search_results: Optional[List[str]] = None
