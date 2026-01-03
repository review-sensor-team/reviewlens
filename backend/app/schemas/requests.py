"""Request schemas"""
from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    """세션 시작 요청"""
    category: str


class ChatRequest(BaseModel):
    """채팅 메시지 요청"""
    session_id: str
    message: str


class CollectReviewsRequest(BaseModel):
    """리뷰 수집 요청"""
    product_url: str
    max_reviews: int = 100
    sort_by_low_rating: bool = True


class StartWithReviewsRequest(BaseModel):
    """리뷰 데이터와 함께 세션 시작 요청"""
    session_id: str
    reviews: list
