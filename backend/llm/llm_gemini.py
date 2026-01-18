"""
Gemini LLM 클라이언트
"""
import logging
from .llm_base import BaseLLMClient

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLMClient):
    """Google Gemini API 클라이언트"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", temperature: float = 0.7, max_tokens: int = 2000):
        super().__init__(api_key, model, temperature, max_tokens)
        
        if not api_key:
            logger.warning("Gemini API key가 설정되지 않았습니다.")
            self.client = None
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(model)
                logger.info(f"Gemini 클라이언트 초기화 완료: model={model}")
            except Exception as e:
                logger.error(f"Gemini 클라이언트 초기화 실패: {e}")
                self.client = None
    
    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Gemini API 호출"""
        if not self.client:
            raise RuntimeError("Gemini 클라이언트가 초기화되지 않았습니다")
        
        # Gemini는 system_prompt와 user_prompt를 합쳐서 전달
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        response = self.client.generate_content(
            combined_prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }
        )
        
        summary = response.text.strip()
        logger.info(f"Gemini 요약 생성 완료: {len(summary)}자")
        return summary
