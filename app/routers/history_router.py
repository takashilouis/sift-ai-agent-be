from fastapi import APIRouter, HTTPException
from app.services.database_service import DatabaseService
from typing import List, Dict, Any

router = APIRouter(prefix="/history", tags=["history"])

@router.get("/research")
async def get_research_history(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent research reports
    
    Args:
        limit: Maximum number of reports to return
        
    Returns:
        List of research reports with id, query, created_at
    """
    db = DatabaseService()
    try:
        await db.connect()
            
        rows = await db.conn.fetch(
            """
            SELECT id, query, created_at, 
                   LEFT(content, 100) as preview
            FROM research_reports 
            WHERE session_id IS NULL
            ORDER BY created_at DESC 
            LIMIT $1
            """,
            limit
        )
        
        return [
            {
                "id": str(row["id"]),
                "query": row["query"],
                "preview": row["preview"],
                "created_at": row["created_at"].isoformat()
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[History API] Research history error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()


@router.get("/chat")
async def get_chat_history(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent chat sessions
    
    Args:
        limit: Maximum number of sessions to return
        
    Returns:
        List of chat sessions with id, first_message, created_at
    """
    db = DatabaseService()
    try:
        await db.connect()
        
        # Get sessions with their first user message
        rows = await db.conn.fetch(
            """
            SELECT 
                s.id,
                s.created_at,
                (
                    SELECT content 
                    FROM chat_messages 
                    WHERE session_id = s.id AND role = 'user'
                    ORDER BY created_at ASC 
                    LIMIT 1
                ) as first_message
            FROM chat_sessions s
            ORDER BY s.created_at DESC
            LIMIT $1
            """,
            limit
        )
        
        return [
            {
                "id": str(row["id"]),
                "first_message": row["first_message"] or "New Chat",
                "created_at": row["created_at"].isoformat()
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[History API] Chat history error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()


@router.get("/research/{report_id}")
async def get_research_report(report_id: str) -> Dict[str, Any]:
    """
    Get a specific research report by ID
    
    Args:
        report_id: UUID of the research report
        
    Returns:
        Research report with full content
    """
    db = DatabaseService()
    try:
        await db.connect()
            
        row = await db.conn.fetchrow(
            """
            SELECT id, query, content, created_at, session_id
            FROM research_reports 
            WHERE id = $1
            """,
            report_id
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="Research report not found")
        
        return {
            "id": str(row["id"]),
            "query": row["query"],
            "content": row["content"],
            "session_id": str(row["session_id"]) if row["session_id"] else None,
            "created_at": row["created_at"].isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[History API] Get research report error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()


@router.get("/chat/{session_id}")
async def get_chat_session(session_id: str) -> Dict[str, Any]:
    """
    Get a specific chat session with all messages
    
    Args:
        session_id: UUID of the chat session
        
    Returns:
        Chat session with all messages
    """
    db = DatabaseService()
    try:
        await db.connect()
        
        # Get session
        session = await db.conn.fetchrow(
            "SELECT id, created_at FROM chat_sessions WHERE id = $1",
            session_id
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Get messages
        messages = await db.conn.fetch(
            """
            SELECT id, role, content, created_at
            FROM chat_messages
            WHERE session_id = $1
            ORDER BY created_at ASC
            """,
            session_id
        )
        
        return {
            "id": str(session["id"]),
            "created_at": session["created_at"].isoformat(),
            "messages": [
                {
                    "id": str(msg["id"]),
                    "role": msg["role"],
                    "content": msg["content"],
                    "created_at": msg["created_at"].isoformat()
                }
                for msg in messages
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[History API] Get chat session error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()
