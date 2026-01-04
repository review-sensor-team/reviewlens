"""Response schemas"""
from pydantic import BaseModel
from typing import Optional, List, Dict


class SessionStartResponse(BaseModel):
    """세션 시작 응답"""
    session_id: str
    message: str


class FactorScore(BaseModel):
    """요인 점수"""
    factor_key: str
    factor_id: Optional[int] = None  # 추가: factor_id (옵셔널, 하위 호환)
    score: float


class ChatResponse(BaseModel):
    """채팅 응답"""
    session_id: str
    bot_message: Optional[str]
    is_final: bool
    top_factors: List[FactorScore]
    llm_context: Optional[Dict] = None
    # 추가: 관련 리뷰 정보
    related_reviews: Optional[Dict] = None  # {factor_key: {count: int, examples: [...]}}
    # 질문 정보
    question_id: Optional[str] = None
    answer_type: Optional[str] = None  # 'no_choice' | 'single_choice'
    choices: Optional[str] = None  # '예|아니오|잘 모르겠음' 형식


class FactorMatch(BaseModel):
    """Factor 매칭 정보"""
    factor_id: Optional[int] = None  # 추가: factor_id (옵셔널, 하위 호환)
    factor_key: str
    display_name: str
    sentences: List[str]
    matched_terms: List[str]


class Review(BaseModel):
    """리뷰 데이터"""
    review_id: int
    rating: Optional[int]
    text: str
    created_at: str
    # 추가: factor 분석 결과
    factor_matches: Optional[List[FactorMatch]] = []


class CollectReviewsResponse(BaseModel):
    """리뷰 수집 응답"""
    success: bool
    message: str
    session_id: Optional[str] = None  # 생성된 세션 ID
    reviews: List[Review]
    total_count: int
    # 카테고리 정보
    detected_category: Optional[str] = None
    category_confidence: str = "high"  # 'high' | 'low' | 'failed'
    available_categories: Optional[List[Dict[str, str]]] = None  # [{'key': 'appliance_induction', 'name': '인덕션'}]
    product_name: Optional[str] = None
    # 상품 정보
    product_name: Optional[str] = None  # 페이지 제목에서 추출한 상품명
