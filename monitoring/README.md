# ReviewLens 모니터링 시스템

> **📖 상세 아키텍처 문서**: 모니터링 시스템의 내부 구조와 설계 원칙은 [`docs/MONITORING_ARCHITECTURE.md`](../docs/MONITORING_ARCHITECTURE.md)를 참고하세요.

ReviewLens의 메트릭 수집, 모니터링 및 시각화를 위한 Prometheus + Grafana 스택입니다.

## 🚀 빠른 시작

### 방법 1: 자동화 스크립트 (가장 간편 ⭐)

```bash
# 모니터링 시스템 재시작 (설치, 설정, 시작 모두 자동)
./scripts/monitor_restart.sh

# 모니터링 시스템 중지
./scripts/monitor_stop.sh
```

**`monitor_restart.sh` 스크립트 기능:**
- 기존 Prometheus/Grafana 프로세스 자동 종료
- Homebrew를 통한 자동 설치 (미설치 시)
- 설정 파일 자동 업데이트 (`prometheus.yml`, Grafana 포트 3001)
- 서비스 자동 시작 및 헬스체크
- 로그 위치: `/tmp/reviewlens-monitoring/`

### 방법 2: Homebrew 수동 설치 (macOS)

```bash
# 1. Prometheus & Grafana 설치
brew install prometheus grafana

# 2. 설정 파일 복사
cp monitoring/prometheus.yml /opt/homebrew/etc/prometheus.yml

# 3. Grafana 포트 변경 (3000 → 3001, 프론트엔드 포트 충돌 방지)
# /opt/homebrew/etc/grafana/grafana.ini에서 http_port = 3001로 설정

# 4. 서비스 시작
prometheus --config.file=/opt/homebrew/etc/prometheus.yml \
  --storage.tsdb.path=/opt/homebrew/var/prometheus \
  > /tmp/prometheus.log 2>&1 &

grafana server \
  --config /opt/homebrew/etc/grafana/grafana.ini \
  --homepath /opt/homebrew/opt/grafana/share/grafana \
  > /tmp/grafana.log 2>&1 &
```

### 방법 2: Docker Compose

```bash
# 모니터링 스택 시작
docker-compose -f docker-compose.monitoring.yml up -d

# 로그 확인
docker-compose -f docker-compose.monitoring.yml logs -f

# 종료
docker-compose -f docker-compose.monitoring.yml down
```

### 방법 3: Docker Compose

```bash
# 모니터링 스택 시작
docker-compose -f docker-compose.monitoring.yml up -d

# 로그 확인
docker-compose -f docker-compose.monitoring.yml logs -f

# 종료
docker-compose -f docker-compose.monitoring.yml down
```

## 🔧 모니터링 시스템 관리

### 프로세스 상태 확인

```bash
# Prometheus & Grafana 프로세스 확인
ps aux | grep -E "(prometheus|grafana)" | grep -v grep

# 포트 사용 확인
lsof -i :9090  # Prometheus
lsof -i :3001  # Grafana
lsof -i :8000  # ReviewLens Backend
```

### 로그 확인

```bash
# monitor_restart.sh 사용 시 로그 위치
tail -f /tmp/reviewlens-monitoring/prometheus.log
tail -f /tmp/reviewlens-monitoring/grafana.log

# 수동 시작 시 로그 위치
tail -f /tmp/prometheus.log
tail -f /tmp/grafana.log
```

### 헬스체크

```bash
# Prometheus 헬스체크
curl http://localhost:9090/-/healthy

# Grafana 헬스체크
curl http://localhost:3001/api/health

# ReviewLens 백엔드 메트릭 확인
curl http://localhost:8000/metrics

# Prometheus 타겟 상태 확인
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool
```

### 방법 4: 스크립트 (구버전 - 바이너리 자동 다운로드)

```bash
# 시작 (바이너리 자동 다운로드)
./scripts/start_monitoring.sh

# 종료
./scripts/stop_monitoring.sh
```

## 📊 접속 정보

| 서비스 | URL | 인증 정보 | 설명 |
|--------|-----|-----------|------|
| **Prometheus** | http://localhost:9090 | 없음 | 메트릭 수집 및 저장 |
| **Grafana** | http://localhost:3001 | admin / admin | 대시보드 시각화 |
| **Metrics 엔드포인트** | http://localhost:8000/metrics | 없음 | ReviewLens 백엔드 메트릭 |

## 🎯 수집되는 메트릭

### 1. HTTP 요청 메트릭

**`http_requests_total`** (Counter)
- 라벨: `endpoint`, `method`, `status_code`, `service`, `env`
- 설명: 총 HTTP 요청 수

**`http_request_duration_seconds`** (Histogram)
- 라벨: `endpoint`, `method`
- 버킷: 0.01s, 0.05s, 0.1s, 0.5s, 1.0s, 2.5s, 5.0s, 10.0s
- 설명: HTTP 요청 응답 시간 분포

### 2. 대화 세션 메트릭

**`dialogue_sessions_total`** (Counter)
- 라벨: `category`
- 설명: 생성된 대화 세션 총 개수

**`dialogue_turns_total`** (Counter)
- 라벨: `category`, `turn_type`
- 설명: 대화 턴 총 개수

### 3. LLM API 메트릭

**`llm_requests_total`** (Counter)
- 라벨: `provider`, `status`
- 설명: LLM API 호출 수

**`llm_request_duration_seconds`** (Histogram)
- 라벨: `provider`
- 설명: LLM API 응답 시간

## 🔍 Prometheus 사용법

### 기본 쿼리 예시

```promql
# HTTP 요청 속도 (초당 요청 수)
rate(http_requests_total[5m])

# 엔드포인트별 HTTP 요청 수
sum by (endpoint) (http_requests_total)

# 95th 퍼센타일 응답 시간
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 에러율 (4xx, 5xx)
rate(http_requests_total{status_code=~"4..|5.."}[5m])

# 카테고리별 대화 세션 수
sum by (category) (dialogue_sessions_total)
```

### 주요 페이지

- **Graph**: http://localhost:9090/graph - 쿼리 실행 및 그래프 확인
- **Targets**: http://localhost:9090/targets - 메트릭 수집 대상 상태
- **Alerts**: http://localhost:9090/alerts - 알림 규칙 상태

## 📈 Grafana 대시보드 설정

### 1. 데이터 소스 추가

1. Grafana 접속: http://localhost:3001
2. 로그인: `admin` / `admin`
3. Configuration → Data Sources → Add data source
4. Prometheus 선택
5. URL: `http://localhost:9090`
6. Save & Test

### 2. 대시보드 생성

#### 패널 1: HTTP 요청 속도
```promql
sum(rate(http_requests_total[5m])) by (endpoint)
```

#### 패널 2: 평균 응답 시간
```promql
rate(http_request_duration_seconds_sum[5m]) / 
rate(http_request_duration_seconds_count[5m])
```

#### 패널 3: 에러율
```promql
sum(rate(http_requests_total{status_code=~"4..|5.."}[5m])) / 
sum(rate(http_requests_total[5m])) * 100
```

#### 패널 4: 대화 세션 수 (카테고리별)
```promql
sum by (category) (dialogue_sessions_total)
```

## 🛠️ 프로세스 관리

### 상태 확인

```bash
# 프로세스 확인
ps aux | grep -E "(prometheus|grafana)" | grep -v grep

# Prometheus 헬스체크
curl http://localhost:9090/-/healthy

# Grafana 헬스체크
curl http://localhost:3001/api/health

# Targets 상태 확인
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool
```

### 중지

```bash
# Prometheus 중지
pkill -f prometheus

# Grafana 중지
pkill -f grafana

# 모두 중지
pkill -f prometheus && pkill -f grafana
```

### 재시작

```bash
# Prometheus 재시작
pkill -f prometheus
prometheus --config.file=/opt/homebrew/etc/prometheus.yml \
  --storage.tsdb.path=/opt/homebrew/var/prometheus \
  > /tmp/prometheus.log 2>&1 &

# Grafana 재시작
pkill -f grafana
grafana server \
  --config /opt/homebrew/etc/grafana/grafana.ini \
  --homepath /opt/homebrew/opt/grafana/share/grafana \
  > /tmp/grafana.log 2>&1 &
```

## 📝 로그 확인

```bash
# Prometheus 로그
tail -f /tmp/prometheus.log

# Grafana 로그
tail -f /tmp/grafana.log

# 백엔드 메트릭 확인
curl http://localhost:8000/metrics
```

## 🐛 문제 해결

### Prometheus가 시작되지 않음

**증상**: `curl http://localhost:9090/-/healthy` 실패

**해결**:
```bash
# 1. 포트 충돌 확인
lsof -i :9090

# 2. 설정 파일 검증
prometheus --config.file=/opt/homebrew/etc/prometheus.yml --check-config

# 3. 로그 확인
tail -50 /tmp/prometheus.log

# 4. 데이터 디렉토리 권한 확인
ls -la /opt/homebrew/var/prometheus
```

### Grafana 포트 충돌 (3000번 포트)

**증상**: `bind: address already in use`

**해결**:
```bash
# 1. Grafana 설정 파일 수정
vi /opt/homebrew/etc/grafana/grafana.ini

# 다음 줄 찾아서 수정:
# ;http_port = 3000
http_port = 3001

# 2. Grafana 재시작
pkill -f grafana
grafana server --config /opt/homebrew/etc/grafana/grafana.ini \
  --homepath /opt/homebrew/opt/grafana/share/grafana \
  > /tmp/grafana.log 2>&1 &
```

### ReviewLens 백엔드 메트릭 수집 안됨

**증상**: Prometheus Targets에서 `reviewlens-backend` DOWN

**해결**:
```bash
# 1. 백엔드 서버 실행 확인
curl http://localhost:8000/metrics

# 2. Prometheus 설정 확인 (localhost:8000 올바른지)
cat /opt/homebrew/etc/prometheus.yml | grep -A5 reviewlens

# 3. Prometheus 재시작
pkill -f prometheus
prometheus --config.file=/opt/homebrew/etc/prometheus.yml \
  --storage.tsdb.path=/opt/homebrew/var/prometheus \
  > /tmp/prometheus.log 2>&1 &
```

### 데이터 초기화

```bash
# 모든 데이터 삭제
pkill -f prometheus
rm -rf /opt/homebrew/var/prometheus/*

# 재시작
prometheus --config.file=/opt/homebrew/etc/prometheus.yml \
  --storage.tsdb.path=/opt/homebrew/var/prometheus \
  > /tmp/prometheus.log 2>&1 &
```

## ⚙️ 설정 파일

### Prometheus 설정 (`monitoring/prometheus.yml`)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'reviewlens-monitor'
    environment: 'development'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'reviewlens-backend'
    scrape_interval: 10s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']
        labels:
          service: 'reviewlens-api'
          env: 'dev'
```

### Grafana 설정 (`/opt/homebrew/etc/grafana/grafana.ini`)

주요 설정:
- `http_port = 3001` - HTTP 포트
- `domain = localhost` - 도메인
- `admin_user = admin` - 관리자 계정
- `admin_password = admin` - 관리자 비밀번호

## 📚 추가 문서

- [전체 아키텍처](../docs/MONITORING_ARCHITECTURE.md)
- [메트릭 상세 가이드](../docs/ARCHITECTURE.md#모니터링-계층)
- [백엔드 API 문서](../backend/README.md)

## ✅ 검증 체크리스트

```bash
# ✅ Prometheus 실행
curl http://localhost:9090/-/healthy
# 예상 출력: Prometheus Server is Healthy.

# ✅ Grafana 실행  
curl http://localhost:3001/api/health
# 예상 출력: {"database":"ok","version":"12.3.1"}

# ✅ 백엔드 메트릭 수집
curl http://localhost:8000/metrics | grep http_requests_total
# 예상 출력: http_requests_total{endpoint="/api/chat/config"...

# ✅ Prometheus 타겟 확인
curl -s http://localhost:9090/api/v1/targets | grep reviewlens-backend
# 예상 출력: "job":"reviewlens-backend"...health":"up"
```

모든 체크가 통과하면 모니터링 시스템이 정상 작동 중입니다! 🎉
