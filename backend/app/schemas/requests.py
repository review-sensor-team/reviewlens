"""Request schemas"""
from pydantic import BaseModel
from typing import Optional


class SessionStartRequest(BaseModel):
    """세션 시작 요청"""
    category: str


class ChatRequest(BaseModel):
    """채팅 메시지 요청"""
    session_id: str
    message: str
    request_finalize: bool = False  # True일 경우 강제로 분석 종료


class CollectReviewsRequest(BaseModel):
    """리뷰 수집 요청"""
    product_url: str
    max_reviews: int = 100
    sort_by_low_rating: bool = True
    category: Optional[str] = None  # 사용자가 카테고리를 직접 지정할 수 있음
