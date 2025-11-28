"""
Chat Agent with Tool Calling

This module implements a conversational agent that can use tools
to answer user questions about products.
"""

from typing import Dict, Any, List, TypedDict, Annotated, Union
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings
from app.services.tavily_service import TavilyService
from app.services.playwright_service import scrape_product_page
from langchain_core.tools import tool

# Initialize services
tavily_service = TavilyService()

# Define tools
@tool
def search_web(query: str):
    """Search the web for information about products, reviews, or general topics."""
    return tavily_service.search(query)

@tool
async def scrape_website(url: str):
    """Scrape a specific website URL to extract detailed product information."""
    result = await scrape_product_page(url)
    return result.model_dump() if result else {}

@tool
def compare_products(products: List[str]):
    """Compare multiple products based on available information."""
    # This is a placeholder for a more complex comparison logic
    # In a real scenario, this might trigger a sub-agent or complex logic
    return f"Comparison requested for: {', '.join(products)}. (Comparison logic to be implemented)"

tools = [search_web, scrape_website]

# Initialize LLM with tools
llm = ChatGoogleGenerativeAI(
    model=settings.LLM_MODEL,
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.7
).bind_tools(tools)

class ChatState(TypedDict):
    """State for the chat workflow"""
    messages: Annotated[List[BaseMessage], add_messages]

def chat_node(state: ChatState):
    """
    Process the chat history and generate a response
    """
    messages = state["messages"]
    
    # Define system instruction
    system_instruction = """You are a helpful E-commerce AI Assistant. 
You help users research products, compare options, and find the best deals.
You have access to tools to search the web and scrape websites.
Use these tools when you need external information.
Always be polite, concise, and helpful."""

    processed_messages = []
    
    # 1. Filter out existing SystemMessages to avoid confusion/duplication
    #    and find the first HumanMessage to attach instructions to
    clean_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
    
    if not clean_messages:
        # If we have no messages (or only system messages), we can't generate a response
        # But to avoid crashing, we'll create a dummy human message
        print("[Chat Agent] Warning: No human/AI messages found. Creating dummy message.")
        clean_messages = [HumanMessage(content="Hello")]

    # 2. Check if we need to inject system instruction
    #    We inject it if it's the start of a conversation (no AI messages yet)
    has_ai_response = any(isinstance(msg, AIMessage) for msg in clean_messages)
    
    for i, msg in enumerate(clean_messages):
        if i == 0 and isinstance(msg, HumanMessage) and not has_ai_response:
            # Prepend system instruction to the first human message
            combined_content = f"{system_instruction}\n\nUser: {msg.content}"
            processed_messages.append(HumanMessage(content=combined_content))
        else:
            processed_messages.append(msg)
            
    # 3. Final safety check
    if not processed_messages:
        # Should not happen due to check above, but just in case
        processed_messages = [HumanMessage(content=f"{system_instruction}\n\nUser: Hello")]

    print(f"[Chat Agent] Sending {len(processed_messages)} messages to LLM")
    
    try:
        response = llm.invoke(processed_messages)
        return {"messages": [response]}
    except Exception as e:
        print(f"[Chat Agent] Error invoking LLM: {e}")
        # Return a fallback error message to the user
        return {"messages": [AIMessage(content="I apologize, but I encountered an error processing your request. Please try again.")]}

def should_continue(state: ChatState):
    """
    Determine if the conversation should continue (tool call) or end
    """
    last_message = state["messages"][-1]
    
    if last_message.tool_calls:
        return "tools"
    return END

# Create the graph
def create_chat_graph():
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("agent", chat_node)
    workflow.add_node("tools", ToolNode(tools))
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()

chat_graph = create_chat_graph()
