"""Request schemas"""
from pydantic import BaseModel
from typing import Optional


class SessionStartRequest(BaseModel):
    """세션 시작 요청"""
    category: str
    #LLM Provider 선택 기본값은 'google', model_name 기본값은 'gemini-2.5-flash', openai, 'gpt-4o' 등으로 설정 가능.
    provider: str = 'google'
    model_name: str ='gemini-2.5-flash'
    
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

class UrlCheckRequest(BaseModel):
    """URL 접속 테스트 요청"""
    url: str