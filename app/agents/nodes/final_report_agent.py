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
        # Extract URLs from task results for evidence section
        urls = []
        for task_idx, result in task_results.items():
            if isinstance(result, dict):
                # Extract URLs from search results
                if "results" in result and isinstance(result["results"], list):
                    for item in result["results"]:
                        if isinstance(item, dict) and "url" in item:
                            urls.append(item["url"])
                # Extract URL from scrape results
                if "url" in result:
                    urls.append(result["url"])
        
        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(urls))
        
        # Build URL evidence section
        url_evidence = "\n".join([f"- {url}" for url in unique_urls[:10]])  # Limit to 10 URLs
        
        # Serialize task results and truncate if too large to prevent massive context
        task_results_json = json.dumps(task_results, indent=2)
        if len(task_results_json) > 50000:
            print(f"[Final Report] Truncating task results from {len(task_results_json)} to 50000 chars")
            task_results_json = task_results_json[:50000] + "\n... [truncated]"

        # Build comprehensive prompt with explicit guidelines
        prompt = f"""Create a comprehensive research report based on the following analysis.

**Original Query:** {query}

**Research Plan:**
{json.dumps(plan, indent=2)}

**Analysis Results:**
{task_results_json}

**CRITICAL GUIDELINES - READ CAREFULLY:**
1. Focus ONLY on actual data found in the analysis results above
2. Do NOT make claims about whether a product exists or doesn't exist
3. If the search results show the product in retail listings, report on those findings
4. Present features, pricing, and reviews that WERE found in the data
5. If data is limited, acknowledge it but still present what WAS found
6. Use objective, factual language - avoid speculation or assumptions
7. Do NOT conclude that a product is "hypothetical" or "doesn't exist" based on limited data
8. If you see placeholder listings or future dates, simply note them as observations, not proof of non-existence
9. Present the information as a product research report, not a product existence investigation
10. **IMPORTANT**: Include inline URL citations with bold retailer names
    - Extract the retailer/website name from the URL (e.g., Amazon, Best Buy, Target, eBay)
    - Format as: "Product Name - $XX.XX (**[Amazon](URL)**)" with bold blue link
    - For features: "Feature description (**[Best Buy](URL)**)"
    - For pricing: "$XX.XX at **[Target](URL)**"
    - Make retailer names BOLD and use markdown links: **[RetailerName](URL)**
    - Examples:
      * "Matcha Whisk Set - $15.99 (**[Amazon](https://amazon.com/...)**)"
      * "Enhanced ANC feature (**[Best Buy](https://bestbuy.com/...)**)"
      * "$219.99 at **[Target](https://target.com/...)**"

Create a professional research report with the following structure:

# Product Research Report

## Executive Summary
Brief overview of findings based on the data collected (2-3 paragraphs)
- Summarize key features found
- Mention pricing information discovered
- Note any standout characteristics

## Product Overview
Detailed product information based on search results and scraped data
- Features and specifications found
- Design and build quality mentions
- Technical specifications

## Key Findings
- Main insights from the analysis
- Important features and specifications discovered
- Pricing information from various sources
- Availability information found

## Sentiment Analysis
Customer sentiment and satisfaction levels (if review data was collected)
- Overall sentiment
- Common positive feedback
- Common concerns or criticisms

## Comparison (if applicable)
How this product compares to alternatives (if comparison data exists)

## Recommendations
- Who might benefit from this product (based on features found)
- Best use cases (based on specifications)
- Value assessment (based on pricing and features)

## Sources & Evidence
List all URLs where information was gathered:
{url_evidence if url_evidence else "- No URLs available"}

## Conclusion
Summary of findings based on the collected data

**FORMATTING:**
- Use markdown formatting
- Use bullet points for lists
- Use tables for comparisons (markdown table format)
- Be comprehensive but concise
- Total length: 600-1500 words
- Include the Sources & Evidence section with all URLs"""
        
        # Generate final report
        final_report = await run_llm(
            prompt=prompt,
            temperature=0.7,
            max_tokens=17000
        )
        
        print(f"[Final Report] Report generated ({len(final_report)} chars)")
        
        # Safeguard: Truncate if absurdly long (prevent UI crash)
        if len(final_report) > 20000:
             print(f"[Final Report] WARNING: Report too long ({len(final_report)} chars). Truncating to 20000.")
             final_report = final_report[:20000] + "\n\n[Report truncated due to excessive length]"
        
        return {"final_report": final_report.strip()}
        
    except Exception as e:
        print(f"[Final Report] Error: {e}")
        return {"final_report": None, "error": str(e)}
