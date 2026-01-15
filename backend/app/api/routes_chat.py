"""Chat API routes"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
#feature/api
from typing import Dict, Any
import time

from backend.pipeline.dialogue import DialogueSession
from ..schemas.requests import ChatRequest, SessionStartRequest
from ..schemas.responses import ChatResponse, SessionStartResponse
from ..services.session_store import SessionStore

#feature/api
from backend.app.core.settings import settings
from backend.pipeline.llm_client import LLMClient
from ..core.metrics import (
    dialogue_sessions_total,
    dialogue_turns_total,
    dialogue_completions_total,
    llm_calls_total,
    llm_duration_seconds
)

router = APIRouter()
session_store = SessionStore()

#feature/api llm 설정 저장용 딕셔너리
session_configs: Dict[str, Any] = {}

@router.post("/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest):
    """대화 세션 시작"""
    try:
        session_id = session_store.create_session(
            category=request.category,
            data_dir=Path("backend/data")
        )

        # 메트릭: 세션 시작 기록
        dialogue_sessions_total.labels(category=request.category).inc()

        #feature/api LLMClient
        api_key = settings.get_api_key(request.provider)
        if not api_key:
            raise HTTPException(status_code=400, detail=f"{request.provider}API Key가 설정되지 않았습니다.")
        
        session_configs[session_id] = { 
            "provider": request.provider,
            "model_name": request.model_name,
            "api_key": api_key
        }

        return SessionStartResponse(
            session_id=session_id,
            #feature/api 초기 메시지에 LLM 정보 포함
            message=f"세션이 시작되었습니다. 무엇이 궁금하신가요? LLM 정보: ({request.provider}/{request.model_name})"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """대화 메시지 전송"""
    session = session_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    #  feature/api LLMClient 설정
    config = session_configs.get(request.session_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM 설정이 만료되었습니다. /start를 다시 해주세요.")
    
    try:
        client = LLMClient(
            provider=config["provider"],
            model_name=config["model_name"],
            api_key=config["api_key"]
        )

        # LLM 호출 시간 측정
        llm_start_time = time.time()
        model_name = f"{config['provider']}/{config['model_name']}"
        
        try:
            answer = client.generate_text(request.message)
            llm_duration = time.time() - llm_start_time
            
            # 메트릭: LLM 호출 성공 기록
            llm_calls_total.labels(model=model_name, status='success').inc()
            llm_duration_seconds.labels(model=model_name).observe(llm_duration)
        except Exception as llm_error:
            llm_duration = time.time() - llm_start_time
            
            # 메트릭: LLM 호출 실패 기록
            llm_calls_total.labels(model=model_name, status='error').inc()
            llm_duration_seconds.labels(model=model_name).observe(llm_duration)
            raise

        # 응답 생성
        is_final = True  # 현재는 항상 True
        response = ChatResponse(
            session_id=request.session_id,
            bot_message=answer,
            is_final=is_final,
            top_factors=[],
            llm_context={}
        )

        # 메트릭: 대화 턴 기록
        dialogue_turns_total.labels(
            session_id=request.session_id,
            is_final=str(is_final).lower()
        ).inc()

        # 메트릭: 세션 완료 기록 (is_final=True일 때)
        if is_final:
            dialogue_completions_total.labels(category=session.category).inc()

        return response

        # feature/api 기존 코드 주석 처리
        # bot_turn = session.step(request.message)
        # return ChatResponse(...)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
