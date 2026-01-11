"""Application settings"""
from pydantic_settings import BaseSettings
from typing import List, Dict, Optional
from pydantic import ConfigDict
import os


class Settings(BaseSettings):
    """Application configuration"""
    
    APP_NAME: str = "ReviewLens"
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    

    #Feature/api LLM Configurations
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # LLM Provider 설정 (.env에서 읽어옴)
    LLM_PROVIDER: str = "openai"
    
    # 각 프로바이더별 모델명 (.env에서 읽어옴)
    OPENAI_MODEL: Optional[str] = None
    GEMINI_MODEL: Optional[str] = None
    CLAUDE_MODEL: Optional[str] = None

    #LLM Common parameters
    LLM_TEMPERATURE: float = 0.6
    LLM_TOP_P: float = 0.9
    LLM_MAX_TOKENS: int = 4096

    #Supported LLM Models
    SUPPORTED_PROVIDERS: List[str] = ['google', 'openai']
    AVAILABLE_MODELS: Dict[str, List[str]] = {
        'google': [
            'gemini-2.5-flash',     
            'gemini-2.5-pro',        
            'gemini-2.0-flash-001',
            'gemini-3.0-pro'   
        ],
        'openai': [
            'gpt-4o',              
            'gpt-4o-mini',            
            'gpt-4.1',
            'gpt-5.1'         
        ]
    }

    #API Key Getter
    def get_api_key(self, provider: str) -> Optional[str]:
        if provider == 'google' or provider == 'gemini':
            return self.GOOGLE_API_KEY
        elif provider == 'openai':
            return self.OPENAI_API_KEY
        elif provider == 'anthropic' or provider == 'claude':
            return self.ANTHROPIC_API_KEY
        return None
    
    def get_model_name(self, provider: str) -> str:
        """프로바이더별 모델명 반환"""
        if provider == 'openai':
            return self.OPENAI_MODEL or "gpt-4o-mini"
        elif provider == 'google' or provider == 'gemini':
            return self.GEMINI_MODEL or "gemini-1.5-flash"
        elif provider == 'anthropic' or provider == 'claude':
            return self.CLAUDE_MODEL or "claude-3-5-sonnet-20241022"
        return "gpt-4o-mini"  # 기본값
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # .env의 추가 필드 무시
    )



settings = Settings()
