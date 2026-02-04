import json
from typing import AsyncGenerator, Any, Dict
from langgraph.graph import StateGraph
from datetime import datetime


async def stream_graph_output(
    graph: StateGraph,
    initial_state: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """
    Stream LangGraph execution output as JSON chunks with enhanced metadata
    
    Args:
        graph: Compiled LangGraph StateGraph
        initial_state: Initial state dictionary
        
    Yields:
        JSON-encoded strings with step name, state, and metadata
    """
    try:
        async for step_output in graph.astream(initial_state):
            # LangGraph astream yields dict with node name as key
            for step_name, state in step_output.items():
                # Calculate progress percentage
                progress = calculate_progress(state, step_name)
                
                # Extract current task description
                current_task_desc = get_current_task_description(state, step_name)
                
                # Build enhanced output
                output = {
                    "step": step_name,
                    "state": state,
                    "timestamp": datetime.utcnow().isoformat(),
                    "progress": progress,
                    "current_task": current_task_desc,
                }
                
                # Add node-specific metadata
                metadata = extract_node_metadata(state, step_name)
                if metadata:
                    output["metadata"] = metadata
                
                yield json.dumps(output) + "\n"
    except Exception as e:
        # Yield error information
        yield json.dumps({
            "step": "error",
            "state": {
                "error": str(e),
                "type": type(e).__name__
            },
            "timestamp": datetime.utcnow().isoformat(),
        }) + "\n"


def calculate_progress(state: Dict[str, Any], step_name: str) -> float:
    """
    Calculate overall progress percentage based on current state
    
    Args:
        state: Current agent state
        step_name: Current step name
        
    Returns:
        Progress percentage (0-100)
    """
    plan = state.get("plan", {})
    tasks = plan.get("tasks", []) if isinstance(plan, dict) else []
    current_task_index = state.get("current_task_index", 0)
    
    if not tasks:
        # No plan yet, estimate based on step
        if step_name == "planner":
            return 10.0
        elif step_name == "task_executor":
            return 50.0
        elif step_name == "finalize":
            return 90.0
        return 0.0
    
    # Calculate based on task completion
    # Total steps: planner (1) + tasks (N) + finalize (1) = N + 2
    total_steps = len(tasks) + 2
    
    if step_name == "planner":
        completed_steps = 1
    elif step_name == "task_executor":
        completed_steps = 1 + current_task_index
    elif step_name == "finalize":
        completed_steps = len(tasks) + 1
    else:
        completed_steps = 0
    
    progress = (completed_steps / total_steps) * 100
    return min(progress, 100.0)


def get_current_task_description(state: Dict[str, Any], step_name: str) -> str:
    """
    Get human-readable description of current task
    
    Args:
        state: Current agent state
        step_name: Current step name
        
    Returns:
        Task description string
    """
    if step_name == "planner":
        return "Creating research plan..."
    
    if step_name == "finalize":
        return "Generating final report..."
    
    if step_name == "task_executor":
        plan = state.get("plan", {})
        tasks = plan.get("tasks", []) if isinstance(plan, dict) else []
        current_idx = state.get("current_task_index", 0)
        
        if current_idx < len(tasks):
            task = tasks[current_idx]
            action = task.get("action", "processing")
            description = task.get("description", "")
            query = task.get("query", "")
            
            if description:
                return description
            elif query:
                return f"{action.capitalize()}: {query}"
            else:
                return f"Running {action} task..."
    
    return "Processing..."


def extract_node_metadata(state: Dict[str, Any], step_name: str) -> Dict[str, Any]:
    """
    Extract node-specific metadata for progress display
    
    Args:
        state: Current agent state
        step_name: Current step name
        
    Returns:
        Dictionary of metadata
    """
    metadata = {}
    
    if step_name == "planner":
        plan = state.get("plan", {})
        if isinstance(plan, dict) and "tasks" in plan:
            metadata["total_tasks"] = len(plan.get("tasks", []))
            metadata["intent"] = plan.get("intent", "")
    
    elif step_name == "task_executor":
        current_idx = state.get("current_task_index", 0)
        plan = state.get("plan", {})
        tasks = plan.get("tasks", []) if isinstance(plan, dict) else []
        
        if current_idx < len(tasks):
            task = tasks[current_idx]
            metadata["action"] = task.get("action", "")
            metadata["task_index"] = current_idx
            metadata["total_tasks"] = len(tasks)
            
            # Add task-specific metadata
            if task.get("query"):
                metadata["query"] = task["query"]
            if task.get("from_task"):
                metadata["from_task"] = task["from_task"]
    
    return metadata


async def stream_json_response(data: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    Stream a single JSON response
    
    Args:
        data: Dictionary to stream as JSON
        
    Yields:
        JSON-encoded string
    """
    yield json.dumps(data) + "\n"
