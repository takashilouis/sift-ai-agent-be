from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest
from app.agents.chat_agent import chat_graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json
import asyncio

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/", response_class=StreamingResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat with the AI agent.
    
    Args:
        request: ChatRequest containing messages
        
    Returns:
        StreamingResponse with JSON chunks
    """
    try:
        # Convert Pydantic messages to LangChain messages
        messages = []
        for msg in request.messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                messages.append(SystemMessage(content=msg.content))
        
        # Create initial state
        initial_state = {"messages": messages}
        
        # Stream the graph execution
        async def generate():
            async for event in chat_graph.astream_events(initial_state, version="v1"):
                kind = event["event"]
                
                # Stream LLM tokens
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield json.dumps({
                            "type": "content",
                            "content": content
                        }) + "\n"
                
                # Stream tool calls
                elif kind == "on_tool_start":
                    yield json.dumps({
                        "type": "tool_start",
                        "tool": event["name"],
                        "input": event["data"].get("input")
                    }) + "\n"
                
                elif kind == "on_tool_end":
                    yield json.dumps({
                        "type": "tool_end",
                        "tool": event["name"],
                        "output": str(event["data"].get("output"))
                    }) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
