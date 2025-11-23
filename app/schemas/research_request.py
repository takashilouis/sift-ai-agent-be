from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """Schema for incoming research requests"""
    query: str = Field(..., description="The research query or product to analyze")
    mode: str = Field(
        default="product-analysis",
        description="Research mode: product-analysis, comparison, sentiment-check"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "research this product: Apple AirPods 4",
                "mode": "product-analysis"
            }
        }
