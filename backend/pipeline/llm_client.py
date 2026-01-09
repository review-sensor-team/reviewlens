import google.generativeai as genai
from openai import OpenAI
from backend.app.core.settings import settings

class LLMClient:
    def __init__(self, provider: str, model_name: str, api_key: str):
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_key = api_key
        self.model = None
        self.client = None
        
        self._configure_service()

    def _configure_service(self):
        """서비스 초기화"""
        if self.provider == 'google':
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        elif self.provider == 'openai':
            self.client = OpenAI(api_key=self.api_key)
        else:
            raise ValueError(f"지원하지 않는 Provider: {self.provider}")

    def generate_text(self, prompt: str) -> str:
        """텍스트 생성 요청"""
        try:
            if self.provider == 'google':
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=settings.LLM_TEMPERATURE,
                        top_p=settings.LLM_TOP_P,
                        max_output_tokens=settings.LLM_MAX_TOKENS
                    )
                )
                return response.text

            elif self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=settings.LLM_TEMPERATURE,
                    top_p=settings.LLM_TOP_P,
                    max_tokens=settings.LLM_MAX_TOKENS
                )
                return response.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"LLM 생성 중 오류 발생: {str(e)}")