"""Application settings"""
from pydantic_settings import BaseSettings
from typing import List, Dict, Optional
from pydantic import ConfigDict
import os


class Settings(BaseSettings):
    """Application configuration"""
    
    APP_NAME: str = "ReviewLens"
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]
    

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
    
    # Prompt 전략 설정 (.env에서 읽어옴)
    PROMPT_STRATEGY: str = "detailed,friendly"  # default|concise|detailed|friendly 또는 쉼표로 구분하여 여러 개
    
    def get_prompt_strategies(self) -> List[str]:
        """PROMPT_STRATEGY를 파싱하여 전략 리스트 반환
        
        Returns:
            전략 이름 리스트 (예: ['default'] 또는 ['default', 'friendly'])
        """
        if not self.PROMPT_STRATEGY:
            return ["default"]
        
        # 쉼표로 분리하고 공백 제거
        strategies = [s.strip() for s in self.PROMPT_STRATEGY.split(",") if s.strip()]
        return strategies if strategies else ["default"]

    #LLM Common parameters
    LLM_TEMPERATURE: float = 0.6
    LLM_TOP_P: float = 0.9
    LLM_MAX_TOKENS: int = 4096
    
    # Dialogue 설정
    DIALOGUE_JACCARD_THRESHOLD: float = 0.67  # top3 유사도 임계값 (3개 중 2개 이상 같으면 안정)
    DIALOGUE_MIN_ANALYSIS_TURNS: int = 3      # 최소 분석 턴 수
    DIALOGUE_FOCUS_TURNS_THRESHOLD: int = 2   # 턴 1-2는 top2, 턴 3+는 top1 집중
    DIALOGUE_TOP_FACTORS_LIMIT: int = 3       # 상위 요인 제한
    
    # Evidence 검색 설정
    EVIDENCE_PER_FACTOR_MIN: int = 8          # factor당 최소 evidence 수
    EVIDENCE_PER_FACTOR_MAX: int = 8          # factor당 최대 evidence 수
    EVIDENCE_MAX_TOTAL: int = 15              # 전체 최대 evidence 수
    EVIDENCE_RANK0_NEG: int = 3               # rank 0의 NEG quota
    EVIDENCE_RANK0_MIX: int = 2               # rank 0의 MIX quota
    EVIDENCE_RANK0_POS: int = 1               # rank 0의 POS quota
    EVIDENCE_RANK1_NEG: int = 2               # rank 1의 NEG quota
    EVIDENCE_RANK1_MIX: int = 2               # rank 1의 MIX quota
    EVIDENCE_RANK1_POS: int = 1               # rank 1의 POS quota
    EVIDENCE_RANK2_NEG: int = 2               # rank 2의 NEG quota
    EVIDENCE_RANK2_MIX: int = 2               # rank 2의 MIX quota
    EVIDENCE_RANK2_POS: int = 1               # rank 2의 POS quota
    
    # API 설정
    API_RELATED_REVIEWS_LIMIT: int = 5        # 관련 리뷰 제한
    API_MIN_FINALIZE_TURNS: int = 3           # 최소 종료 턴 수
    API_MIN_STABILITY_HITS: int = 2           # 최소 안정성 히트
    API_MAX_CACHE_SIZE: int = 10              # 최대 캐시 크기
    API_CATEGORY_PREVIEW_REVIEWS: int = 20    # 카테고리 감지용 미리보기 리뷰 수
    
    # 리뷰 소스 설정
    REVIEW_SOURCE_MODE: str = "json_file"     # "json_file" 또는 "url"
    REVIEW_FILE_FORMAT: str = "json"          # "json" 또는 "csv" - 리뷰 파일 형식
    REVIEW_JSON_DIR: str = "backend/data/review"  # JSON 파일 디렉토리
    FACTOR_CSV_PATH: str = "backend/data/factor/reg_factor_v4.csv"  # Factor CSV 파일 경로
    
    # UI 설정
    USE_PRODUCT_SELECTION: bool = True        # True: 상품 선택 모드, False: URL 입력 모드

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
