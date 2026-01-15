"""FastAPI application factory and main entry point"""
import logging
import os
import time
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .api import routes_chat
from .api import routes_metrics
from .core.settings import settings
from .core.logging_config import setup_logging
from backend.core.metrics import (
    http_requests_total,
    http_request_duration_seconds,
)

# .env 파일 로드
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logging.info(f".env 파일 로드 완료: {env_path}")
else:
    logging.warning(f".env 파일이 없습니다: {env_path}")

# 로깅 시스템 초기화
setup_logging()
logger = logging.getLogger("api")


class MetricsMiddleware(BaseHTTPMiddleware):
    """HTTP 요청 메트릭을 자동으로 수집하는 미들웨어"""
    
    async def dispatch(self, request: Request, call_next):
        # /metrics 엔드포인트는 메트릭 수집 제외 (무한 루프 방지)
        if request.url.path == "/metrics":
            return await call_next(request)
        
        start_time = time.time()
        
        # 요청 처리
        response = await call_next(request)
        
        # 처리 시간 계산
        duration = time.time() - start_time
        
        # 메트릭 기록
        method = request.method
        endpoint = request.url.path
        status_code = response.status_code
        
        # 요청 수 카운터
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        # 응답 시간 히스토그램
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        # 로깅
        logger.info(
            f"{method} {endpoint} - {status_code} - {duration:.3f}s"
        )
        
        return response


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    logger.info("ReviewLens API 애플리케이션 생성 중...")
    
    app = FastAPI(
        title="ReviewLens API",
        description="후회를 줄이기 위한 대화형 리뷰 분석 API",
        version="0.1.0",
    )

    # Startup event - 세션 복원
    @app.on_event("startup")
    async def startup_event():
        """애플리케이션 시작 시 실행"""
        logger.info("[Startup] 세션 복원 시작...")
        try:
            # SessionStore의 세션 복원 실행
            from .api.routes_chat import session_store, session_configs, review_cache
            if session_store.enable_persistence:
                session_store._restore_sessions()
                
                # session_configs 및 review_cache 복원 (LLM 설정 및 캐시)
                cache_restored = 0
                for session_id, metadata in session_store._metadata.items():
                    # LLM 설정 복원
                    llm_config = metadata.get("llm_config")
                    if llm_config:
                        session_configs[session_id] = llm_config
                        logger.debug(f"[Startup] LLM 설정 복원: {session_id}")
                    
                    # review_cache 복원
                    product_url = metadata.get("product_url")
                    if product_url and session_id in session_store._reviews:
                        # 캐시 키 재구성 (기본값: max_reviews=100, sort_by_low_rating=True)
                        cache_key = f"{product_url}|100|True"
                        
                        # 리뷰 데이터를 Review 객체로 변환
                        from .schemas.responses import Review
                        reviews = session_store._reviews[session_id]
                        review_responses = [
                            Review(
                                review_id=r.get('review_id', idx),
                                text=r.get('text', ''),
                                rating=r.get('rating', 0),
                                created_at=r.get('created_at', ''),
                                factor_matches=r.get('factor_matches', [])
                            ) for idx, r in enumerate(reviews)
                        ]
                        
                        # suggested_factors 복원 (최소 5개)
                        from .api.routes_chat_helpers import aggregate_factors
                        suggested_factors = aggregate_factors(review_responses)
                        
                        # 캐시 저장
                        review_cache[cache_key] = {
                            'session_id': session_id,
                            'reviews': review_responses,
                            'total_count': len(review_responses),
                            'product_name': metadata.get('product_name'),
                            'category': metadata.get('category'),
                            'confidence': 'high',  # 복원된 세션은 high로 간주
                            'suggested_factors': suggested_factors,
                            'timestamp': __import__('datetime').datetime.now()
                        }
                        cache_restored += 1
                        logger.debug(f"[Startup] 캐시 복원: {product_url} -> {session_id}")
                
                logger.info(f"[Startup] 세션 복원 완료: {len(session_store._sessions)}개 세션, {cache_restored}개 캐시")
        except Exception as e:
            logger.error(f"[Startup] 세션 복원 중 오류: {str(e)}", exc_info=True)

    # Metrics middleware (첫 번째로 등록하여 모든 요청 추적)
    app.add_middleware(MetricsMiddleware)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(routes_chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(routes_metrics.router, tags=["monitoring"])
    
    logger.info("API 라우터 등록 완료")
    logger.info(f"CORS 허용 도메인: {settings.ALLOWED_ORIGINS}")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
