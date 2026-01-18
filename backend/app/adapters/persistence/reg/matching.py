"""질문 -> Factor 매칭 로직"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def match_question_to_factors(
    question: str,
    factor_store: Dict,
    threshold: float = 0.7
) -> List[str]:
    """
    사용자 질문을 분석하여 관련 factor들을 찾음
    
    Args:
        question: 사용자 질문
        factor_store: Factor 데이터 저장소
        threshold: 유사도 임계값
        
    Returns:
        매칭된 factor ID 리스트
    """
    # TODO: 실제 매칭 로직 구현
    # 현재는 placeholder
    logger.info(f"질문 매칭: {question}")
    return []
