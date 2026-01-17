"""Chat API Router - Clean Architecture Version (Phase 4)

얇은 컨트롤러: Service 레이어만 호출, 비즈니스 로직 없음
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ...services.chat_service import ChatService
from ...services.prompt_service import PromptService
from ...services.review_service import ReviewService

logger = logging.getLogger("api.routers.chat")

# 라우터 생성
router = APIRouter(prefix="/api/v2/chat", tags=["chat"])

# Service 인스턴스 (싱글톤 패턴)
_chat_service: Optional[ChatService] = None
_prompt_service: Optional[PromptService] = None
_review_service: Optional[ReviewService] = None


def get_data_dir() -> Path:
    """데이터 디렉토리 경로 반환"""
    return Path(__file__).resolve().parent.parent.parent.parent / "data"


def get_chat_service() -> ChatService:
    """ChatService 의존성"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(data_dir=get_data_dir())
    return _chat_service


def get_prompt_service() -> PromptService:
    """PromptService 의존성"""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService(version="v2")
    return _prompt_service


def get_review_service() -> ReviewService:
    """ReviewService 의존성"""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService(data_dir=get_data_dir())
    return _review_service


# === Request/Response Models ===

class SessionStartRequest(BaseModel):
    """세션 시작 요청"""
    category: str
    product_name: str
    product_id: Optional[str] = None


class SessionStartResponse(BaseModel):
    """세션 시작 응답"""
    session_id: str
    message: str
    category: str
    product_name: str
    factor_count: int


class ChatMessageRequest(BaseModel):
    """채팅 메시지 요청"""
    session_id: str
    message: str
    selected_factor: Optional[str] = None
    request_finalize: bool = False


class ChatMessageResponse(BaseModel):
    """채팅 메시지 응답"""
    session_id: str
    question: str
    top_factors: list[tuple[str, float]]
    turn_count: int
    has_analysis: bool
    analysis: Optional[Dict[str, Any]] = None
    matched_factors: list[str]


# === API Endpoints ===

@router.post("/sessions", response_model=SessionStartResponse)
async def create_session(
    request: SessionStartRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """새 대화 세션 생성
    
    Service 레이어의 create_session()을 호출하여 세션을 생성합니다.
    """
    logger.info(f"세션 생성 요청: category={request.category}, product={request.product_name}")
    
    try:
        # Service 레이어 호출 (비즈니스 로직 없음)
        result = chat_service.create_session(
            session_id=f"session-{request.category}-{hash(request.product_name) % 10000}",
            category=request.category,
            product_name=request.product_name
        )
        
        logger.info(f"세션 생성 완료: {result['session_id']}")
        
        return SessionStartResponse(
            session_id=result["session_id"],
            message=f"{request.product_name}에 대한 대화를 시작합니다. 무엇이 궁금하신가요?",
            category=result["category"],
            product_name=request.product_name,
            factor_count=result["factor_count"]
        )
    except Exception as e:
        logger.error(f"세션 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")


@router.post("/messages", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """채팅 메시지 전송 및 응답 받기
    
    Service 레이어의 process_turn()을 호출하여 대화를 진행합니다.
    """
    logger.info(f"메시지 수신: session={request.session_id}, msg={request.message[:50]}...")
    
    # 세션 존재 확인
    session = chat_service.get_session(request.session_id)
    if not session:
        logger.warning(f"세션 없음: {request.session_id}")
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    try:
        # Service 레이어 호출 (비즈니스 로직 없음)
        result = chat_service.process_turn(
            session_id=request.session_id,
            user_message=request.message,
            selected_factor=request.selected_factor
        )
        
        logger.info(f"메시지 처리 완료: turn={result['turn_count']}, analysis={result['has_analysis']}")
        
        return ChatMessageResponse(
            session_id=request.session_id,
            question=result["question"],
            top_factors=result["top_factors"],
            turn_count=result["turn_count"],
            has_analysis=result["has_analysis"],
            analysis=result.get("analysis"),
            matched_factors=result.get("matched_factors", [])
        )
    except Exception as e:
        logger.error(f"메시지 처리 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"메시지 처리 실패: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """세션 정보 조회"""
    logger.info(f"세션 조회: {session_id}")
    
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """세션 삭제"""
    logger.info(f"세션 삭제: {session_id}")
    
    # TODO: ChatService에 delete_session 메서드 추가
    return {"message": "세션이 삭제되었습니다", "session_id": session_id}
