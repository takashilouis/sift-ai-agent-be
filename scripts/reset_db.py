"""
Script to reset the database schema.
This will drop all tables and recreate them with the new schema.
"""
import asyncio
import asyncpg
import os

async def reset_database():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5433/ecommerce_agent")
    
    print("Connecting to database...")
    conn = await asyncpg.connect(db_url)
    
    try:
        print("Dropping existing tables...")
        await conn.execute("""
            DROP TABLE IF EXISTS chat_messages CASCADE;
            DROP TABLE IF EXISTS research_reports CASCADE;
            DROP TABLE IF EXISTS products CASCADE;
            DROP TABLE IF EXISTS chat_sessions CASCADE;
        """)
        print("Tables dropped successfully.")
        
        print("Database reset complete. Tables will be recreated on next connection.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(reset_database())
