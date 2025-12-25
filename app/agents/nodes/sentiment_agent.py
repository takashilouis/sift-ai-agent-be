"""
Sentiment Agent Node - Real LLM Integration

Analyzes product sentiment using Gemini with structured output.
"""

from typing import Dict, Any, List, Literal
from pydantic import BaseModel, Field
from app.agents.llm_router import run_llm_structured, get_system_instruction
import json


class SentimentAnalysis(BaseModel):
    """Structured sentiment analysis output"""
    overall: Literal["positive", "neutral", "negative"]
    score: float = Field(..., ge=0, le=1, description="Sentiment score 0-1")
    positive_percentage: int = Field(..., ge=0, le=100)
    neutral_percentage: int = Field(..., ge=0, le=100)
    negative_percentage: int = Field(..., ge=0, le=100)
    key_positive_themes: List[str] = Field(default_factory=list)
    key_negative_themes: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    analysis_summary: str


async def sentiment_agent_node(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze product sentiment using LLM
    
    Args:
        state: Current agent state
        task: Task configuration with 'from_task'
        
    Returns:
        Sentiment analysis results
    """
    # Get product data from previous task
    product_data = None
    
    if task.get("from_task"):
        from_task_ref = task["from_task"]
        task_results = state.get("task_results", {})
        
        # Parse task reference
        if ":" in from_task_ref:
            task_idx = from_task_ref.split(":")[1]
            prev_result = task_results.get(task_idx, {})
            product_data = prev_result.get("product_data")
    
    if not product_data:
        print("[Sentiment Agent] No product data for analysis")
        state["agent_status"] = "error"
        state["agent_message"] = "No product data for sentiment analysis"
        return {"sentiment": None, "error": "No product data"}
    
    product_title = product_data.get('title', 'Unknown Product')
    print(f"[Sentiment Agent] Analyzing sentiment for: {product_title}")
    
    # Emit sentiment analysis start status
    state["agent_status"] = "analyzing"
    state["agent_message"] = f"Analyzing sentiment for: {product_title}"
    
    try:
        # Build prompt for sentiment analysis
        prompt = f"""Analyze the sentiment for this product based on all available information.

Product Data:
{json.dumps(product_data, indent=2)}

Perform a comprehensive sentiment analysis considering:
- Product rating and review count
- Product features and description
- Price positioning
- Availability
- Overall value proposition

Determine:
1. Overall sentiment (positive/neutral/negative)
2. Sentiment score (0.0 to 1.0, where 1.0 is most positive)
3. Percentage breakdown (positive/neutral/negative must sum to 100)
4. Key positive themes (list of 3-5 items)
5. Key negative themes (list of 3-5 items)
6. Confidence in analysis (0.0 to 1.0)
7. Brief analysis summary

Be objective and data-driven."""
        
        # Call LLM with structured output
        sentiment = await run_llm_structured(
            prompt=prompt,
            response_model=SentimentAnalysis,
            temperature=0.5,
            system_instruction=get_system_instruction("sentiment")
        )
        
        print(f"[Sentiment Agent] Sentiment: {sentiment.overall} (score: {sentiment.score})")
        
        # Emit sentiment analysis completion status
        state["agent_status"] = "completed"
        state["agent_message"] = f"Sentiment analysis completed: {sentiment.overall}"
        
        return {
            "sentiment": sentiment.model_dump(),
            "rating": product_data.get("rating"),
            "review_count": product_data.get("review_count")
        }
        
    except Exception as e:
        print(f"[Sentiment Agent] Error: {e}")
        
        # Emit error status
        state["agent_status"] = "error"
        state["agent_message"] = f"Sentiment analysis failed: {str(e)}"
        
        return {"sentiment": None, "error": str(e)}
