"""
Chat Agent with Tool Calling

This module implements a conversational agent that can use tools
to answer user questions about products.
"""

from typing import Dict, Any, List, TypedDict, Annotated, Union, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings
from app.services.tavily_service import TavilyService
from app.services.playwright_service import scrape_product_page
from app.services.database_service import DatabaseService
from langchain_core.tools import tool
import asyncio
import json
from contextvars import ContextVar
from datetime import datetime

# Initialize services
tavily_service = TavilyService()
database_service = DatabaseService()

# Context variable to store current session_id
current_session_id: ContextVar[Optional[str]] = ContextVar('current_session_id', default=None)

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
def create_plan(steps: List[str]):
    """
    Create a step-by-step plan to answer a complex user request.
    Use this tool when the request requires multiple steps like searching, comparing, and summarizing.
    """
    return f"Plan created with {len(steps)} steps: {', '.join(steps)}"

@tool
async def perform_research(query: str):
    """
    Perform deep research on a specific product or topic.
    This tool triggers a comprehensive research workflow including searching, scraping, and summarizing.
    The final report will be saved to the database linked to the current chat session.
    
    Args:
        query: The research query (e.g., "Best gaming laptops under $1500")
    
    Example usage:
        perform_research("latest iPad Pro")
        perform_research("best wireless headphones under $200")
    """
    session_id = current_session_id.get()
    print(f"[Chat Agent] Triggering research for: {query} in session: {session_id}")
    
    try:
        # Import research graph here to avoid circular imports
        from app.agents.graph import research_graph, create_initial_state
        
        # Create initial state for research
        initial_state = create_initial_state(query, session_id=session_id)
        
        # Run the research graph
        print("[Chat Agent] Running research workflow...")
        final_state = await research_graph.ainvoke(initial_state)
        
        # Extract final report
        final_report = final_state.get("final_report", "Failed to generate report.")
        
        if not final_report or final_report == "Failed to generate report.":
            return "Research failed: Unable to generate report. Please try again with a different query."
        
        print(f"[Chat Agent] Research completed. Report generated ({len(final_report)} chars)")
        
        # Return the FULL report with a special marker for the frontend
        return f"✅ **Research Report: {query}**\n\n---\n\n{final_report}"
        
    except Exception as e:
        print(f"[Chat Agent] Research failed: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Research failed: {str(e)}"

tools = [search_web, scrape_website, create_plan, perform_research]

# Initialize LLM with tools
llm = ChatGoogleGenerativeAI(
    model=settings.LLM_MODEL,
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.7
).bind_tools(tools)

class ChatState(TypedDict):
    """State for the chat workflow"""
    messages: Annotated[List[BaseMessage], add_messages]
    session_id: Optional[str]

async def chat_node(state: ChatState):
    """
    Process the chat history and generate a response
    """
    messages = state["messages"]
    session_id = state.get("session_id")
    
    # Set session_id in context for tools to access
    current_session_id.set(session_id)
    
    # Define system instruction
    system_instruction = f"""Current Date: {datetime.now().strftime('%B %d, %Y')}

You are a helpful E-commerce AI Assistant. 
You help users research products, compare options, and find the best deals.
You have access to tools to search the web, scrape websites, create plans, and perform deep research.

TOOLS:
- 'search_web': For quick answers and fact-checking.
- 'scrape_website': To get details from a specific URL.
- 'create_plan': To outline a strategy for complex requests.
- 'perform_research': Use this when the user asks for a "report", "deep dive", "comprehensive analysis", or "research" on a topic.
  - Only requires the query parameter
  - Example: perform_research(query="latest smartphones")
  - Example: perform_research(query="best wireless headphones under $200")

When you present a plan or thought process, wrap it in a markdown code block with the language 'plan', like:
```plan
1. Step one
2. Step two
```
Use other tools when you need external information.
Always be polite, concise, and helpful."""

    processed_messages = []
    
    # 1. Filter out existing SystemMessages to avoid confusion/duplication
    clean_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
    
    if not clean_messages:
        print("[Chat Agent] Warning: No human/AI messages found. Creating dummy message.")
        clean_messages = [HumanMessage(content="Hello")]

    # 2. Check if we need to inject system instruction and context
    has_ai_response = any(isinstance(msg, AIMessage) for msg in clean_messages)
    
    # Fetch recent research context if it's the start of conversation
    context_str = ""
    if not has_ai_response and session_id:
        try:
            # Get reports specific to this session
            recent_reports = await database_service.get_session_reports(session_id)
            if recent_reports:
                context_str = "\n\nRecent Research Context (from this session):\n"
                for report in recent_reports:
                    context_str += f"- Query: {report['query']}\n  Summary: {report['content'][:200]}...\n"
        except Exception as e:
            print(f"[Chat Agent] Error fetching context: {e}")

    for i, msg in enumerate(clean_messages):
        if i == 0 and isinstance(msg, HumanMessage) and not has_ai_response:
            # Prepend system instruction and context to the first human message
            combined_content = f"{system_instruction}{context_str}\n\nUser: {msg.content}"
            processed_messages.append(HumanMessage(content=combined_content))
        else:
            processed_messages.append(msg)
            
    # 3. Final safety check
    if not processed_messages:
        processed_messages = [HumanMessage(content=f"{system_instruction}\n\nUser: Hello")]

    print(f"[Chat Agent] Sending {len(processed_messages)} messages to LLM")
    
    try:
        response = await llm.ainvoke(processed_messages)
        return {"messages": [response], "session_id": session_id}
    except Exception as e:
        print(f"[Chat Agent] Error invoking LLM: {e}")
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
