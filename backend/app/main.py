"""FastAPI application factory and main entry point"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

from .api import routes_chat, routes_metrics
from .core.settings import settings
from .core.metrics import (
    http_requests_total,
    http_request_duration_seconds
)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="ReviewLens API",
        description="후회를 줄이기 위한 대화형 리뷰 분석 API",
        version="0.1.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Metrics middleware - HTTP 요청 자동 추적
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        """HTTP 요청 메트릭 수집 미들웨어"""
        method = request.method
        endpoint = request.url.path

        print(f"Metrics middleware - method: {method}, endpoint: {endpoint}")
        
        # 요청 시작 시간
        start_time = time.time()
        
        try:
            # 요청 처리
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            status = 500
            raise
        finally:
            # 응답 시간 계산
            duration = time.time() - start_time
            
            # 메트릭 기록 (status는 문자열로 변환)
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=str(status)  # 정수 → 문자열 변환
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        
        return response

    # Register routers
    app.include_router(routes_chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(routes_metrics.router, tags=["metrics"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
