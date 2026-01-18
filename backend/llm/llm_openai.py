"""
OpenAI LLM 클라이언트
"""
import logging
from .llm_base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI API 클라이언트"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.7, max_tokens: int = 2000):
        super().__init__(api_key, model, temperature, max_tokens)
        
        if not api_key:
            logger.warning("OpenAI API key가 설정되지 않았습니다.")
            self.client = None
        else:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
                logger.info(f"OpenAI 클라이언트 초기화 완료: model={model}")
            except Exception as e:
                logger.error(f"OpenAI 클라이언트 초기화 실패: {e}")
                self.client = None
    
    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """OpenAI API 호출"""
        if not self.client:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다")
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"OpenAI 요약 생성 완료: {len(summary)}자")
        return summary
