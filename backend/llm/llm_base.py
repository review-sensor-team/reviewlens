"""
LLM 클라이언트 베이스 클래스
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from .prompt_factory import PromptFactory, PromptStrategy

logger = logging.getLogger(__name__)


class PromptBuilder:
    """프롬프트 구성 유틸리티 - PromptFactory를 사용한 전략 기반 프롬프트 생성
    
    레거시 호환성을 위해 유지하되, 내부적으로 PromptFactory 사용
    """
    
    # 기본 프롬프트 전략 (환경 변수나 설정으로 변경 가능)
    _default_strategy: Optional[PromptStrategy] = None
    
    @classmethod
    def _get_strategy(cls) -> PromptStrategy:
        """프롬프트 전략 가져오기 (싱글톤 패턴)"""
        if cls._default_strategy is None:
            # Settings에서 전략 이름 가져오기
            from ..app.core.settings import Settings
            settings = Settings()
            strategy_name = settings.PROMPT_STRATEGY
            
            logger.info(f"[PromptBuilder] 프롬프트 전략 초기화: {strategy_name}")
            cls._default_strategy = PromptFactory.create(strategy=strategy_name)
        
        return cls._default_strategy
    
    @classmethod
    def set_strategy(cls, strategy: str):
        """프롬프트 전략 변경
        
        Args:
            strategy: 전략 이름 (default|concise|detailed|friendly)
        """
        logger.info(f"[PromptBuilder] 프롬프트 전략 변경: {strategy}")
        cls._default_strategy = PromptFactory.create(strategy=strategy)
    
    @staticmethod
    def build_system_prompt() -> str:
        """시스템 프롬프트 생성"""
        strategy = PromptBuilder._get_strategy()
        return strategy.build_system_prompt()
    
    @staticmethod
    def build_user_prompt(
        top_factors: List[tuple],
        evidence_reviews: List[Dict[str, Any]],
        total_turns: int,
        category_name: str,
        product_name: str,
        dialogue_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """유저 프롬프트 생성"""
        strategy = PromptBuilder._get_strategy()
        return strategy.build_user_prompt(
            top_factors, evidence_reviews, total_turns,
            category_name, product_name, dialogue_history
        )
    
    @staticmethod
    def get_fallback_summary(
        top_factors: List[tuple],
        category_name: str,
        product_name: str
    ) -> str:
        """API 실패 시 기본 요약"""
        strategy = PromptBuilder._get_strategy()
        return strategy.build_fallback(top_factors, category_name, product_name)


class BaseLLMClient(ABC):
    """LLM 클라이언트 베이스 클래스 - 템플릿 메서드 패턴 사용"""
    
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def generate_summary(
        self, 
        top_factors: List[tuple],
        evidence_reviews: List[Dict[str, Any]],
        total_turns: int,
        category_name: str,
        product_name: str = "이 제품",
        dialogue_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        최종 분석 요약 생성 (템플릿 메서드)
        
        Args:
            top_factors: [(factor_key, score), ...] 상위 후회 요인
            evidence_reviews: 증거 리뷰 리스트
            total_turns: 총 대화 턴 수
            category_name: 제품 카테고리명
            product_name: 제품명
            dialogue_history: 대화 내역
            
        Returns:
            str: 생성된 분석 요약 (JSON 형식)
        """
        # 프롬프트 구성 (공통 로직)
        system_prompt = PromptBuilder.build_system_prompt()
        user_prompt = PromptBuilder.build_user_prompt(
            top_factors, evidence_reviews, total_turns,
            category_name, product_name, dialogue_history
        )
        
        # 프롬프트 저장 (모든 LLM)
        self._save_prompt(system_prompt, user_prompt)
        
        # API 호출 (각 구현체에서 정의)
        try:
            response = self._call_api(system_prompt, user_prompt)
            
            # 응답 저장
            self._save_response(response, product_name)
            
            return response
        except Exception as e:
            logger.error(f"{self.__class__.__name__} API 호출 실패: {e}")
            fallback = PromptBuilder.get_fallback_summary(top_factors, category_name, product_name)
            self._save_response(fallback, product_name)
            return fallback
    
    @abstractmethod
    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """
        실제 LLM API 호출 (각 구현체에서 구현)
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 유저 프롬프트
            
        Returns:
            str: LLM 응답
        """
        pass
    
    def _save_prompt(self, system_prompt: str, user_prompt: str):
        """프롬프트를 파일로 저장 (모든 LLM 공통)"""
        try:
            from datetime import datetime
            from pathlib import Path
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = Path("out")
            out_dir.mkdir(exist_ok=True)
            
            prompt_file = out_dir / f"llm_prompt_{timestamp}.txt"
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("SYSTEM PROMPT\n")
                f.write("=" * 80 + "\n")
                f.write(system_prompt)
                f.write("\n\n")
                f.write("=" * 80 + "\n")
                f.write("USER PROMPT\n")
                f.write("=" * 80 + "\n")
                f.write(user_prompt)
                f.write("\n")
            
            logger.info(f"[LLM 프롬프트 저장] {prompt_file}")
        except Exception as e:
            logger.error(f"프롬프트 저장 실패: {e}")
    
    def _save_response(self, response: str, product_name: str):
        """LLM 응답을 JSON 파일로 저장"""
        try:
            from datetime import datetime
            from pathlib import Path
            import json
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = Path("out")
            out_dir.mkdir(exist_ok=True)
            
            response_file = out_dir / f"llm_response_{timestamp}.json"
            
            # JSON 파싱 시도
            try:
                response_json = json.loads(response)
                # 제품명과 타임스탬프 추가
                response_json["_metadata"] = {
                    "product_name": product_name,
                    "timestamp": timestamp,
                    "model": self.model,
                    "provider": self.__class__.__name__
                }
                
                with open(response_file, "w", encoding="utf-8") as f:
                    json.dump(response_json, f, ensure_ascii=False, indent=2)
                    
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트로 저장
                with open(response_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "raw_response": response,
                        "_metadata": {
                            "product_name": product_name,
                            "timestamp": timestamp,
                            "model": self.model,
                            "provider": self.__class__.__name__,
                            "parse_error": "JSON 파싱 실패"
                        }
                    }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[LLM 응답 저장] {response_file}")
        except Exception as e:
            logger.error(f"응답 저장 실패: {e}")
