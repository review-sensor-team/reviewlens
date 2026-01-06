"""
LLM 클라이언트 팩토리
"""
import logging
from typing import Literal
from .llm_base import BaseLLMClient
from .llm_gemini import GeminiClient
from .llm_openai import OpenAIClient
from .llm_claude import ClaudeClient

logger = logging.getLogger(__name__)


class LLMFactory:
    """LLM 클라이언트 팩토리"""
    
    @staticmethod
    def create_client(
        provider: Literal["gemini", "openai", "claude"],
        api_key: str,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> BaseLLMClient:
        """
        LLM 클라이언트 생성
        
        Args:
            provider: LLM 제공자 ("gemini", "openai", "claude")
            api_key: API 키
            model: 사용할 모델 (None이면 기본값 사용)
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
            
        Returns:
            BaseLLMClient: LLM 클라이언트 인스턴스
        """
        
        if provider == "gemini":
            model = model or "gemini-1.5-flash"
            return GeminiClient(api_key, model, temperature, max_tokens)
        
        elif provider == "openai":
            model = model or "gpt-4o-mini"
            return OpenAIClient(api_key, model, temperature, max_tokens)
        
        elif provider == "claude":
            model = model or "claude-3-5-sonnet-20241022"
            return ClaudeClient(api_key, model, temperature, max_tokens)
        
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {provider}. 'gemini', 'openai', 'claude' 중 하나를 선택하세요.")


def get_llm_client() -> BaseLLMClient:
    """
    설정 파일 기반으로 LLM 클라이언트 생성
    
    Returns:
        BaseLLMClient: 설정된 LLM 클라이언트
    """
    from ..core.settings import (
        LLM_PROVIDER,
        GEMINI_API_KEY,
        OPENAI_API_KEY,
        ANTHROPIC_API_KEY,
        GEMINI_MODEL,
        OPENAI_MODEL,
        CLAUDE_MODEL,
        LLM_TEMPERATURE,
        LLM_MAX_TOKENS
    )
    
    # API 키 선택
    api_keys = {
        "gemini": GEMINI_API_KEY,
        "openai": OPENAI_API_KEY,
        "claude": ANTHROPIC_API_KEY
    }
    
    # 모델 선택
    models = {
        "gemini": GEMINI_MODEL,
        "openai": OPENAI_MODEL,
        "claude": CLAUDE_MODEL
    }
    
    api_key = api_keys.get(LLM_PROVIDER, "")
    model = models.get(LLM_PROVIDER)
    
    logger.info(f"LLM 클라이언트 생성: provider={LLM_PROVIDER}, model={model}, has_key={bool(api_key)}")
    
    return LLMFactory.create_client(
        provider=LLM_PROVIDER,
        api_key=api_key,
        model=model,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS
    )
