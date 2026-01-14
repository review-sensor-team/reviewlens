# ReviewLens 모니터링 아키텍처 상세 문서

## 목차
- [개요](#개요)
- [아키텍처 설계](#아키텍처-설계)
- [메트릭 정의](#메트릭-정의)
- [데이터 수집 계층](#데이터-수집-계층)
- [저장 및 쿼리 계층](#저장-및-쿼리-계층)
- [시각화 계층](#시각화-계층)
- [배포 전략](#배포-전략)
- [성능 최적화](#성능-최적화)

---

## 개요

ReviewLens 모니터링 시스템은 **Prometheus + Grafana** 기반으로 구축된 관측성(Observability) 스택입니다. 애플리케이션의 성능, 신뢰성, 사용자 경험을 실시간으로 추적하고 분석할 수 있도록 설계되었습니다.

### 핵심 원칙

1. **자동화**: 미들웨어를 통한 자동 메트릭 수집
2. **최소 침투성**: 비즈니스 로직에 영향 없는 계측
3. **확장성**: 새로운 메트릭 추가 용이
4. **실시간성**: 10-15초 간격 스크랩
5. **유연성**: Docker와 로컬 바이너리 모두 지원

---

## 아키텍처 설계

### 전체 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Application Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   FastAPI    │  │   Dialogue   │  │  LLM Clients │              │
│  │   Server     │──│    Engine    │──│   (Multi)    │              │
│  │              │  │              │  │              │              │
│  │  Middleware  │  │  - Retrieval │  │ - Gemini     │              │
│  │  - Metrics   │  │  - Scoring   │  │ - OpenAI     │              │
│  │  - CORS      │  │  - Evidence  │  │ - Claude     │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                  │                       │
│         └─────────────────┴──────────────────┘                       │
│                           │                                          │
└───────────────────────────┼──────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Metrics Collection Layer                        │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Prometheus Client Registry                      │  │
│  │                                                               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │    HTTP     │  │  Dialogue   │  │     LLM     │          │  │
│  │  │   Metrics   │  │   Metrics   │  │   Metrics   │          │  │
│  │  │             │  │             │  │             │          │  │
│  │  │ - Counter   │  │ - Counter   │  │ - Counter   │          │  │
│  │  │ - Histogram │  │ - Gauge     │  │ - Histogram │          │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  │                                                               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │  Pipeline   │  │    Error    │  │   Business  │          │  │
│  │  │   Metrics   │  │   Metrics   │  │   Metrics   │          │  │
│  │  │             │  │             │  │             │          │  │
│  │  │ - Histogram │  │ - Counter   │  │ - Counter   │          │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                       │
│                             ▼                                       │
│                  ┌─────────────────────┐                            │
│                  │  /metrics Endpoint  │                            │
│                  │  (text/plain)       │                            │
│                  │                     │                            │
│                  │  Prometheus Format  │                            │
│                  └──────────┬──────────┘                            │
└─────────────────────────────┼──────────────────────────────────────┘
                              │ HTTP GET /metrics
                              │ every 10-15 seconds
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Storage & Query Layer                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      Prometheus                               │  │
│  │                        :9090                                  │  │
│  │                                                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐      │  │
│  │  │   Scraper    │  │     TSDB     │  │  PromQL       │      │  │
│  │  │              │  │              │  │  Engine       │      │  │
│  │  │ - Target     │  │ - Samples    │  │               │      │  │
│  │  │   Discovery  │  │ - Chunks     │  │ - Aggregation │      │  │
│  │  │ - Health     │  │ - Retention  │  │ - Functions   │      │  │
│  │  │   Check      │  │              │  │ - Operators   │      │  │
│  │  └──────────────┘  └──────────────┘  └───────────────┘      │  │
│  │                                                               │  │
│  │  Configuration:                                               │  │
│  │  - scrape_interval: 10-15s                                   │  │
│  │  - retention: 15d (default)                                  │  │
│  │  - storage: local TSDB                                       │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────────────┘
                              │ PromQL Queries
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Visualization Layer                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                        Grafana                                │  │
│  │                        :3001                                  │  │
│  │                                                               │  │
│  │  ┌───────────────────────────────────────────────────────┐   │  │
│  │  │                   Dashboards                          │   │  │
│  │  │                                                       │   │  │
│  │  │  1. reviewlens_dashboard.json                        │   │  │
│  │  │     - HTTP Performance                               │   │  │
│  │  │     - Request Rate, Latency, Error Rate              │   │  │
│  │  │                                                       │   │  │
│  │  │  2. reviewlens-demo-kr.json                          │   │  │
│  │  │     - Demo Scenarios                                 │   │  │
│  │  │     - User Journey Tracking                          │   │  │
│  │  │                                                       │   │  │
│  │  │  3. reviewlens-production-kr-v2.json                 │   │  │
│  │  │     - Production Monitoring                          │   │  │
│  │  │     - SLA Tracking                                   │   │  │
│  │  │     - Alerts Overview                                │   │  │
│  │  └───────────────────────────────────────────────────────┘   │  │
│  │                                                               │  │
│  │  Features:                                                    │  │
│  │  - Auto-provisioned datasources                              │  │
│  │  - Auto-loaded dashboards                                    │  │
│  │  - Alert rules (optional)                                    │  │
│  │  - User management                                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 메트릭 정의

### 1. HTTP 메트릭

#### `http_requests_total` (Counter)
- **목적**: 전체 HTTP 요청 수 추적
- **레이블**:
  - `method`: HTTP 메서드 (GET, POST, PUT, DELETE 등)
  - `endpoint`: API 엔드포인트 경로
  - `status_code`: HTTP 상태 코드 (200, 404, 500 등)
- **사용 예시**:
  ```promql
  # 초당 요청 수 (RPS)
  rate(http_requests_total[1m])
  
  # 엔드포인트별 요청 수
  sum by (endpoint) (http_requests_total)
  
  # 에러율 (4xx + 5xx)
  sum(rate(http_requests_total{status_code=~"[45].."}[5m])) / 
  sum(rate(http_requests_total[5m]))
  ```

#### `http_request_duration_seconds` (Histogram)
- **목적**: HTTP 요청 처리 시간 (latency) 추적
- **레이블**:
  - `method`: HTTP 메서드
  - `endpoint`: API 엔드포인트
- **Buckets**: 0.01s, 0.05s, 0.1s, 0.5s, 1.0s, 2.5s, 5.0s, 10.0s
- **자동 생성 메트릭**:
  - `_sum`: 총 누적 시간
  - `_count`: 총 요청 수
  - `_bucket{le="x"}`: 각 버킷별 카운트
- **사용 예시**:
  ```promql
  # p50 latency
  histogram_quantile(0.5, rate(http_request_duration_seconds_bucket[5m]))
  
  # p95 latency
  histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
  
  # p99 latency
  histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
  
  # 평균 latency
  rate(http_request_duration_seconds_sum[5m]) / 
  rate(http_request_duration_seconds_count[5m])
  ```

### 2. 대화 시스템 메트릭

#### `dialogue_sessions_total` (Counter)
- **목적**: 생성된 대화 세션 수
- **레이블**: `category` (제품 카테고리)
- **사용 예시**:
  ```promql
  # 시간당 신규 세션 수
  rate(dialogue_sessions_total[1h]) * 3600
  
  # 카테고리별 세션 분포
  sum by (category) (dialogue_sessions_total)
  ```

#### `dialogue_turns_total` (Counter)
- **목적**: 대화 턴 수 추적
- **레이블**: `category`
- **사용 예시**:
  ```promql
  # 세션당 평균 턴 수
  sum(rate(dialogue_turns_total[1h])) / 
  sum(rate(dialogue_sessions_total[1h]))
  ```

#### `dialogue_completions_total` (Counter)
- **목적**: 완료된 대화 수
- **레이블**: `category`
- **사용 예시**:
  ```promql
  # 완료율
  sum(rate(dialogue_completions_total[1h])) / 
  sum(rate(dialogue_sessions_total[1h]))
  ```

### 3. LLM API 메트릭

#### `llm_calls_total` (Counter)
- **목적**: LLM API 호출 수
- **레이블**:
  - `provider`: LLM 제공자 (gemini, openai, claude)
  - `status`: 상태 (success, error, fallback)
- **사용 예시**:
  ```promql
  # Provider별 호출 분포
  sum by (provider) (llm_calls_total)
  
  # 에러율
  sum(rate(llm_calls_total{status="error"}[5m])) / 
  sum(rate(llm_calls_total[5m]))
  ```

#### `llm_duration_seconds` (Histogram)
- **목적**: LLM API 응답 시간
- **레이블**: `provider`
- **Buckets**: 0.5s, 1.0s, 2.0s, 5.0s, 10.0s, 20.0s, 30.0s
- **사용 예시**:
  ```promql
  # Provider별 p95 latency
  histogram_quantile(0.95, 
    sum by (provider, le) (rate(llm_duration_seconds_bucket[5m]))
  )
  ```

#### `llm_tokens_total` (Counter)
- **목적**: LLM 토큰 사용량
- **레이블**:
  - `provider`
  - `type`: prompt 또는 completion
- **사용 예시**:
  ```promql
  # 시간당 토큰 사용량
  rate(llm_tokens_total[1h]) * 3600
  
  # 비용 추정 (예: $0.001/1K tokens)
  (rate(llm_tokens_total[1h]) * 3600 / 1000) * 0.001
  ```

### 4. 파이프라인 메트릭

#### `retrieval_duration_seconds` (Histogram)
- **목적**: Evidence retrieval 처리 시간
- **레이블**: `category`
- **Buckets**: 0.01s, 0.05s, 0.1s, 0.25s, 0.5s, 1.0s, 2.0s

#### `scoring_duration_seconds` (Histogram)
- **목적**: Factor scoring 처리 시간
- **레이블**: `category`
- **Buckets**: 0.01s, 0.05s, 0.1s, 0.25s, 0.5s, 1.0s

#### `evidence_count` (Histogram)
- **목적**: 검색된 evidence 수
- **레이블**: `category`
- **Buckets**: 0, 1, 2, 3, 5, 10, 20, 50

#### `active_evidence_gauge` (Gauge)
- **목적**: 현재 활성 evidence 수
- **레이블**: `category`, `session_id`

### 5. 에러 메트릭

#### `errors_total` (Counter)
- **목적**: 발생한 에러 수
- **레이블**:
  - `error_type`: 에러 유형
  - `component`: 발생 컴포넌트
- **사용 예시**:
  ```promql
  # 에러 발생률
  rate(errors_total[5m])
  
  # 컴포넌트별 에러 분포
  sum by (component) (errors_total)
  ```

---

## 데이터 수집 계층

### 1. MetricsMiddleware 구현

**위치**: `backend/app/main.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.metrics import (
    http_requests_total,
    http_request_duration_seconds,
)

class MetricsMiddleware(BaseHTTPMiddleware):
    """HTTP 요청 메트릭을 자동으로 수집하는 미들웨어"""
    
    async def dispatch(self, request: Request, call_next):
        # /metrics 엔드포인트는 제외 (무한 루프 방지)
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
        
        # Counter 증가
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        # Histogram 기록
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        # 로깅
        logger.info(
            f"{method} {endpoint} - {status_code} - {duration:.3f}s"
        )
        
        return response
```

**특징**:
- 자동 계측: 모든 HTTP 요청 자동 추적
- 무한 루프 방지: `/metrics` 엔드포인트 제외
- 최소 오버헤드: `time.time()` 만 사용

### 2. 유틸리티 함수

**위치**: `backend/core/metrics.py`

#### Timer 컨텍스트 매니저
```python
class Timer:
    """컨텍스트 매니저로 시간 측정"""
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

# 사용 예시
with Timer(retrieval_duration_seconds, {'category': 'robot_cleaner'}):
    evidence = retrieve_evidence()
```

#### track_time 데코레이터
```python
def track_time(histogram: Histogram, labels: dict = None):
    """함수 실행 시간을 추적하는 데코레이터"""
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

# 사용 예시
@track_time(scoring_duration_seconds, {'category': 'appliance'})
def calculate_scores(reviews):
    # scoring logic
    pass
```

#### track_errors 데코레이터
```python
def track_errors(error_type: str, component: str):
    """에러를 추적하는 데코레이터"""
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

# 사용 예시
@track_errors('retrieval_error', 'retrieval')
def risky_function():
    # may raise exception
    pass
```

---

## 저장 및 쿼리 계층

### Prometheus 설정

#### 로컬 개발 환경

**파일**: `monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s      # 기본 스크랩 간격
  evaluation_interval: 15s  # 규칙 평가 간격
  external_labels:
    monitor: 'reviewlens-monitor'
    environment: 'development'

scrape_configs:
  # Prometheus 자체 모니터링
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # ReviewLens 백엔드 API
  - job_name: 'reviewlens-backend'
    scrape_interval: 10s  # 더 자주 수집
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']
        labels:
          service: 'reviewlens-api'
          env: 'dev'
    
    # 불필요한 메트릭 제외
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'go_.*'  # Go runtime 메트릭 제외
        action: drop
```

#### Docker 환경

**파일**: `monitoring/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 10s
  evaluation_interval: 10s
  external_labels:
    cluster: 'reviewlens'
    environment: 'development'

scrape_configs:
  # ReviewLens API (Docker 컨테이너 → 호스트)
  - job_name: 'reviewlens-api'
    scrape_interval: 10s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['host.docker.internal:8000']
        labels:
          service: 'reviewlens-api'
          component: 'backend'

  # Prometheus 자체
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # 크롤링 스크립트 (선택적)
  - job_name: 'crawl-script'
    scrape_interval: 30s
    static_configs:
      - targets: ['host.docker.internal:8001']
        labels:
          service: 'crawl-script'
          component: 'crawler'
```

**주요 차이점**:
| 설정 | 로컬 | Docker |
|------|------|--------|
| Target | `localhost:8000` | `host.docker.internal:8000` |
| 간격 | 15s/10s | 10s |
| 용도 | 개발 | 스테이징/프로덕션 |

---

## 시각화 계층

### Grafana 구성

#### 데이터소스 자동 프로비저닝

**파일**: `monitoring/grafana/provisioning/datasources/prometheus.yml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: 15  # 초 단위 (숫자)
```

**특징**:
- Grafana 시작 시 자동 데이터소스 생성
- 수동 설정 불필요
- 재시작 시 설정 유지

#### 대시보드 자동 프로비저닝

**파일**: `monitoring/grafana/provisioning/dashboards/dashboard.yml`

```yaml
apiVersion: 1

providers:
  - name: 'ReviewLens Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
```

**대시보드 파일**:
1. `reviewlens_dashboard.json` - 기본 대시보드
2. `reviewlens-demo-kr.json` - 데모용
3. `reviewlens-production-kr-v2.json` - 프로덕션용

### 대시보드 패널 예시

#### 1. HTTP Request Rate (RPS)
```promql
sum(rate(http_requests_total[1m]))
```

#### 2. HTTP Latency (p50/p95/p99)
```promql
# p50
histogram_quantile(0.5, 
  sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
)

# p95
histogram_quantile(0.95, 
  sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
)

# p99
histogram_quantile(0.99, 
  sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
)
```

#### 3. Error Rate (%)
```promql
(
  sum(rate(http_requests_total{status_code=~"[45].."}[5m])) /
  sum(rate(http_requests_total[5m]))
) * 100
```

#### 4. LLM API Performance
```promql
# Calls per minute
rate(llm_calls_total[1m]) * 60

# Success rate
sum(rate(llm_calls_total{status="success"}[5m])) /
sum(rate(llm_calls_total[5m]))

# Average latency by provider
sum by (provider) (rate(llm_duration_seconds_sum[5m])) /
sum by (provider) (rate(llm_duration_seconds_count[5m]))
```

---

## 배포 전략

### Docker Compose 배포

#### 시작
```bash
# 백그라운드 실행
docker-compose -f docker-compose.monitoring.yml up -d

# 로그 확인
docker-compose -f docker-compose.monitoring.yml logs -f

# 특정 서비스만
docker-compose -f docker-compose.monitoring.yml logs -f prometheus
docker-compose -f docker-compose.monitoring.yml logs -f grafana
```

#### 종료
```bash
# 정상 종료 (데이터 유지)
docker-compose -f docker-compose.monitoring.yml down

# 볼륨까지 삭제 (데이터 제거)
docker-compose -f docker-compose.monitoring.yml down -v
```

#### 재시작
```bash
# 설정 변경 후 재시작
docker-compose -f docker-compose.monitoring.yml restart prometheus
docker-compose -f docker-compose.monitoring.yml restart grafana
```

### 로컬 바이너리 배포

#### 시작 스크립트

**파일**: `scripts/start_monitoring.sh`

```bash
#!/bin/bash
# OS 및 아키텍처 감지
# Prometheus/Grafana 다운로드
# 설정 파일 적용
# 프로세스 시작
# PID 저장
```

#### 종료 스크립트

**파일**: `scripts/stop_monitoring.sh`

```bash
#!/bin/bash
# PID 파일에서 프로세스 ID 읽기
# 프로세스 종료 (SIGTERM)
# PID 파일 삭제
```

---

## 성능 최적화

### 1. 메트릭 카디널리티 관리

**문제**: 레이블 값이 너무 많으면 메모리 사용량 급증

**해결책**:
```python
# ❌ 나쁜 예: session_id를 레이블로 사용
dialogue_turns_total.labels(
    session_id=session_id,  # 무한히 증가
    category=category
).inc()

# ✅ 좋은 예: session_id는 로그로, category만 레이블
dialogue_turns_total.labels(
    category=category
).inc()
logger.info(f"Turn recorded for session {session_id}")
```

### 2. Histogram Bucket 최적화

**원칙**: 관심 있는 latency 범위에 집중

```python
# 기본 (과도하게 많음)
buckets=(0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0)

# 최적화 (HTTP 요청용)
buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)

# LLM API용 (더 느림)
buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0)
```

### 3. Scrape Interval 조정

**Trade-off**:
- 짧은 간격 (5s): 더 정확, 높은 부하
- 긴 간격 (60s): 낮은 부하, 덜 정확

**권장**:
- 프로덕션 API: 10-15s
- 배치 작업: 30-60s
- Prometheus 자체: 15s

### 4. Retention 정책

```yaml
# Prometheus 설정
command:
  - '--storage.tsdb.retention.time=15d'  # 15일 보관
  - '--storage.tsdb.retention.size=10GB' # 최대 10GB
```

**권장**:
- 개발: 7-15일
- 프로덕션: 30-90일
- 장기 저장: Thanos, Cortex 등 사용

---

## 알림 설정 (향후 계획)

### Alertmanager 통합

```yaml
# prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

rule_files:
  - "alerts/*.yml"
```

### 알림 규칙 예시

```yaml
# alerts/api_alerts.yml
groups:
  - name: api_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status_code=~"5.."}[5m])) /
            sum(rate(http_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}%"
      
      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High p99 latency"
          description: "p99 latency is {{ $value }}s"
```

---

## 트러블슈팅

### 문제 1: Prometheus가 Target을 스크랩하지 못함

**증상**: Status → Targets에서 "DOWN" 상태

**해결**:
1. FastAPI 서버 실행 확인: `curl http://localhost:8000/metrics`
2. 방화벽 확인
3. Docker 네트워크 확인: `docker network inspect monitoring_default`

### 문제 2: Grafana 대시보드에 데이터가 없음

**증상**: "No data" 표시

**해결**:
1. 데이터소스 연결 확인: Configuration → Data Sources
2. Prometheus 쿼리 테스트
3. 시간 범위 확인 (Last 5 minutes → Last 1 hour)

### 문제 3: 메트릭 값이 이상함

**증상**: Counter가 감소하거나 Histogram이 비어있음

**해결**:
1. 애플리케이션 재시작 후 Counter 리셋 확인
2. 레이블 철자 확인
3. Prometheus 로그 확인: `docker logs reviewlens_prometheus`

---

## 배포 가이드

### 환경별 배포 전략

#### 개발 환경 (로컬)
✅ **로컬 바이너리 방식** - 간단하고 빠름

```bash
./scripts/start_monitoring.sh
```

#### 프로덕션 환경
✅ **Docker Compose 방식** (추천) - 안정적이고 이식성 높음

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### 배포 시나리오별 가이드

#### 1️⃣ AWS EC2 / GCP VM (일반 서버)

**추천: Docker Compose**

```bash
# 1. Docker 설치
sudo apt-get update
sudo apt-get install docker.io docker-compose

# 2. 프로젝트 배포
git clone <your-repo>
cd reviewlens

# 3. 모니터링 스택 시작
docker-compose -f docker-compose.monitoring.yml up -d

# 4. API 서버 시작
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. systemd로 자동 시작 설정
sudo cp deploy/reviewlens-api.service /etc/systemd/system/
sudo systemctl enable reviewlens-api
sudo systemctl start reviewlens-api
```

**장점**:
- ✅ 프로세스 자동 재시작 (Docker restart policy)
- ✅ 로그 중앙화 (docker logs)
- ✅ 포트 격리

#### 2️⃣ AWS ECS / GCP Cloud Run (컨테이너 플랫폼)

**필수: Docker 이미지**

```bash
# 1. API 서버 Dockerfile 생성
cat > Dockerfile <<EOF
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# 2. 이미지 빌드 & 푸시
docker build -t reviewlens-api:latest .
docker tag reviewlens-api:latest <your-registry>/reviewlens-api:latest
docker push <your-registry>/reviewlens-api:latest

# 3. ECS Task Definition / Cloud Run 설정
# monitoring은 별도 서비스로 배포하거나 클라우드 관리형 사용
```

**모니터링 옵션**:
- Option A: Prometheus/Grafana도 컨테이너로 배포
- Option B: **AWS CloudWatch / GCP Cloud Monitoring 사용** (추천)

#### 3️⃣ Kubernetes (EKS, GKE, AKS)

**추천: Helm Chart**

```bash
# 1. Prometheus Operator 설치
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack

# 2. ServiceMonitor 생성 (API 메트릭 스크랩)
kubectl apply -f deploy/k8s/servicemonitor.yaml

# 3. Grafana 대시보드 import
kubectl port-forward svc/prometheus-grafana 3000:80
# http://localhost:3000 접속 후 reviewlens_dashboard.json import
```

#### 4️⃣ 클라우드 관리형 서비스 (가장 간단)

**AWS CloudWatch + Grafana Cloud**

```python
# backend/core/metrics.py 수정
# CloudWatch로 메트릭 전송

import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def send_metric(name, value, unit='Count'):
    cloudwatch.put_metric_data(
        Namespace='ReviewLens',
        MetricData=[{
            'MetricName': name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow()
        }]
    )

# 사용
send_metric('HttpRequests', 1)
```

**Grafana Cloud 연동**:
```bash
# Grafana Cloud Agent 설치
curl -O https://github.com/grafana/agent/releases/latest/download/agent-linux-amd64
sudo mv agent-linux-amd64 /usr/local/bin/grafana-agent

# 설정
cat > agent-config.yaml <<EOF
server:
  log_level: info

metrics:
  wal_directory: /tmp/grafana-agent-wal
  global:
    scrape_interval: 15s
    remote_write:
      - url: https://prometheus-prod-01-eu-west-0.grafana.net/api/prom/push
        basic_auth:
          username: <your-username>
          password: <your-api-key>
  configs:
    - name: reviewlens
      scrape_configs:
        - job_name: reviewlens-api
          static_configs:
            - targets: ['localhost:8000']
EOF
```

**비용**: 무료 티어 사용 가능 (월 10K 시리즈까지 무료)

### 프로덕션 체크리스트

**필수 설정**

- [ ] **프로세스 자동 재시작**
  - systemd (Linux)
  - Docker restart policy
  - Kubernetes liveness probe

- [ ] **로그 관리**
  - 로그 rotation 설정
  - 중앙 로그 수집 (ELK, CloudWatch Logs)

- [ ] **데이터 백업**
  - Prometheus 데이터 볼륨 백업
  - Grafana 대시보드 export

- [ ] **보안**
  - Grafana admin 비밀번호 변경
  - HTTPS 적용 (Nginx/Traefik reverse proxy)
  - 방화벽 설정 (9090, 3001 포트 제한)

- [ ] **알림 설정**
  - Prometheus Alertmanager 설정
  - Slack/Email 알림 채널

**성능 튜닝**

- [ ] Prometheus retention 기간 조정 (기본 15일)
- [ ] Scrape interval 조정 (트래픽에 따라)
- [ ] Grafana query timeout 설정

### 추천 배포 전략

| 환경 | 추천 방식 | 이유 |
|------|----------|------|
| **로컬 개발** | 로컬 바이너리 | 간단, 빠름 |
| **스테이징** | Docker Compose | 프로덕션과 동일 환경 |
| **프로덕션 (소규모)** | Docker Compose | 관리 간편, 비용 낮음 |
| **프로덕션 (중규모)** | Kubernetes | 스케일링, HA |
| **프로덕션 (대규모)** | 클라우드 관리형 | 운영 부담 최소화 |

### 마이그레이션 가이드

**로컬 바이너리 → Docker Compose**

```bash
# 1. 로컬 모니터링 중지
./scripts/stop_monitoring.sh

# 2. Docker Compose로 시작
docker-compose -f docker-compose.monitoring.yml up -d

# 3. 데이터 마이그레이션 (필요시)
docker cp monitoring/data/prometheus/. reviewlens_prometheus:/prometheus/
```

**Docker Compose → Kubernetes**

```bash
# 1. Helm으로 Prometheus 설치
helm install prometheus prometheus-community/kube-prometheus-stack

# 2. 대시보드 ConfigMap 생성
kubectl create configmap reviewlens-dashboard \
  --from-file=monitoring/grafana/dashboards/reviewlens_dashboard.json

# 3. ServiceMonitor 배포
kubectl apply -f deploy/k8s/
```

### 비용 비교

| 방식 | 월 비용 (예상) | 관리 난이도 |
|------|---------------|------------|
| 로컬 바이너리 | $0 | 낮음 |
| Docker Compose | $0 (서버 비용만) | 중간 |
| Kubernetes | $50-200 (클러스터) | 높음 |
| Grafana Cloud | $0-50 (트래픽) | 낮음 |
| AWS CloudWatch | $10-100 (메트릭 수) | 중간 |

### FAQ

**Q: 로컬 바이너리로 배포해도 되나요?**  
A: 개발/테스트는 괜찮지만, 프로덕션은 Docker나 클라우드 관리형 추천

**Q: Docker 없이 프로덕션 배포하려면?**  
A: systemd로 프로세스 관리 + nginx reverse proxy + 백업 자동화 필요

**Q: 가장 간단한 프로덕션 방법은?**  
A: Grafana Cloud (무료 티어) + CloudWatch/Cloud Monitoring 조합

**Q: Kubernetes 꼭 필요한가요?**  
A: 소규모는 불필요. 트래픽 많고 HA 필요하면 고려

**Q: 비용을 최소화하려면?**  
A: Docker Compose + 작은 EC2/VM 인스턴스 ($5-10/월)

---

## 참고 자료

- [Prometheus 공식 문서](https://prometheus.io/docs/)
- [Grafana 공식 문서](https://grafana.com/docs/)
- [prometheus-client Python](https://github.com/prometheus/client_python)
- [PromQL 가이드](https://prometheus.io/docs/prometheus/latest/querying/basics/)
