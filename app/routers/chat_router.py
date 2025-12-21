from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest
from app.agents.chat_agent import chat_graph
from app.services.database_service import DatabaseService
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json
import asyncio

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_class=StreamingResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat with the AI agent.
    
    Args:
        request: ChatRequest containing messages and optional session_id
        
    Returns:
        StreamingResponse with JSON chunks
    """
    try:
        db = DatabaseService()
        session_id = request.session_id
        
        # Create session if not provided
        if not session_id:
            session_id = await db.create_session()
            
        # Save user message
        last_user_msg = request.messages[-1]
        if last_user_msg.role == "user":
            await db.save_message(session_id, "user", last_user_msg.content)
            
        # Load history from DB
        history = await db.get_chat_history(session_id)
        
        # Convert to LangChain messages
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                messages.append(SystemMessage(content=msg["content"]))
        
        # If history is empty (new session), use the messages from request (should be just the user msg)
        if not messages:
             for msg in request.messages:
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))
                elif msg.role == "system":
                    messages.append(SystemMessage(content=msg.content))

        # Create initial state
        initial_state = {
            "messages": messages,
            "session_id": session_id
        }
        
        # Stream the graph execution
        async def generate():
            # Send session_id first
            yield json.dumps({
                "type": "session_id",
                "session_id": session_id
            }) + "\n"
            
            full_response = ""
            
            async for event in chat_graph.astream_events(initial_state, version="v1"):
                kind = event["event"]
                #print("kind: ",kind)
                # Stream LLM tokens
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        full_response += content
                        yield json.dumps({
                            "type": "content",
                            "content": content
                        }) + "\n"
                
                # Stream tool calls
                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    # Map tool names to user-friendly status messages
                    status_messages = {
                        "search_web": "Searching the web...",
                        "scrape_website": "Scraping website...",
                        "create_plan": "Creating plan...",
                        "perform_research": "Generating comprehensive research report..."
                    }
                    status_msg = status_messages.get(tool_name, f"Using {tool_name}...")
                    
                    yield json.dumps({
                        "type": "agent_status",
                        "status": status_msg,
                        "tool": tool_name
                    }) + "\n"
                    
                    yield json.dumps({
                        "type": "tool_start",
                        "tool": event["name"],
                        "input": event["data"].get("input")
                    }) + "\n"
                
                elif kind == "on_tool_end":
                    # Clear status when tool completes
                    yield json.dumps({
                        "type": "agent_status",
                        "status": None
                    }) + "\n"
                    
                    yield json.dumps({
                        "type": "tool_end",
                        "tool": event["name"],
                        "output": str(event["data"].get("output"))
                    }) + "\n"
            
            # Save assistant response to DB
            if full_response:
                await db.save_message(session_id, "assistant", full_response)
            
            await db.close()

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
