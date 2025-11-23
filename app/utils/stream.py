import json
from typing import AsyncGenerator, Any, Dict
from langgraph.graph import StateGraph


async def stream_graph_output(
    graph: StateGraph,
    initial_state: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """
    Stream LangGraph execution output as JSON chunks
    
    Args:
        graph: Compiled LangGraph StateGraph
        initial_state: Initial state dictionary
        
    Yields:
        JSON-encoded strings with step name and state
    """
    try:
        async for step_output in graph.astream(initial_state):
            # LangGraph astream yields dict with node name as key
            for step_name, state in step_output.items():
                yield json.dumps({
                    "step": step_name,
                    "state": state
                }) + "\n"
    except Exception as e:
        # Yield error information
        yield json.dumps({
            "step": "error",
            "state": {
                "error": str(e),
                "type": type(e).__name__
            }
        }) + "\n"


async def stream_json_response(data: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    Stream a single JSON response
    
    Args:
        data: Dictionary to stream as JSON
        
    Yields:
        JSON-encoded string
    """
    yield json.dumps(data) + "\n"
