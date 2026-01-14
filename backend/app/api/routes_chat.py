"""Chat API routes"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.core.settings import settings
from ..collector import SmartStoreCollector
from ..schemas.requests import ChatRequest, SessionStartRequest, CollectReviewsRequest
from ..schemas.responses import ChatResponse, SessionStartResponse, CollectReviewsResponse, Review, FactorMatch
from ..session.session_store import SessionStore
from .routes_chat_helpers import (
    get_available_categories, detect_category, get_related_reviews,
    format_bot_message, get_stability_info, format_choices, check_cache,
    extract_product_name, determine_category, create_review_responses,
    aggregate_factors, update_cache,
    TOP_FACTORS_LIMIT, MIN_FINALIZE_TURNS, MIN_STABILITY_HITS
)

logger = logging.getLogger("api.chat")

router = APIRouter()
session_store = SessionStore()

# 리뷰 수집 캐시 (URL을 키로 사용)
review_cache: Dict[str, Dict] = {}
MAX_CACHE_SIZE = 10

# LLM 설정 저장용 딕셔너리
session_configs: Dict[str, Any] = {}

@router.post("/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest):
    """대화 세션 시작"""
    logger.info(f"[세션 시작] category={request.category}")
    try:
        session_id = session_store.create_session(
            category=request.category,
            data_dir=Path("backend/data")
        )
        logger.info(f"[세션 생성 성공] session_id={session_id}, category={request.category}")

        #feature/api LLMClient
        api_key = settings.get_api_key(request.provider)
        if not api_key:
            raise HTTPException(status_code=400, detail=f"{request.provider} API Key가 설정되지 않았습니다.")
        
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
        logger.error(f"[세션 시작 실패] category={request.category}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))





@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """대화 메시지 전송"""
    logger.info(f"[메시지 수신] session_id={request.session_id}, message={request.message[:50]}..., request_finalize={request.request_finalize}")
    
    # 세션 확인
    session = session_store.get_session(request.session_id)
    if not session:
        logger.warning(f"[세션 없음] session_id={request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    #  feature/api LLMClient 설정
    config = session_configs.get(request.session_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM 설정이 만료되었습니다. /start를 다시 해주세요.")
    
    try:
        # 대화 진행 또는 종료
        if request.request_finalize:
            logger.info(f"[사용자 요청 종료] session_id={request.session_id}")
            bot_turn = session.finalize_now()
        else:
            bot_turn = session.step(request.message)
        
        logger.info(f"[대화 진행] session_id={request.session_id}, is_final={bot_turn.is_final}, top_factors={len(bot_turn.top_factors)}")
        logger.info(f"[top_factors 상세] {bot_turn.top_factors[:5]}")
        
        # 관련 리뷰 조회
        related_reviews = get_related_reviews(session_store, request.session_id, bot_turn.top_factors)
        
        # 봇 메시지 구성
        bot_message = format_bot_message(bot_turn, related_reviews)
        logger.info(f"[메시지 응답] session_id={request.session_id}, bot_msg_len={len(bot_message) if bot_message else 0}, is_final={bot_turn.is_final}")
        logger.info(f"[related_reviews 상태] keys={list(related_reviews.keys()) if related_reviews else 'None'}")
        
        # 응답 데이터 구성
        response_data = ChatResponse(
            session_id=request.session_id,
            bot_message=bot_message,
            is_final=bot_turn.is_final,
            has_analysis=bot_turn.has_analysis,
            top_factors=[{"factor_key": k, "score": s} for k, s in bot_turn.top_factors],
            llm_context=bot_turn.llm_context,
            related_reviews=related_reviews,
            question_id=bot_turn.question_id,
            answer_type=bot_turn.answer_type,
            choices=format_choices(bot_turn.choices),
            can_finalize=session.turn_count >= MIN_FINALIZE_TURNS and session.stability_hits >= MIN_STABILITY_HITS,
            turn_count=session.turn_count,
            stability_info=get_stability_info(session.turn_count, session.stability_hits)
        )
        
        logger.info(f"[응답 데이터] related_reviews in response: {response_data.related_reviews is not None}")
        if response_data.related_reviews:
            for key, val in response_data.related_reviews.items():
                logger.info(f"  - {key}: count={val.get('count', 0)}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"[메시지 처리 실패] session_id={request.session_id}, error={str(e)}", exc_info=True)
        import traceback
        logger.error(f"[스택트레이스]\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect-reviews", response_model=CollectReviewsResponse)
async def collect_reviews(request: CollectReviewsRequest):
    """스마트스토어 리뷰 수집 (메모리 캐시 지원)"""
    cache_key = f"{request.product_url}|{request.max_reviews}|{request.sort_by_low_rating}"
    
    # 캐시 확인
    cached_response = check_cache(review_cache, session_store, session_configs, cache_key, request.product_url)
    if cached_response:
        return cached_response
    
    logger.info(f"[캐시 미스] 리뷰 수집 시작 - url={request.product_url}, max={request.max_reviews}")
    
    try:
        collector = SmartStoreCollector(product_url=request.product_url, headless=True)
        
        # 카테고리 결정을 위한 사전 수집 (메타데이터만)
        reviews_preview, page_title = collector.collect_reviews(
            max_reviews=min(20, request.max_reviews),
            sort_by_low_rating=request.sort_by_low_rating
        )
        
        # 상품명 추출
        product_name = extract_product_name(page_title)
        
        # 카테고리 결정
        preview_converted = collector.convert_to_backend_format(reviews_preview) if reviews_preview else []
        category, confidence = determine_category(
            request.category, request.product_url, page_title, preview_converted
        )
        
        # 카테고리 감지 실패 시 사용자 선택 요청
        if confidence == 'failed':
            logger.warning(f"[카테고리 감지 실패] 사용자에게 선택 요청")
            return CollectReviewsResponse(
                success=True,
                message="카테고리를 선택해주세요.",
                reviews=[],
                total_count=0,
                detected_category=None,
                category_confidence='failed',
                available_categories=get_available_categories()
            )
        
        # 리뷰 수집 및 Factor 분석 (전체 파이프라인 - collector가 담당)
        logger.info(f"[전체 수집 시작] category={category}")
        result = collector.collect_and_analyze(
            category=category,
            max_reviews=request.max_reviews,
            sort_by_low_rating=request.sort_by_low_rating
        )
        
        # 리뷰 수집 실패 처리
        if result['total_count'] == 0:
            logger.warning(f"[리뷰 수집 실패] url={request.product_url}")
            return CollectReviewsResponse(
                success=False,
                message="리뷰를 수집하지 못했습니다.",
                reviews=[],
                total_count=0
            )
        
        # Review 응답 모델 생성
        review_responses = create_review_responses(result['reviews'])
        
        # 후회 팩터 집계 (상위 5개)
        suggested_factors = aggregate_factors(review_responses)
        
        # 세션 생성
        session_id = session_store.create_session(
            category=category,
            data_dir=Path("backend/data"),
            reviews=result['reviews'],
            product_name=product_name
        )
        logger.info(f"[세션 생성] session_id={session_id}, category={category}, reviews={result['total_count']}건")
        
        # LLM 설정 저장 (.env의 LLM_PROVIDER 사용)
        provider = settings.LLM_PROVIDER
        session_configs[session_id] = {
            "provider": provider,
            "model_name": settings.get_model_name(provider),
            "api_key": settings.get_api_key(provider)
        }
        logger.info(f"[LLM 설정 저장] session_id={session_id}, provider={provider}")
        
        # 응답 생성
        response = CollectReviewsResponse(
            success=True,
            message=f"리뷰 {len(review_responses)}건을 수집했습니다.",
            session_id=session_id,
            reviews=review_responses,
            total_count=len(review_responses),
            detected_category=category,
            category_confidence=confidence,
            available_categories=get_available_categories() if confidence in ['low', 'failed'] else None,
            product_name=product_name,
            suggested_factors=suggested_factors
        )
        
        # 캐시 업데이트
        update_cache(review_cache, MAX_CACHE_SIZE, cache_key, session_id, review_responses, 
                    product_name, category, confidence, suggested_factors)
        
        return response
        
    except Exception as e:
        logger.error(f"[리뷰 수집 실패] url={request.product_url}, error={str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
