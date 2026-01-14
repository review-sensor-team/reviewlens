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
    score: float


class ChatResponse(BaseModel):
    """채팅 응답"""
    session_id: str
    bot_message: Optional[str]
    is_final: bool
    top_factors: List[FactorScore]
    llm_context: Optional[Dict] = None



class URLResponse(BaseModel):
    """URL 응답"""
    url: str
    status: str
    error_message: str
    content_summary: Optional[str] = None
