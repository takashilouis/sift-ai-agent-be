"""
Final Report Agent Node

Synthesizes all task results into a comprehensive final report using LLM.
"""

from typing import Dict, Any
from app.agents.llm_router import run_llm
from app.services.database_service import DatabaseService
import json
from datetime import datetime


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
    session_id = state.get("session_id")
    deep_research = state.get("deep_research", False)
    report_id = state.get("report_id")
    
    print(f"[Final Report] Synthesizing all results into final report (Deep Research: {deep_research})")
    
    try:
        # Extract URLs and images from task results for evidence section
        urls = []
        product_images = {}  # {product_name: image_url}
        
        for task_idx, result in task_results.items():
            if isinstance(result, dict):
                # Extract URLs from search results
                if "results" in result and isinstance(result["results"], list):
                    for item in result["results"]:
                        if isinstance(item, dict):
                            if "url" in item:
                                urls.append(item["url"])
                            # Extract images from Tavily results if available
                            if "title" in item and "image" in item and item["image"]:
                                product_images[item["title"]] = item["image"]
                                
                # Extract URL from scrape results
                if "url" in result:
                    urls.append(result["url"])
                # Extract images from scraped product data
                if "product_data" in result and isinstance(result["product_data"], dict):
                    product_data = result["product_data"]
                    product_name = product_data.get("title", "Product")
                    images = product_data.get("images", [])
                    if images and len(images) > 0:
                        # Use first image
                        product_images[product_name] = images[0]
        
        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(urls))
        
        # Build URL evidence section
        url_evidence = "\n".join([f"- {url}" for url in unique_urls[:10]])  # Limit to 10 URLs
        
        # Serialize task results and truncate if too large to prevent massive context
        task_results_json = json.dumps(task_results, indent=2)
        if len(task_results_json) > 50000:
            print(f"[Final Report] Truncating task results from {len(task_results_json)} to 50000 chars")
            task_results_json = task_results_json[:50000] + "\n... [truncated]"

        # Determine target length and model based on mode
        target_length = "1100-2000 words" if deep_research else "700-1600 words"
        model_name = "gemini-2.5-pro" if deep_research else None  # None uses default (Flash)
        
        # Build comprehensive prompt with explicit guidelines
        prompt = f"""Current Date: {datetime.now().strftime('%B %d, %Y')}

Create a comprehensive research report based on the following analysis.

**Original Query:** {query}

**Research Plan:**
{json.dumps(plan, indent=2)}

**Analysis Results:**
{task_results_json}

**Product Images Available:**
{json.dumps(product_images, indent=2) if product_images else "No images available"}

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
    - Format as: "Product Name - $XX.XX (**[Amazon](URL)**)\" with bold blue link
    - For features: "Feature description (**[Best Buy](URL)**)"
    - For pricing: "$XX.XX at **[Target](URL)**"
    - Make retailer names BOLD and use markdown links: **[RetailerName](URL)**
    - Examples:
      * "Matcha Whisk Set - $15.99 (**[Amazon](https://amazon.com/...)**)"
      * "Enhanced ANC feature (**[Best Buy](https://bestbuy.com/...)**)"
      * "$219.99 at **[Target](https://target.com/...)**"
11. **Product Images**: When product images are available in the "Product Images Available" section above:
    - Include images in the Product Overview section using markdown image syntax
    - Format: ![Product Name](image_url)
    - Place images near the product description
    - For product comparisons, show images in a markdown table for side-by-side display
    - Example single product: ![Apple AirPods Pro](https://example.com/airpods.jpg)
    - Example comparison table:
      | Product A | Product B |
      |-----------|-----------|
      | ![Product A](url1) | ![Product B](url2) |
      | Description A | Description B |

Create a professional research report with the following structure:

# Product Research Report

## Product Overview
[If product images are available, display them here in a row using markdown:
![Product Name](image_url) ![Product Name 2](image_url2)
This gives users a visual overview of the products being compared/analyzed]

[Then continue with the product overview text...]
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

**IMPORTANT:** Only include the Sentiment Analysis section if you have actual review or sentiment data. If no sentiment data is available, skip this section entirely.

## Comparison
How this product compares to alternatives (if comparison data exists)

**IMPORTANT:** Only include the Comparison section if you have actual comparison data or information about alternative products. If no comparison data is available, skip this section entirely.

## Recommendations
- Who might benefit from this product (based on features found)
- Best use cases (based on specifications)
- Value assessment (based on pricing and features)

## Conclusion
Summary of findings based on the collected data

## References
List of all sources used in this report:
{url_evidence if url_evidence else "- No URLs available"}

**FORMATTING:**
- Use markdown formatting
- Use bullet points for lists
- Use tables for comparisons (markdown table format)
- Be comprehensive but concise
- Total length: {target_length}
- Include the References section with all URLs at the very end
- **CRITICAL:** Do NOT include sections marked as "IMPORTANT" if you don't have the relevant data. Simply omit those sections from the report."""
        
        # Generate final report
        final_report = await run_llm(
            prompt=prompt,
            model=model_name,
            temperature=0.7,
            max_tokens=18000
        )
        
        print(f"[Final Report] Report generated ({len(final_report)} chars)")
        
        # Safeguard: Truncate if absurdly long (prevent UI crash)
        if len(final_report) > 24000:
             print(f"[Final Report] WARNING: Report too long ({len(final_report)} chars). Truncating to 24000.")
             final_report = final_report[:24000] + "\n\n[Report truncated due to excessive length]"
        
        # Save report to database
        try:
            print(f"[Final Report] Saving report to database (session_id: {session_id}, report_id: {report_id})...")
            db = DatabaseService()
            await db.save_report(query=query, content=final_report, session_id=session_id, report_id=report_id)
            print("[Final Report] Report saved to database")
            await db.close()
        except Exception as e:
            print(f"[Final Report] Error saving to database: {e}")

        return {"final_report": final_report.strip()}
        
    except Exception as e:
        print(f"[Final Report] Error: {e}")
        return {"final_report": None, "error": str(e)}
