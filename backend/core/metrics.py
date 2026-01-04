"""
Prometheus 메트릭 정의
애플리케이션의 성능 및 상태를 추적하기 위한 Prometheus 지표들
"""
import time
from functools import wraps
from typing import Callable, Any
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest

# Prometheus registry
REGISTRY = CollectorRegistry()

# ============================================================================
# HTTP 요청 메트릭
# ============================================================================

# HTTP 요청 총 수 (경로별, 메서드별, 상태코드별)
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

# HTTP 요청 처리 시간 (latency)
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY
)

# ============================================================================
# 챗봇/대화 메트릭
# ============================================================================

# 대화 세션 수
dialogue_sessions_total = Counter(
    'dialogue_sessions_total',
    'Total dialogue sessions',
    ['category'],
    registry=REGISTRY
)

# 대화 턴 수
dialogue_turns_total = Counter(
    'dialogue_turns_total',
    'Total dialogue turns',
    ['category'],
    registry=REGISTRY
)

# 대화 완료 수 (is_final=True)
dialogue_completions_total = Counter(
    'dialogue_completions_total',
    'Total dialogue completions',
    ['category'],
    registry=REGISTRY
)

# ============================================================================
# 파이프라인 단계별 메트릭
# ============================================================================

# 리트리벌 처리 시간
retrieval_duration_seconds = Histogram(
    'retrieval_duration_seconds',
    'Retrieval stage latency',
    ['category'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
    registry=REGISTRY
)

# 검색된 evidence 수
evidence_count = Histogram(
    'evidence_count',
    'Number of evidence reviews retrieved',
    ['category'],
    buckets=(0, 1, 2, 3, 5, 10, 20, 50),
    registry=REGISTRY
)

# 현재 활성 evidence 수 (gauge)
active_evidence_gauge = Gauge(
    'active_evidence_count',
    'Current number of evidence reviews',
    ['category', 'session_id'],
    registry=REGISTRY
)

# 점수 계산 처리 시간
scoring_duration_seconds = Histogram(
    'scoring_duration_seconds',
    'Scoring stage latency',
    ['category'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=REGISTRY
)

# ============================================================================
# LLM 메트릭
# ============================================================================

# LLM 호출 수
llm_calls_total = Counter(
    'llm_calls_total',
    'Total LLM API calls',
    ['provider', 'status'],  # status: success, error, fallback
    registry=REGISTRY
)

# LLM 응답 시간
llm_duration_seconds = Histogram(
    'llm_duration_seconds',
    'LLM API call latency',
    ['provider'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0),
    registry=REGISTRY
)

# LLM 토큰 사용량
llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens used by LLM',
    ['provider', 'type'],  # type: prompt, completion
    registry=REGISTRY
)

# ============================================================================
# 에러 메트릭
# ============================================================================

# 에러 발생 수
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'component'],
    registry=REGISTRY
)

# ============================================================================
# 비즈니스 메트릭
# ============================================================================

# 제품별 분석 요청 수
product_analysis_total = Counter(
    'product_analysis_total',
    'Total product analysis requests',
    ['category'],
    registry=REGISTRY
)

# 리뷰 처리 수
reviews_processed_total = Counter(
    'reviews_processed_total',
    'Total reviews processed',
    ['category'],
    registry=REGISTRY
)

# Factor 매칭 수
factors_matched_total = Counter(
    'factors_matched_total',
    'Total factors matched',
    ['category'],
    registry=REGISTRY
)


# ============================================================================
# 유틸리티 함수 및 데코레이터
# ============================================================================

def track_time(histogram: Histogram, labels: dict = None):
    """
    함수 실행 시간을 추적하는 데코레이터
    
    Usage:
        @track_time(retrieval_duration_seconds, {'category': 'appliance'})
        def retrieve_reviews():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    histogram.labels(**labels).observe(duration)
                else:
                    histogram.observe(duration)
        return wrapper
    return decorator


def track_errors(error_type: str, component: str):
    """
    에러를 추적하는 데코레이터
    
    Usage:
        @track_errors('retrieval_error', 'retrieval')
        def risky_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                errors_total.labels(
                    error_type=error_type,
                    component=component
                ).inc()
                raise
        return wrapper
    return decorator


class Timer:
    """
    컨텍스트 매니저로 시간 측정
    
    Usage:
        with Timer(retrieval_duration_seconds, {'category': 'appliance'}):
            # do something
            pass
    """
    def __init__(self, histogram: Histogram, labels: dict = None):
        self.histogram = histogram
        self.labels = labels or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if self.labels:
            self.histogram.labels(**self.labels).observe(duration)
        else:
            self.histogram.observe(duration)


def get_metrics() -> bytes:
    """
    Prometheus 포맷으로 모든 메트릭 반환
    /metrics 엔드포인트에서 사용
    """
    return generate_latest(REGISTRY)
