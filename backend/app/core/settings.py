"""Application settings"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application configuration"""
    
    APP_NAME: str = "ReviewLens"
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # LLM Settings
    LLM_PROVIDER: str = "openai"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # .env의 추가 필드 무시
    )


settings = Settings()
