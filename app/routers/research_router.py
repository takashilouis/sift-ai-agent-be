from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.research_request import ResearchRequest
from app.schemas.research_response import ResearchResponse, FinalResearchReport
from app.agents.graph import research_graph, create_initial_state
from app.utils.stream import stream_graph_output
import json
from typing import AsyncGenerator


router = APIRouter(prefix="/research", tags=["research"])


@router.post("/", response_class=StreamingResponse)
async def research_product(request: ResearchRequest):
    """
    Perform product research using the LLM-based agent workflow
    
    This endpoint uses a dynamic planner to create a research plan,
    then executes tasks and streams progress.
    
    Args:
        request: ResearchRequest with query and mode
        
    Returns:
        StreamingResponse with JSON chunks for each step
    """
    try:
        # Generate report ID upfront
        import uuid
        report_id = str(uuid.uuid4())
        
        # Create initial state
        initial_state = create_initial_state(
            query=request.query,
            deep_research=request.deep_research,
            report_id=report_id
        )
        
        # Stream the graph execution
        async def generate():
            # Yield report ID as first chunk
            yield json.dumps({"type": "report_id", "report_id": report_id}) + "\n"
            
            async for chunk in stream_graph_output(research_graph, initial_state):
                yield chunk
        
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


@router.post("/sync", response_model=FinalResearchReport)
async def research_product_sync(request: ResearchRequest):
    """
    Perform product research synchronously (non-streaming)
    
    This endpoint runs the full workflow and returns the final result.
    
    Args:
        request: ResearchRequest with query and mode
        
    Returns:
        FinalResearchReport with complete research results
    """
    try:
        # Create initial state
        initial_state = create_initial_state(
            query=request.query,
            deep_research=request.deep_research
        )
        
        # Run the graph to completion
        final_state = None
        async for step_output in research_graph.astream(initial_state):
            # Keep updating until we get the final state
            for step_name, state in step_output.items():
                final_state = state
        
        if final_state is None:
            raise HTTPException(status_code=500, detail="Graph execution failed")
        
        # Extract legacy fields for backward compatibility
        task_results = final_state.get("task_results", {})
        
        # Try to extract common fields from task results
        url = None
        product_data = None
        summary = None
        sentiment = None
        comparison = None
        
        for task_idx, result in task_results.items():
            if "url" in result and not url:
                url = result["url"]
            if "product_data" in result and not product_data:
                product_data = result["product_data"]
            if "summary" in result and not summary:
                summary = result["summary"]
            if "sentiment" in result and not sentiment:
                sentiment = result["sentiment"]
            if "comparison" in result and not comparison:
                comparison = result["comparison"]
        
        # Return the final report
        return FinalResearchReport(
            query=final_state.get("query"),
            plan=final_state.get("plan"),
            task_results=task_results,
            final_report=final_state.get("final_report"),
            error=final_state.get("error"),
            # Legacy fields
            url=url,
            product_data=product_data,
            summary=summary,
            sentiment=sentiment,
            comparison=comparison
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Status message
    """
    return {
        "status": "healthy",
        "service": "research-agent",
        "version": "2.0.0",
        "features": ["llm-planner", "dynamic-tasks", "real-apis"]
    }
