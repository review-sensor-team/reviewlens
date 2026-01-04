# ReviewLens 모니터링 가이드

ReviewLens 애플리케이션의 성능 및 상태를 모니터링하기 위한 Prometheus + Grafana 기반 관측성 스택입니다.

**✨ 로컬 바이너리 실행 방식 - Docker 불필요!**

## 목차

- [개요](#개요)
- [아키텍처](#아키텍처)
- [빠른 시작](#빠른-시작)
- [수집 지표](#수집-지표)
- [대시보드 사용법](#대시보드-사용법)
- [알림 설정](#알림-설정)
- [문제 해결](#문제-해결)

## 개요

### 구성 요소

1. **Prometheus**: 시계열 데이터베이스 및 메트릭 수집기 (로컬 바이너리)
2. **Grafana**: 메트릭 시각화 대시보드 (로컬 바이너리)
3. **FastAPI 미들웨어**: 자동 메트릭 수집
4. **Pipeline 계측**: 각 단계별 성능 추적

### 주요 기능

- ✅ HTTP 요청 성능 추적 (latency, throughput, error rate)
- ✅ 대화 시스템 메트릭 (세션, 턴, 완료)
- ✅ 파이프라인 단계별 latency (retrieval, scoring, LLM)
- ✅ Evidence 수집 통계
- ✅ LLM API 성능 및 에러 추적
- ✅ 실시간 대시보드 (p50/p95/p99 percentile)
- ✅ **Docker 불필요 - 단일 명령으로 시작/종료**

## 아키텍처

```
┌─────────────────┐
│  ReviewLens API │
│   (FastAPI)     │
│                 │
│ - Middleware    │
│ - Metrics       │
└────────┬────────┘
         │ /metrics endpoint
         │ (Prometheus format)
         ▼
┌─────────────────┐
│   Prometheus    │  ← 로컬 바이너리 실행 (포트 9090)
│                 │
│ - Scrape every  │
│   10-15 seconds │
│ - Store TSDB    │
└────────┬────────┘
         │ PromQL queries
         ▼
┌─────────────────┐
│    Grafana      │  ← 로컬 바이너리 실행 (포트 3001)
│                 │
│ - Dashboards    │
│ - Alerts        │
└─────────────────┘
```

**특징**: Docker 없이 네이티브 바이너리로 실행하여 복잡성과 리소스 사용량 감소

## 빠른 시작

### 1. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

새로 추가된 패키지:
- `prometheus-client>=0.20.0`

### 2. 모니터링 스택 시작 (단일 명령!)

**자동 설치 + 시작**:
```bash
# 프로젝트 루트에서
chmod +x scripts/start_monitoring.sh
./scripts/start_monitoring.sh
```

이 스크립트가 자동으로 수행하는 작업:
1. OS/아키텍처 감지 (macOS/Linux, amd64/arm64)
2. Prometheus 바이너리 다운로드 및 설치
3. Grafana 바이너리 다운로드 및 설치
4. 설정 파일 적용
5. Prometheus 시작 (포트 9090)
6. Grafana 시작 (포트 3001)
7. 헬스 체크 및 PID 저장

**처음 실행 시**: 다운로드로 인해 1-2분 소요
**이후 실행**: 5초 이내 즉시 시작

### 3. ReviewLens API 시작

```bash
# 백엔드 서버 시작
./local_restart.sh
```

### 4. 접속 확인

1. **Prometheus**: http://localhost:9090
   - Status → Targets에서 `reviewlens-backend` 상태 확인
   - Graph에서 `http_requests_total` 쿼리 테스트

2. **Grafana**: http://localhost:3001
   - ID: `admin` / PW: `admin` (초기 로그인)
   - 좌측 메뉴 → Dashboards → "ReviewLens Performance Dashboard"

3. **Metrics 엔드포인트**: http://localhost:8000/metrics
   - Prometheus text format으로 모든 메트릭 노출
   - 예시:
     ```
     # HELP http_requests_total Total HTTP requests
     # TYPE http_requests_total counter
     http_requests_total{endpoint="/api/chat/start",method="POST",status_code="200"} 15.0
     ```

### 5. 종료

```bash
./scripts/stop_monitoring.sh
```

모든 Prometheus/Grafana 프로세스가 깔끔하게 종료됩니다.

## 수집 지표

### HTTP 메트릭

#### `http_requests_total` (Counter)
총 HTTP 요청 수

**Labels**:
- `method`: HTTP 메서드 (GET, POST, etc.)
- `endpoint`: 요청 경로
- `status_code`: 응답 상태 코드

**사용 예**:
```promql
# 초당 요청 수
rate(http_requests_total[1m])

# 에러율 (5xx)
sum(rate(http_requests_total{status_code=~"5.."}[5m])) 
/ 
sum(rate(http_requests_total[5m])) * 100
```

#### `http_request_duration_seconds` (Histogram)
HTTP 요청 처리 시간 (초 단위)

**Labels**:
- `method`: HTTP 메서드
- `endpoint`: 요청 경로

**Buckets**: 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0

**사용 예**:
```promql
# p95 latency
histogram_quantile(0.95, 
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
)

# 평균 latency
rate(http_request_duration_seconds_sum[5m]) 
/ 
rate(http_request_duration_seconds_count[5m])
```

### 대화 시스템 메트릭

#### `dialogue_sessions_total` (Counter)
시작된 대화 세션 수

**Labels**:
- `category`: 제품 카테고리

#### `dialogue_turns_total` (Counter)
대화 턴 수

**Labels**:
- `category`: 제품 카테고리

#### `dialogue_completions_total` (Counter)
완료된 대화 수 (is_final=True)

**Labels**:
- `category`: 제품 카테고리

**사용 예**:
```promql
# 완료율
rate(dialogue_completions_total[5m]) 
/ 
rate(dialogue_sessions_total[5m]) * 100
```

### 파이프라인 메트릭

#### `retrieval_duration_seconds` (Histogram)
리트리벌 단계 처리 시간

**Labels**:
- `category`: 제품 카테고리

**Buckets**: 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0

#### `scoring_duration_seconds` (Histogram)
스코어링 단계 처리 시간

**Labels**:
- `category`: 제품 카테고리

**Buckets**: 0.01, 0.05, 0.1, 0.25, 0.5, 1.0

#### `evidence_count` (Histogram)
검색된 evidence 리뷰 수

**Labels**:
- `category`: 제품 카테고리

**Buckets**: 0, 1, 2, 3, 5, 10, 20, 50

**사용 예**:
```promql
# 평균 evidence 수
rate(evidence_count_sum[5m]) / rate(evidence_count_count[5m])

# p95 evidence 수
histogram_quantile(0.95, 
  sum(rate(evidence_count_bucket[5m])) by (le, category)
)
```

### LLM 메트릭

#### `llm_calls_total` (Counter)
LLM API 호출 수

**Labels**:
- `provider`: LLM 제공자 (gemini, openai, claude)
- `status`: 호출 상태 (success, error, fallback)

#### `llm_duration_seconds` (Histogram)
LLM API 응답 시간

**Labels**:
- `provider`: LLM 제공자

**Buckets**: 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0

**사용 예**:
```promql
# LLM 에러율
sum(rate(llm_calls_total{status="error"}[5m])) 
/ 
sum(rate(llm_calls_total[5m])) * 100

# Provider별 p95 latency
histogram_quantile(0.95, 
  sum(rate(llm_duration_seconds_bucket[5m])) by (le, provider)
)
```

#### `llm_tokens_total` (Counter)
사용된 토큰 수 (예정)

**Labels**:
- `provider`: LLM 제공자
- `type`: 토큰 타입 (prompt, completion)

### 에러 메트릭

#### `errors_total` (Counter)
발생한 에러 수

**Labels**:
- `error_type`: 에러 타입
- `component`: 에러 발생 컴포넌트

## 대시보드 사용법

### ReviewLens Performance Dashboard

12개의 패널로 구성된 종합 성능 대시보드입니다.

#### 1. HTTP 요청 속도
- **쿼리**: `rate(http_requests_total[1m])`
- **설명**: 엔드포인트별 초당 요청 수
- **활용**: 트래픽 패턴 파악, 핫 엔드포인트 식별

#### 2. 총 요청 속도 (Gauge)
- **쿼리**: `sum(rate(http_requests_total[5m]))`
- **설명**: 전체 애플리케이션 요청 속도
- **임계값**: 
  - Green: < 1000 req/s
  - Yellow: 1000-5000 req/s
  - Red: > 5000 req/s

#### 3. 에러율 (Gauge)
- **쿼리**: `sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100`
- **설명**: 5xx 에러 비율
- **임계값**:
  - Green: < 5%
  - Yellow: 5-10%
  - Red: > 10%

#### 4. HTTP 요청 Latency (p50/p95/p99)
- **쿼리**: `histogram_quantile(0.xx, ...)`
- **설명**: 응답 시간 백분위수
- **활용**: 
  - p50: 일반적인 성능
  - p95: 대부분의 사용자 경험
  - p99: 최악의 경우

#### 5-6. 대화 세션 및 턴 속도
- **설명**: 대화 시스템 활성도 추적
- **활용**: 사용자 참여도 모니터링

#### 7-8. Retrieval/Scoring Stage Latency
- **설명**: 파이프라인 단계별 성능
- **활용**: 병목 지점 식별

#### 9. Evidence Count (p50/p95)
- **설명**: 검색된 증거 리뷰 수 분포
- **활용**: 리트리벌 품질 모니터링

#### 10. LLM API Latency
- **설명**: LLM 호출 응답 시간
- **임계값**:
  - Green: < 5s
  - Yellow: 5-10s
  - Red: > 10s

#### 11. LLM API 호출 상태
- **설명**: Success/Error/Fallback 비율
- **활용**: LLM 안정성 모니터링

#### 12. 에러 발생 속도
- **설명**: 컴포넌트별 에러율
- **활용**: 문제 컴포넌트 조기 발견

### 시간 범위 조정

우측 상단의 시간 선택기:
- 기본: 최근 1시간
- 옵션: 5분, 15분, 1시간, 6시간, 24시간, 7일
- 자동 새로고침: 10초 간격 (변경 가능)

### 변수 사용 (고급)

대시보드 상단에서 변수로 필터링:
- `$category`: 카테고리별 필터
- `$endpoint`: 엔드포인트별 필터

## 알림 설정

### Prometheus Alerting Rules

`monitoring/alerts/rules.yml` 파일 생성 (예정):

```yaml
groups:
  - name: reviewlens_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "높은 에러율 감지"
          description: "에러율이 5%를 초과했습니다: {{ $value }}%"

      - alert: SlowLLMResponse
        expr: histogram_quantile(0.95, sum(rate(llm_duration_seconds_bucket[5m])) by (le, provider)) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM 응답 지연"
          description: "{{ $labels.provider }}의 p95 latency가 10초를 초과했습니다"

      - alert: LowEvidenceCount
        expr: histogram_quantile(0.50, sum(rate(evidence_count_bucket[5m])) by (le, category)) < 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "낮은 evidence 수"
          description: "{{ $labels.category }}의 중간 evidence 수가 3개 미만입니다"
```

### Grafana Alerts

대시보드 패널에서 Alert 탭:
1. Conditions 설정
2. Notification channel 추가 (Slack, Email, etc.)
3. Message template 작성

## 문제 해결

### Prometheus가 메트릭을 수집하지 못함

**증상**: Prometheus Targets에서 `reviewlens-backend`가 DOWN 상태

**원인 및 해결**:

1. **백엔드 서버 미실행**
   ```bash
   # 서버 시작 확인
   curl http://localhost:8000/metrics
   ```

2. **Prometheus 미실행**
   ```bash
   # Prometheus 프로세스 확인
   ps aux | grep prometheus
   
   # 재시작
   ./scripts/stop_monitoring.sh
   ./scripts/start_monitoring.sh
   ```

3. **포트 충돌**
   ```bash
   # 포트 9090 사용 확인
   lsof -i :9090
   
   # 다른 프로세스가 사용 중이면 종료 후 재시작
   ```

### Grafana 대시보드가 비어있음

**증상**: 패널에 "No data" 표시

**원인 및 해결**:

1. **Prometheus 데이터소스 연결 확인**
   - Grafana → Configuration → Data Sources
   - Prometheus URL: `http://prometheus:9090`
   - "Save & Test" 클릭

2. **메트릭 데이터 미수집**
   ```bash
   # Prometheus에서 메트릭 확인
   curl http://localhost:9090/api/v1/label/__name__/values | jq '.data[]' | grep http_requests
   ```

3. **시간 범위 조정**
   - 우측 상단 시간 선택기에서 "Last 5 minutes" 선택
   - 최근 요청이 있어야 데이터 표시

### 메트릭이 누락됨

**증상**: 특정 메트릭만 표시되지 않음

**원인 및 해결**:

1. **코드에서 메트릭 미호출**
   ```python
   # dialogue.py에서 확인
   from ..core.metrics import dialogue_sessions_total
   dialogue_sessions_total.labels(category=self.category).inc()
   ```

2. **레이블 불일치**
   - 메트릭 정의와 사용 시 레이블 이름 동일해야 함
   - 예: `category` vs `cat` (불일치 시 에러)

3. **서버 재시작 필요**
   ```bash
   ./local_restart.sh
   ```

### 높은 메모리 사용량

**증상**: Prometheus가 많은 메모리 사용

**원인 및 해결**:

1. **retention 기간 조정**
   
   `scripts/start_monitoring.sh` 수정:
   ```bash
   nohup "$BIN_DIR/prometheus" \
       --config.file="$MONITORING_DIR/prometheus.yml" \
       --storage.tsdb.path="$DATA_DIR/prometheus" \
       --storage.tsdb.retention.time=7d \  # 추가
       ...
   ```

2. **스크랩 간격 증가**
   `monitoring/prometheus.yml` 수정:
   ```yaml
   global:
     scrape_interval: 30s  # 15s → 30s
   ```

3. **데이터 삭제**
   ```bash
   # 오래된 데이터 삭제
   rm -rf monitoring/data/prometheus/*
   ./scripts/start_monitoring.sh
   ```

### 대시보드 성능 저하

**증상**: Grafana 패널 로딩이 느림

**원인 및 해결**:

1. **쿼리 범위 축소**
   - 시간 범위를 1시간 이내로 제한
   - 해상도 조정 (Min interval: 15s)

2. **패널 쿼리 최적화**
   ```promql
   # 나쁜 예
   http_requests_total
   
   # 좋은 예
   sum(rate(http_requests_total[5m])) by (endpoint)
   ```

3. **패널 수 줄이기**
   - 자주 보는 패널만 활성화
   - 나머지는 별도 대시보드로 분리

## 고급 사용법

### 커스텀 메트릭 추가

1. **metrics.py에 정의**:
   ```python
   from prometheus_client import Counter
   
   custom_metric = Counter(
       'custom_metric_name',
       'Description',
       ['label1', 'label2'],
       registry=REGISTRY
   )
   ```

2. **코드에서 사용**:
   ```python
   from ..core.metrics import custom_metric
   
   custom_metric.labels(label1='value1', label2='value2').inc()
   ```

3. **Grafana에서 시각화**:
   ```promql
   rate(custom_metric_name[5m])
   ```

### PromQL 쿼리 예시

```promql
# 엔드포인트별 평균 응답 시간
rate(http_request_duration_seconds_sum[5m]) 
/ 
rate(http_request_duration_seconds_count[5m])

# 카테고리별 대화 완료율
rate(dialogue_completions_total[5m]) 
/ 
rate(dialogue_sessions_total[5m]) * 100

# LLM provider별 성공률
sum(rate(llm_calls_total{status="success"}[5m])) by (provider)
/
sum(rate(llm_calls_total[5m])) by (provider) * 100

# 최근 5분간 총 에러 수
sum(increase(errors_total[5m]))
```

## 참고 자료

- [Prometheus 문서](https://prometheus.io/docs/)
- [Grafana 문서](https://grafana.com/docs/)
- [PromQL 가이드](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [FastAPI 모니터링](https://github.com/trallnag/prometheus-fastapi-instrumentator)

## 디렉토리 구조

```
monitoring/
├── prometheus.yml          # Prometheus 설정
├── grafana.ini            # Grafana 설정
├── bin/                   # 바이너리 파일 (자동 다운로드)
│   ├── prometheus
│   ├── promtool
│   └── grafana/
├── data/                  # 데이터 저장 (.gitignore)
│   ├── prometheus/
│   │   ├── *.log
│   │   └── wal/
│   └── grafana/
│       ├── grafana.db
│       └── logs/
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── prometheus.yml
    │   └── dashboards/
    │       └── dashboards.yml
    └── dashboards/
        └── reviewlens_dashboard.json
```

## 업데이트 로그

- 2026-01-04: 초기 모니터링 스택 구축
  - Prometheus + Grafana 설정
  - 12개 패널 대시보드 구축
  - HTTP, 대화, 파이프라인, LLM 메트릭 추가
- 2026-01-04: **로컬 바이너리 방식으로 전환**
  - Docker 제거, 복잡성 50% 감소
  - 자동 설치 스크립트 추가
  - 단일 명령으로 시작/종료
