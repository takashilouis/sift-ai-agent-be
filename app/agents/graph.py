"""
Dynamic LangGraph Workflow with LLM Planner

This module implements a dynamic agent workflow where:
1. Planner creates a task plan
2. Task executor runs tasks dynamically
3. Final report synthesizes results

NO fixed pipeline - tasks are determined by the LLM planner.
"""

from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END
from app.agents.planner_agent import planner_node
from app.agents.nodes.search_agent import search_agent_node
from app.agents.nodes.scraper_agent import scraper_agent_node
from app.agents.nodes.summarize_agent import summarize_agent_node
from app.agents.nodes.sentiment_agent import sentiment_agent_node
from app.agents.nodes.compare_agent import compare_agent_node
from app.agents.nodes.final_report_agent import final_report_node


class AgentState(TypedDict):
    """State for the dynamic agent workflow"""
    query: str
    plan: Optional[Dict[str, Any]]
    task_results: Dict[str, Any]
    current_task_index: int
    final_report: Optional[str]
    error: Optional[str]
    session_id: Optional[str]
    deep_research: bool
    report_id: Optional[str]


# Map action names to agent functions
AGENT_DISPATCH = {
    "search": search_agent_node,
    "scrape": scraper_agent_node,
    "summarize": summarize_agent_node,
    "sentiment": sentiment_agent_node,
    "compare": compare_agent_node,
    "final_report": final_report_node,
}


async def task_executor_node(state: AgentState) -> AgentState:
    """
    Execute the current task in the plan
    
    This node dynamically dispatches to the appropriate agent based on
    the task action type.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with task result
    """
    plan = state.get("plan", {})
    tasks = plan.get("tasks", [])
    current_idx = state.get("current_task_index", 0)
    
    if current_idx >= len(tasks):
        print("[Task Executor] All tasks completed")
        return state
    
    # Get current task
    task = tasks[current_idx]
    action = task.get("action")
    
    print(f"[Task Executor] Executing task {current_idx}: {action}")
    
    # Dispatch to appropriate agent
    agent_func = AGENT_DISPATCH.get(action)
    
    if not agent_func:
        print(f"[Task Executor] Unknown action: {action}")
        state["task_results"][str(current_idx)] = {
            "error": f"Unknown action: {action}"
        }
    else:
        try:
            # Execute agent
            result = await agent_func(state, task)
            
            # Store result
            state["task_results"][str(current_idx)] = result
            
            print(f"[Task Executor] Task {current_idx} completed")
            
        except Exception as e:
            print(f"[Task Executor] Task {current_idx} failed: {e}")
            state["task_results"][str(current_idx)] = {
                "error": str(e)
            }
    
    # Move to next task
    state["current_task_index"] = current_idx + 1
    
    return state


def should_continue_tasks(state: AgentState) -> str:
    """
    Determine if there are more tasks to execute
    
    Args:
        state: Current agent state
        
    Returns:
        "continue" if more tasks, "end" if done
    """
    plan = state.get("plan", {})
    tasks = plan.get("tasks", [])
    current_idx = state.get("current_task_index", 0)
    
    if current_idx < len(tasks):
        return "continue"
    else:
        return "end"


async def extract_final_report(state: AgentState) -> AgentState:
    """
    Extract final report from task results
    
    Args:
        state: Current agent state
        
    Returns:
        State with final_report populated
    """
    task_results = state.get("task_results", {})
    
    # Find final_report in task results
    for task_idx, result in task_results.items():
        if "final_report" in result:
            state["final_report"] = result["final_report"]
            break
    
    return state


def create_research_graph():
    """
    Create the dynamic research workflow graph
    
    Returns:
        Compiled StateGraph
    """
    # Initialize graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("task_executor", task_executor_node)
    workflow.add_node("finalize", extract_final_report)
    
    # Set entry point
    workflow.set_entry_point("planner")
    
    # Planner → Task Executor
    workflow.add_edge("planner", "task_executor")
    
    # Task Executor → Loop or Finalize
    workflow.add_conditional_edges(
        "task_executor",
        should_continue_tasks,
        {
            "continue": "task_executor",  # Loop back for next task
            "end": "finalize"              # All tasks done
        }
    )
    
    # Finalize → END
    workflow.add_edge("finalize", END)
    
    # Compile graph
    compiled_graph = workflow.compile()
    
    return compiled_graph


def create_initial_state(query: str, session_id: Optional[str] = None, deep_research: bool = False, report_id: Optional[str] = None) -> AgentState:
    """
    Create initial state for the workflow
    
    Args:
        query: User's research query
        session_id: Optional session ID to link report to chat
        deep_research: Whether to use Deep Research mode (Pro model)
        
    Returns:
        Initial AgentState
    """
    return AgentState(
        query=query,
        plan=None,
        task_results={},
        current_task_index=0,
        final_report=None,
        error=None,
        session_id=session_id,
        deep_research=deep_research,
        report_id=report_id
    )


# Create singleton graph instance
research_graph = create_research_graph()
