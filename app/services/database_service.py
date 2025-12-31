import os
import json
from typing import List, Dict, Any, Optional
import asyncpg
from pgvector.asyncpg import register_vector
from app.config import settings
import uuid

from langchain_google_genai import GoogleGenerativeAIEmbeddings

class DatabaseService:
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self.conn = None
        # Debug: Print the database URL (mask password)
        masked_url = self.db_url.replace(self.db_url.split('@')[0].split(':')[-1], '****') if '@' in self.db_url else self.db_url
        print(f"[DatabaseService] Using database URL: {masked_url}")
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=settings.GEMINI_API_KEY
        )

    async def connect(self):
        """Explicitly connect to database and initialize schema"""
        if not self.conn:
            self.conn = await asyncpg.connect(self.db_url)
            try:
                await register_vector(self.conn)
            except Exception as e:
                print(f"[DatabaseService] Warning: Could not register vector type: {e}")
                print("[DatabaseService] Continuing without vector support...")
            await self.init_db()
        return self

    async def init_db(self):
        # Create tables if they don't exist
        try:
            # Try to create vector extension (may fail if not available)
            await self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception as e:
            print(f"[DatabaseService] Warning: Could not create vector extension: {e}")
            print("[DatabaseService] Tables will be created without vector columns...")
        
        # Create tables - make vector columns optional
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID REFERENCES chat_sessions(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS research_reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID REFERENCES chat_sessions(id),
                query TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS products (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                url TEXT UNIQUE,
                title TEXT,
                description TEXT,
                price TEXT,
                details JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Try to add vector columns if extension is available
        try:
            await self.conn.execute("""
                ALTER TABLE research_reports 
                ADD COLUMN IF NOT EXISTS embedding vector(768);
                
                ALTER TABLE products 
                ADD COLUMN IF NOT EXISTS embedding vector(768);
            """)
        except Exception as e:
            print(f"[DatabaseService] Warning: Could not add vector columns: {e}")

    async def generate_embedding(self, text: str) -> List[float]:
        return await self.embeddings.aembed_query(text)

    async def create_session(self) -> str:
        await self.connect()
        session_id = str(uuid.uuid4())
        await self.conn.execute("INSERT INTO chat_sessions (id) VALUES ($1)", session_id)
        return session_id

    async def save_message(self, session_id: str, role: str, content: str):
        await self.connect()
        await self.conn.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES ($1, $2, $3)",
            session_id, role, content
        )

    async def get_chat_history(self, session_id: str):
        await self.connect()
        rows = await self.conn.fetch(
            "SELECT role, content FROM chat_messages WHERE session_id = $1 ORDER BY created_at ASC",
            session_id
        )
        return [dict(row) for row in rows]

    async def save_report(self, query: str, content: str, session_id: Optional[str] = None, embedding: List[float] = None, report_id: Optional[str] = None):
        await self.connect()
        if not embedding:
            try:
                embedding = await self.generate_embedding(content)
            except Exception as e:
                print(f"[DatabaseService] Error generating embedding: {e}")
                pass

        if embedding:
            if report_id:
                await self.conn.execute(
                    "INSERT INTO research_reports (id, query, content, embedding, session_id) VALUES ($1, $2, $3, $4, $5)",
                    report_id, query, content, embedding, session_id
                )
            else:
                await self.conn.execute(
                    "INSERT INTO research_reports (query, content, embedding, session_id) VALUES ($1, $2, $3, $4)",
                    query, content, embedding, session_id
                )
        else:
            if report_id:
                await self.conn.execute(
                    "INSERT INTO research_reports (id, query, content, session_id) VALUES ($1, $2, $3, $4)",
                    report_id, query, content, session_id
                )
            else:
                await self.conn.execute(
                    "INSERT INTO research_reports (query, content, session_id) VALUES ($1, $2, $3)",
                    query, content, session_id
                )

    async def search_reports(self, query_embedding: List[float], limit: int = 5):
        await self.connect()
        rows = await self.conn.fetch(
            "SELECT query, content, created_at FROM research_reports ORDER BY embedding <-> $1 LIMIT $2",
            query_embedding, limit
        )
        return [dict(row) for row in rows]

    async def get_recent_reports(self, limit: int = 5):
        await self.connect()
        rows = await self.conn.fetch(
            "SELECT query, content, created_at FROM research_reports ORDER BY created_at DESC LIMIT $1",
            limit
        )
        return [dict(row) for row in rows]
        
    async def get_session_reports(self, session_id: str):
        await self.connect()
        rows = await self.conn.fetch(
            "SELECT query, content, created_at FROM research_reports WHERE session_id = $1 ORDER BY created_at DESC",
            session_id
        )
        return [dict(row) for row in rows]

    async def close(self):
        if self.conn:
            await self.conn.close()
            self.conn = None
