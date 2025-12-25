"""
LLM-based Planner Agent

This module contains the planner agent that uses Gemini to analyze user queries
and generate structured task plans for the research workflow.
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
import google.generativeai as genai
from app.config import settings
import json


# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class Task(BaseModel):
    """Individual task in the research plan"""
    action: Literal["search", "scrape", "summarize", "sentiment", "compare", "final_report"]
    query: Optional[str] = None
    from_task: Optional[str] = Field(None, description="Reference to previous task (e.g., 'task:0')")
    description: Optional[str] = None
    url_index: Optional[int] = Field(0, description="Index of URL to use from list (default 0)")


class ResearchPlan(BaseModel):
    """Structured plan for research workflow"""
    intent: str = Field(..., description="User's research intent")
    tasks: List[Task] = Field(..., description="Ordered list of tasks to execute")
    reasoning: Optional[str] = Field(None, description="Why this plan was chosen")


from datetime import datetime


PLANNER_SYSTEM_PROMPT = f"""Current Date: {datetime.now().strftime('%B %d, %Y')}

You are an expert research planner for e-commerce product analysis.

Your job is to analyze user queries and create structured research plans.

Available actions:
- "search": Search the web for product information (requires 'query')
- "scrape": Scrape a product page (requires 'from_task' reference or URL in query)
- "summarize": Generate product summary (requires 'from_task' with product data)
- "sentiment": Analyze product sentiment (requires 'from_task' with product data)
- "compare": Compare multiple products (requires 'from_task' with multiple products)
- "final_report": Synthesize all results into final report (always last)

Rules:
1. If query contains a URL, start with "scrape"
2. If no URL, start with "search" then generate MULTIPLE "scrape" tasks for top results.
3. For "scrape" tasks following a "search", use 'url_index' to target different results (0, 1, 2).
4. Always include "final_report" as the last task
5. Use "from_task" to reference previous task outputs (e.g., "task:0", "task:1")
6. For comparison, ensure multiple products are scraped first

Examples:

Query: "Apple AirPods 4"
Plan:
{{
  "intent": "product_research",
  "reasoning": "Search for top results, scrape the first 3 distinct products to get a good overview, then summarize and analyze sentiment for each.",
  "tasks": [
    {{"action": "search", "query": "Apple AirPods 4 product page"}},
    {{"action": "scrape", "from_task": "task:0", "url_index": 0}},
    {{"action": "summarize", "from_task": "task:1"}},
    {{"action": "sentiment", "from_task": "task:1"}},
    {{"action": "scrape", "from_task": "task:0", "url_index": 1}},
    {{"action": "summarize", "from_task": "task:4"}},
    {{"action": "sentiment", "from_task": "task:4"}},
    {{"action": "scrape", "from_task": "task:0", "url_index": 2}},
    {{"action": "summarize", "from_task": "task:7"}},
    {{"action": "sentiment", "from_task": "task:7"}},
    {{"action": "final_report"}}
  ]
}}

Query: "Compare Apple AirPods 4 vs Samsung Galaxy Buds"
Plan:
{{
  "intent": "product_comparison",
  "tasks": [
    {{"action": "search", "query": "Apple AirPods 4"}},
    {{"action": "scrape", "from_task": "task:0", "url_index": 0}},
    {{"action": "search", "query": "Samsung Galaxy Buds"}},
    {{"action": "scrape", "from_task": "task:2", "url_index": 0}},
    {{"action": "compare", "from_task": "task:1,task:3"}},
    {{"action": "final_report"}}
  ]
}}

Query: "https://www.amazon.com/dp/B0D1XD1ZV3"
Plan:
{{
  "intent": "product_analysis",
  "tasks": [
    {{"action": "scrape", "query": "https://www.amazon.com/dp/B0D1XD1ZV3"}},
    {{"action": "summarize", "from_task": "task:0"}},
    {{"action": "sentiment", "from_task": "task:0"}},
    {{"action": "final_report"}}
  ]
}}

Respond ONLY with valid JSON matching the ResearchPlan schema.
"""


async def create_plan(query: str) -> ResearchPlan:
    """
    Use Gemini to create a structured research plan
    
    Args:
        query: User's research query
        
    Returns:
        ResearchPlan with structured tasks
    """
    if not settings.GEMINI_API_KEY:
        # Fallback plan if no API key
        return _create_fallback_plan(query)
    
    try:
        # Use Gemini with JSON mode
        model = genai.GenerativeModel(
            model_name=settings.PLANNER_MODEL,
            generation_config={
                "temperature": 0.3,  # Lower temperature for more consistent planning
                "response_mime_type": "application/json",
            },
            system_instruction=PLANNER_SYSTEM_PROMPT
        )
        
        prompt = f"""Create a research plan for this query:

Query: {query}

Respond with a JSON object matching this schema:
{{
  "intent": "string describing the user's goal",
  "tasks": [
    {{"action": "search|scrape|summarize|sentiment|compare|final_report", "query": "optional", "from_task": "optional task reference"}},
    ...
  ],
  "reasoning": "optional explanation"
}}"""
        
        response = model.generate_content(prompt)
        
        # Parse JSON response
        plan_dict = json.loads(response.text)
        
        # Validate with Pydantic
        plan = ResearchPlan(**plan_dict)
        
        print(f"[Planner] Created plan with {len(plan.tasks)} tasks for intent: {plan.intent}")
        
        return plan
        
    except Exception as e:
        print(f"[Planner] Error creating plan: {e}")
        print(f"[Planner] Falling back to default plan")
        return _create_fallback_plan(query)


def _create_fallback_plan(query: str) -> ResearchPlan:
    """
    Create a simple fallback plan when LLM is unavailable
    
    Args:
        query: User query
        
    Returns:
        Basic ResearchPlan
    """
    # Check if query contains URL
    import re
    url_pattern = r"(https?://[^\s]+)"
    has_url = re.search(url_pattern, query)
    
    if has_url:
        # Direct scraping plan
        tasks = [
            Task(action="scrape", query=query),
            Task(action="summarize", from_task="task:0"),
            Task(action="sentiment", from_task="task:0"),
            Task(action="final_report")
        ]
        intent = "product_analysis"
    else:
        # Search then scrape plan
        tasks = [
            Task(action="search", query=query),
            Task(action="scrape", from_task="task:0"),
            Task(action="summarize", from_task="task:1"),
            Task(action="sentiment", from_task="task:1"),
            Task(action="final_report")
        ]
        intent = "product_research"
    
    return ResearchPlan(
        intent=intent,
        tasks=tasks,
        reasoning="Fallback plan (LLM unavailable)"
    )


async def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node that creates the research plan
    
    Args:
        state: Current agent state with 'query'
        
    Returns:
        Updated state with 'plan'
    """
    query = state.get("query", "")
    
    print(f"[Planner Node] Planning for query: {query}")
    
    # Emit planning start status
    state["node_status"] = "planning"
    state["node_message"] = f"Analyzing query: {query}"
    
    plan = await create_plan(query)
    
    state["plan"] = plan.model_dump()
    state["task_results"] = {}
    state["current_task_index"] = 0
    
    # Emit planning completion status
    state["node_status"] = "completed"
    state["node_message"] = f"Created research plan with {len(plan.tasks)} tasks"
    state["plan_summary"] = {
        "intent": plan.intent,
        "total_tasks": len(plan.tasks),
        "task_types": [task.action for task in plan.tasks]
    }
    
    print(f"[Planner Node] Plan created: {plan.intent} with {len(plan.tasks)} tasks")
    
    return state
