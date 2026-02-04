"""
Summarize Agent Node - Real LLM Integration

Generates product summaries using Gemini LLM.
"""

from typing import Dict, Any
from app.agents.llm_router import run_llm, get_system_instruction
import json


async def summarize_agent_node(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate product summary using LLM
    
    Args:
        state: Current agent state
        task: Task configuration with 'from_task'
        
    Returns:
        Summary text
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
        print("[Summarize Agent] No product data to summarize")
        state["agent_status"] = "error"
        state["agent_message"] = "No product data to summarize"
        return {"summary": None, "error": "No product data"}
    
    product_title = product_data.get('title', 'Unknown Product')
    print(f"[Summarize Agent] Generating summary for: {product_title}")
    
    # Emit summarization start status
    state["agent_status"] = "summarizing"
    state["agent_message"] = f"Generating summary for: {product_title}"
    
    # Determine model based on deep_research flag
    deep_research = state.get("deep_research", False)
    model_name = "gemini-3-pro-preview" if deep_research else None
    
    try:
        # Build prompt for LLM
        prompt = f"""Analyze this product and provide a comprehensive summary.

Product Information:
{json.dumps(product_data, indent=2)}

Create a summary that includes:
1. **Overview**: Brief introduction to the product
2. **Key Features**: Highlight 3-5 most important features
3. **Value Proposition**: What makes this product stand out
4. **Target Audience**: Who would benefit most from this product
5. **Pros & Cons**: Balanced assessment

Format as markdown with clear sections. Be concise but informative (300-400 words)."""
        
        # Call LLM
        summary = await run_llm(
            prompt=prompt,
            model=model_name,
            temperature=0.7,
            system_instruction=get_system_instruction("summarize")
        )
        
        print(f"[Summarize Agent] Summary generated ({len(summary)} chars)")
        
        # Emit summarization completion status
        state["agent_status"] = "completed"
        state["agent_message"] = f"Summary generated for: {product_title}"
        
        return {"summary": summary.strip()}
        
    except Exception as e:
        print(f"[Summarize Agent] Error: {e}")
        
        # Emit error status
        state["agent_status"] = "error"
        state["agent_message"] = f"Summarization failed: {str(e)}"
        
        return {"summary": None, "error": str(e)}
