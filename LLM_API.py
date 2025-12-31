# packages
import os
import sys
from typing import Optional, Dict, Any, List
import google.generativeai as genai
import openai
from openai import OpenAI

# ====================================================
# [Configuration] 설정 관리
# ====================================================
class LLMConfig:
    """ LLM 설정 클래스. 다양한 LLM 제공자와 모델 파라미터를 관리. """
    SUPPORTED_PROVIDERS = ['google', 'openai']

    # Provider별 사용 가능한 모델 목록
    AVAILABLE_MODELS = {
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
    
    # 기본 프롬프트
    PROMPT = "부정 리뷰가 긍정 리뷰보다 솔직한 데이터가 많이 들어가 있는 이유는?"

    # 모델 공통 파라미터 
    TEMPERATURE = 0.6
    TOP_P = 0.9
    MAX_TOKENS = 4096

    # API Key 가져오기 헬퍼 함수
    @staticmethod
    def get_api_key(provider: str) -> Optional[str]:
        if provider == 'google':
            return os.getenv('GOOGLE_API_KEY')
        elif provider == 'openai':
            return os.getenv('OPENAI_API_KEY')
        return None

# ====================================================
# [Class] LLM Client
# ====================================================
class LLMClient:
    def __init__(self, provider: str, model_name: str, api_key: str):
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_key = api_key
        self.client = None 
        self.model = None  
        
        self._configure_service()

    def _configure_service(self):
        """선택된 정보로 서비스 연결 (초기화)"""
        if self.provider == 'google':
            print(f"🔄 Google Gemini 초기화 중... (Model: {self.model_name})")
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print("✅ 초기화 완료!")

        elif self.provider == 'openai':
            print(f"🔄 OpenAI GPT 초기화 중... (Model: {self.model_name})")
            self.client = OpenAI(api_key=self.api_key)
            print("✅ 초기화 완료!")

        else:
            raise ValueError(f"지원하지 않는 Provider입니다: {self.provider}")

    def generate_text(self, prompt: str) -> str:
        """설정된 파라미터(Config)를 사용하여 텍스트 생성"""
        try:
            if self.provider == 'google':
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=LLMConfig.TEMPERATURE,
                        top_p=LLMConfig.TOP_P,
                        max_output_tokens=LLMConfig.MAX_TOKENS
                    )
                )
                return response.text

            elif self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=LLMConfig.TEMPERATURE,
                    top_p=LLMConfig.TOP_P,
                    max_tokens=LLMConfig.MAX_TOKENS
                )
                return response.choices[0].message.content

        except Exception as e:
            return f"❌ 생성 중 오류 발생: {str(e)}"

# ====================================================
# [UI Helper] 리스트 선택 함수 (수정됨)
# ====================================================
def select_from_list(options: List[str], title: str) -> str:
    """
    리스트를 출력하고 사용자 입력을 받음 (들여쓰기 및 출력 버퍼 문제 해결)
    """
    if not options:
        print(f"⚠️ 선택 가능한 {title} 목록이 없습니다.")
        return ""

    print(f"\n📋 {title}")
    print("-" * 30)
    for i, option in enumerate(options):
        print(f"  [{i+1}] {option}")
    print("-" * 30)
    
    while True:
        try:
            choice = input(f"👉 번호를 선택하세요 (Enter = 1번 '{options[0]}'): ").strip()
            
            # 1. 엔터만 쳤을 때 -> 첫 번째 옵션 선택
            if not choice:
                print(f"   👌 기본값 '{options[0]}' 선택됨")
                return options[0]
            
            # 2. 숫자를 입력했을 때
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    selected = options[idx]
                    print(f"   👌 '{selected}' 선택됨")
                    return selected
                else:
                    print(f"⚠️ 1부터 {len(options)} 사이의 번호를 입력해주세요.")
            else:
                print("⚠️ 숫자를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n🚫 취소되었습니다.")
            sys.exit()

# ====================================================
# [Main] 실행 테스트 (CLI)
# ====================================================
def get_user_selection():
    """유저에게 Provider와 Model을 번호로 선택받는 함수"""
    print("\n" + "="*40)
    print("🤖 LLM 클라이언트 설정 마법사")
    print("="*40)

    # 1. Provider 선택 
    provider = select_from_list(LLMConfig.SUPPORTED_PROVIDERS, "사용할 서비스를 선택하세요")
    if not provider: return None, None, None

    # 2. Model 선택
    # Provider가 올바르게 선택되었는지 확인 후 진행
    if provider in LLMConfig.AVAILABLE_MODELS:
        available_models = LLMConfig.AVAILABLE_MODELS[provider]
        model = select_from_list(available_models, f"{provider.upper()} 모델을 선택하세요")
    else:
        print("❌ 잘못된 서비스 Provider입니다.")
        return None, None, None

    # 3. API Key 확인
    api_key = LLMConfig.get_api_key(provider)
    
    if not api_key:
        print(f"\n⚠️ 환경변수에서 {provider.upper()} API 키를 찾을 수 없습니다.")
        api_key = input("👉 API Key를 직접 입력해주세요: ").strip()
    
    return provider, model, api_key

if __name__ == "__main__":
    try:
        # 1. 유저 입력 받기
        user_provider, user_model, user_key = get_user_selection()

        if not user_key:
            print("\n❌ 설정이 완료되지 않아 종료합니다.")
            sys.exit()

        # 2. 클라이언트 생성
        bot = LLMClient(provider=user_provider, model_name=user_model, api_key=user_key)

        # 3. 질문 테스트
        print("\n" + "-"*40)
        print(f"💬 기본 질문: {LLMConfig.PROMPT}")
        user_question = input("💬 질문을 입력하세요 (Enter = 기본 질문 사용): ").strip()
        
        if not user_question:
            user_question = LLMConfig.PROMPT

        print(f"\nQ: {user_question}")
        print("⏳ 답변 생성 중 ...")
        
        answer = bot.generate_text(user_question)
        print(f"\nA: {answer}")
        print("-" * 40)

    except Exception as e:
        print(f"\n❌ 프로그램 실행 중 오류 발생: {e}")