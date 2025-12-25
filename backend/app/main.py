"""FastAPI application factory and main entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import routes_chat
from .core.settings import settings


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

    # Register routers
    app.include_router(routes_chat.router, prefix="/api/chat", tags=["chat"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
