"""Request schemas"""
from pydantic import BaseModel


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

class UrlCheckRequest(BaseModel):
    """URL 접속 테스트 요청"""
    url: str