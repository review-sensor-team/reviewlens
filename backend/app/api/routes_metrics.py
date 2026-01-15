"""Metrics API routes for Prometheus"""
from fastapi import APIRouter
from ..core.metrics import get_metrics

router = APIRouter()


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics 엔드포인트
    Prometheus가 이 엔드포인트를 스크랩하여 메트릭을 수집합니다.
    """
    return get_metrics()

