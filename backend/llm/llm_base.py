"""
LLM 클라이언트 베이스 클래스
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLMClient(ABC):
    """LLM 클라이언트 베이스 클래스"""
    
    @abstractmethod
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
        최종 분석 요약 생성
        
        Args:
            top_factors: [(factor_key, score), ...] 상위 후회 요인
            evidence_reviews: 증거 리뷰 리스트
            total_turns: 총 대화 턴 수
            category_name: 제품 카테고리명
            product_name: 제품명
            dialogue_history: 대화 내역 [
                {"role": "user", "text": "..."},
                {"role": "bot", "text": "..."}
            ]
            
        Returns:
            str: 생성된 분석 요약
        """
        pass
