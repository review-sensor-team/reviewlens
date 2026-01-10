"""Prometheus metrics for ReviewLens monitoring"""
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from fastapi import Response

# ============================================================================
# HTTP Metrics (HTTP 메트릭)
# ============================================================================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# ============================================================================
# Business Metrics (비즈니스 메트릭)
# ============================================================================

dialogue_sessions_total = Counter(
    'dialogue_sessions_total',
    'Total dialogue sessions started',
    ['category']
)

dialogue_turns_total = Counter(
    'dialogue_turns_total',
    'Total dialogue turns',
    ['session_id', 'is_final']
)

dialogue_completions_total = Counter(
    'dialogue_completions_total',
    'Total completed dialogues',
    ['session_id']
)

# ============================================================================
# Performance Metrics (성능 메트릭)
# ============================================================================

retrieval_duration_seconds = Histogram(
    'retrieval_duration_seconds',
    'Evidence retrieval duration in seconds',
    ['method']  # 'factor_based', 'vector', 'keyword'
)

scoring_duration_seconds = Histogram(
    'scoring_duration_seconds',
    'Factor scoring duration in seconds',
    ['factor_key']
)

evidence_count = Histogram(
    'evidence_count',
    'Number of evidence reviews retrieved',
    ['type']  # 'positive', 'negative', 'mixed'
)

# ============================================================================
# LLM Metrics (LLM 메트릭)
# ============================================================================

llm_calls_total = Counter(
    'llm_calls_total',
    'Total LLM API calls',
    ['model', 'status']  # 'success', 'error', 'timeout'
)

llm_duration_seconds = Histogram(
    'llm_duration_seconds',
    'LLM API response time in seconds',
    ['model']
)

# ============================================================================
# Error Metrics (에러 메트릭)
# ============================================================================

errors_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'endpoint']
)

# ============================================================================
# User Journey Metrics (사용자 여정 메트릭) - 선택사항
# ============================================================================

user_journey_stage_total = Counter(
    'user_journey_stage_total',
    'User journey stage progression',
    ['stage', 'status']  # stage: 단계명, status: 'start' | 'complete'
)

# ============================================================================
# Metrics Endpoint Helper
# ============================================================================

def get_metrics() -> Response:
    """Generate Prometheus metrics response"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
