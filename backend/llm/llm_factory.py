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
    from ..app.core.settings import settings
    
    # API 키 및 모델 가져오기
    provider = settings.LLM_PROVIDER
    api_key = settings.get_api_key(provider)
    model = settings.get_model_name(provider)
    
    if not api_key:
        raise ValueError(f"{provider} API 키가 설정되지 않았습니다.")
    
    logger.info(f"LLM 클라이언트 생성: provider={provider}, model={model}, has_key={bool(api_key)}")
    
    return LLMFactory.create_client(
        provider=provider,
        api_key=api_key,
        model=model,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS
    )
