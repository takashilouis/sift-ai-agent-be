"""
Compare Agent Node - Real LLM Integration

Compares multiple products using Gemini LLM.
"""

from typing import Dict, Any, List
from app.agents.llm_router import run_llm, get_system_instruction
import json


async def compare_agent_node(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare multiple products using LLM
    
    Args:
        state: Current agent state
        task: Task configuration with 'from_task' (comma-separated task references)
        
    Returns:
        Comparison analysis
    """
    # Get product data from multiple previous tasks
    products = []
    
    if task.get("from_task"):
        from_task_refs = task["from_task"].split(",")
        task_results = state.get("task_results", {})
        
        for ref in from_task_refs:
            ref = ref.strip()
            if ":" in ref:
                task_idx = ref.split(":")[1]
                prev_result = task_results.get(task_idx, {})
                product_data = prev_result.get("product_data")
                
                if product_data:
                    products.append(product_data)
    
    if len(products) < 2:
        print(f"[Compare Agent] Need at least 2 products, got {len(products)}")
        return {"comparison": None, "error": "Insufficient products for comparison"}
    
    print(f"[Compare Agent] Comparing {len(products)} products")
    
    try:
        # Build comparison prompt
        products_json = json.dumps(products, indent=2)
        
        prompt = f"""Compare these products and provide a comprehensive analysis.

Products to Compare:
{products_json}

Create a detailed comparison that includes:

1. **Feature Comparison Matrix**
   - Create a table comparing key features across all products
   - Highlight unique features of each product

2. **Price Analysis**
   - Compare prices
   - Assess value for money
   - Identify best budget option and best premium option

3. **Quality Assessment**
   - Compare ratings and review counts
   - Assess build quality and reliability indicators
   - Identify highest quality option

4. **Use Case Recommendations**
   - Best for budget-conscious buyers
   - Best for premium features
   - Best overall value
   - Best for specific use cases

5. **Pros & Cons**
   - List pros and cons for each product

6. **Final Verdict**
   - Clear recommendation with reasoning
   - Winner in different categories

Format as markdown with tables where appropriate. Be objective and data-driven."""
        
        # Call LLM
        comparison = await run_llm(
            prompt=prompt,
            temperature=0.6,
            max_tokens=3000,
            system_instruction=get_system_instruction("compare")
        )
        
        # Extract product titles for summary
        product_titles = [p.get("title", "Unknown") for p in products]
        
        print(f"[Compare Agent] Comparison generated for: {', '.join(product_titles)}")
        
        return {
            "comparison": comparison.strip(),
            "products_compared": product_titles,
            "comparison_count": len(products)
        }
        
    except Exception as e:
        print(f"[Compare Agent] Error: {e}")
        return {"comparison": None, "error": str(e)}
