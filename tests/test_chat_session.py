import asyncio
import os
from app.services.database_service import DatabaseService

async def test_chat_session_flow():
    print("Testing Chat Session Flow...")
    db = DatabaseService()
    
    try:
        # 1. Create Session
        session_id = await db.create_session()
        print(f"Created Session ID: {session_id}")
        assert session_id is not None
        
        # 2. Save Messages
        await db.save_message(session_id, "user", "Hello, I need a laptop.")
        await db.save_message(session_id, "assistant", "Sure, what kind?")
        print("Messages saved.")
        
        # 3. Retrieve History
        history = await db.get_chat_history(session_id)
        print(f"Retrieved {len(history)} messages.")
        assert len(history) == 2
        assert history[0]["content"] == "Hello, I need a laptop."
        
        # 4. Simulate Research Report Saving
        print("Simulating research report save...")
        await db.save_report(
            query="best gaming laptops",
            content="Gaming laptops are great.",
            session_id=session_id
        )
        
        # 5. Retrieve Session Reports
        reports = await db.get_session_reports(session_id)
        print(f"Retrieved {len(reports)} reports for session.")
        assert len(reports) == 1
        assert reports[0]["query"] == "best gaming laptops"
        
        print("Chat Session Flow Test PASSED!")
        
    except Exception as e:
        print(f"Test FAILED: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(test_chat_session_flow())
