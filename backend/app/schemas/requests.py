"""Request schemas"""
from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    """세션 시작 요청"""
    category: str


class ChatRequest(BaseModel):
    """채팅 메시지 요청"""
    session_id: str
    message: str
