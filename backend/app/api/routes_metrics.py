"""
메트릭 엔드포인트
Prometheus가 스크랩할 메트릭 노출
"""
from fastapi import APIRouter, Response
from ..core.metrics import get_metrics

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics():
    """
    Prometheus 메트릭 엔드포인트
    
    Prometheus가 이 엔드포인트를 주기적으로 스크랩하여
    애플리케이션의 성능 지표를 수집합니다.
    
    반환 형식: Prometheus text format
    """
    metrics_data = get_metrics()
    return Response(
        content=metrics_data,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )
