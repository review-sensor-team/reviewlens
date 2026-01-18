"""
Anthropic Claude LLM 클라이언트
"""
import logging
from .llm_base import BaseLLMClient

logger = logging.getLogger(__name__)


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API 클라이언트"""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022", temperature: float = 0.7, max_tokens: int = 2000):
        super().__init__(api_key, model, temperature, max_tokens)
        
        if not api_key:
            logger.warning("Anthropic API key가 설정되지 않았습니다.")
            self.client = None
        else:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
                logger.info(f"Claude 클라이언트 초기화 완료: model={model}")
            except Exception as e:
                logger.error(f"Claude 클라이언트 초기화 실패: {e}")
                self.client = None
    
    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Claude API 호출"""
        if not self.client:
            raise RuntimeError("Claude 클라이언트가 초기화되지 않았습니다")
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        summary = response.content[0].text.strip()
        logger.info(f"Claude 요약 생성 완료: {len(summary)}자")
        return summary
