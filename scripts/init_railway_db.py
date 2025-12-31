"""
Script to initialize Railway database with tables.
Run this once after deploying to Railway.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database_service import DatabaseService

async def init_database():
    print("Initializing Railway database...")
    db_service = DatabaseService()
    
    try:
        await db_service.connect()
        print("✅ Database connected successfully!")
        print("✅ Tables created successfully!")
        print("\nTables created:")
        print("  - chat_sessions")
        print("  - chat_messages")
        print("  - research_reports")
        print("  - products")
        print("  - pgvector extension enabled")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db_service.close()
        print("\nDatabase initialization complete.")

if __name__ == "__main__":
    asyncio.run(init_database())
