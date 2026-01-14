# ReviewLens 모니터링 빠른 시작

## 한 줄 명령으로 시작

```bash
# 모니터링 스택 시작 (자동 설치)
./scripts/start_monitoring.sh

# 모니터링 스택 종료
./scripts/stop_monitoring.sh
```

## 접속

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **Metrics**: http://localhost:8000/metrics

## 처음 실행 시

1. Prometheus/Grafana 바이너리 자동 다운로드 (1-2분)
2. 이후엔 즉시 시작 (5초 이내)

## 대시보드

Grafana → Dashboards → "ReviewLens Performance Dashboard"

**12개 패널**:
- HTTP 요청 속도/Latency
- 에러율
- 대화 세션/턴
- Retrieval/Scoring Latency
- Evidence Count
- LLM API 성능

## 로그 확인

```bash
# Prometheus 로그
tail -f monitoring/data/prometheus/prometheus.log

# Grafana 로그
tail -f monitoring/data/grafana/grafana.log
```

## 문제 해결

### Prometheus가 시작되지 않음
```bash
# 포트 충돌 확인
lsof -i :9090

# 프로세스 확인
ps aux | grep prometheus

# 재시작
./scripts/stop_monitoring.sh
./scripts/start_monitoring.sh
```

### Grafana가 시작되지 않음
```bash
# 포트 충돌 확인
lsof -i :3001

# 프로세스 확인
ps aux | grep grafana

# 재시작
./scripts/stop_monitoring.sh
./scripts/start_monitoring.sh
```

### 데이터 초기화
```bash
# 모든 데이터 삭제 후 재시작
./scripts/stop_monitoring.sh
rm -rf monitoring/data/*
./scripts/start_monitoring.sh
```

자세한 내용은 [MONITORING_ARCHITECTURE.md](../docs/MONITORING_ARCHITECTURE.md) 참조
