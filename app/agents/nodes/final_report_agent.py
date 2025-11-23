"""
Final Report Agent Node

Synthesizes all task results into a comprehensive final report using LLM.
"""

from typing import Dict, Any
from app.agents.llm_router import run_llm
import json


async def final_report_node(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate final research report synthesizing all results
    
    Args:
        state: Current agent state with all task results
        task: Task configuration
        
    Returns:
        Final report text
    """
    query = state.get("query", "")
    plan = state.get("plan", {})
    task_results = state.get("task_results", {})
    
    print("[Final Report] Synthesizing all results into final report")
    
    try:
        # Build comprehensive prompt
        prompt = f"""Create a comprehensive research report based on the following analysis.

**Original Query:** {query}

**Research Plan:**
{json.dumps(plan, indent=2)}

**Analysis Results:**
{json.dumps(task_results, indent=2)}

Create a professional research report with the following structure:

# Product Research Report

## Executive Summary
Brief overview of findings (2-3 paragraphs)

## Product Overview
Detailed product information

## Key Findings
- Main insights from the analysis
- Important features and specifications
- Pricing and value assessment

## Sentiment Analysis
Customer sentiment and satisfaction levels

## Comparison (if applicable)
How this product compares to alternatives

## Recommendations
- Who should buy this product
- Best use cases
- Value assessment
- Final verdict

## Conclusion
Summary and final thoughts

Format as markdown. Be comprehensive but concise. Use bullet points and tables where appropriate.
Total length: 500-800 words."""
        
        # Generate final report
        final_report = await run_llm(
            prompt=prompt,
            temperature=0.7,
            max_tokens=4000
        )
        
        print(f"[Final Report] Report generated ({len(final_report)} chars)")
        
        return {"final_report": final_report.strip()}
        
    except Exception as e:
        print(f"[Final Report] Error: {e}")
        return {"final_report": None, "error": str(e)}
