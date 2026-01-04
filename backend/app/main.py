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
from .core.metrics import (
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
