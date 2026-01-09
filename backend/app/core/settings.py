"""Application settings"""
from pydantic_settings import BaseSettings
from typing import List, Dict, Optional
import os


class Settings(BaseSettings):
    """Application configuration"""
    
    APP_NAME: str = "ReviewLens"
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    

    #Feature/api LLM Configurations
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

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
        if provider == 'google':
            return self.GOOGLE_API_KEY
        elif provider == 'openai':
            return self.OPENAI_API_KEY
        return None
    
    class Config:
        env_file = ".env"
        case_sensitive = True



settings = Settings()
