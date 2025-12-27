"""Chat API routes"""
from fastapi import APIRouter, HTTPException
from pathlib import Path

from backend.pipeline.dialogue import DialogueSession
from ..schemas.requests import ChatRequest, SessionStartRequest
from ..schemas.responses import ChatResponse, SessionStartResponse
from ..services.session_store import SessionStore

router = APIRouter()
session_store = SessionStore()


@router.post("/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest):
    """대화 세션 시작"""
    try:
        session_id = session_store.create_session(
            category=request.category,
            data_dir=Path("backend/data")
        )
        return SessionStartResponse(
            session_id=session_id,
            message="세션이 시작되었습니다. 무엇이 궁금하신가요?"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """대화 메시지 전송"""
    session = session_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        bot_turn = session.step(request.message)
        
        return ChatResponse(
            session_id=request.session_id,
            bot_message=bot_turn.question_text,
            is_final=bot_turn.is_final,
            top_factors=[{"factor_key": k, "score": s} for k, s in bot_turn.top_factors],
            llm_context=bot_turn.llm_context
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
