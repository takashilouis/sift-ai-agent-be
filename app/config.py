from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # API Configuration
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "E-Commerce Research Agent"
    VERSION: str = "1.0.0"
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    # LLM API Keys (REQUIRED for production)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Search API (REQUIRED for real search)
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    
    # LLM Configuration
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    PLANNER_MODEL: str = os.getenv("PLANNER_MODEL", "gemini-2.5-flash")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "8192"))  # Gemini 2.5 Flash max output
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
