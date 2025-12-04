from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class Message(BaseModel):
    """A single message in the chat history"""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    """Request for the chat endpoint"""
    messages: List[Message]
    session_id: Optional[str] = None
    stream: bool = True

class ChatResponse(BaseModel):
    """Response from the chat endpoint"""
    role: str = "assistant"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
