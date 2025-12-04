import asyncio
import os
from app.services.database_service import DatabaseService

async def test_database():
    print("Testing DatabaseService...")
    db = DatabaseService()
    
    try:
        await db.connect()
        print("Connected to database.")
        
        # Test saving a report
        print("Saving a test report...")
        # Dummy embedding (768 dimensions)
        dummy_embedding = [0.1] * 768
        await db.save_report(
            query="test query",
            content="This is a test report content about laptops.",
            embedding=dummy_embedding
        )
        print("Report saved.")
        
        # Test fetching recent reports
        print("Fetching recent reports...")
        recent = await db.get_recent_reports(limit=1)
        print(f"Recent reports: {recent}")
        assert len(recent) > 0
        assert recent[0]['query'] == "test query"
        
        # Test vector search
        print("Testing vector search...")
        results = await db.search_reports(query_embedding=dummy_embedding, limit=1)
        print(f"Search results: {results}")
        assert len(results) > 0
        assert results[0]['query'] == "test query"
        
        print("DatabaseService test passed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(test_database())
