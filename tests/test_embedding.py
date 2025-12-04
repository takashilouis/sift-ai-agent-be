import asyncio
import os
from app.services.database_service import DatabaseService

async def test_embedding():
    print("Testing DatabaseService Embedding Generation...")
    db = DatabaseService()
    
    try:
        text = "This is a test sentence for embedding generation."
        embedding = await db.generate_embedding(text)
        print(f"Generated embedding of length: {len(embedding)}")
        assert len(embedding) == 768
        print("Embedding generation test passed!")
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_embedding())
