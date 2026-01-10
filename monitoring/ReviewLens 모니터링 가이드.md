# ReviewLens 모니터링 가이드

이 가이드는 GitHub에서 프로젝트를 받은 후 Prometheus와 Grafana를 통해 ReviewLens 시스템을 모니터링하는 방법을 설명합니다.


---

## 사전 요구사항

### 필수 설치 항목

1. **Docker Desktop** (또는 Docker + Docker Compose)
   - Windows: [Docker Desktop 다운로드](https://www.docker.com/products/docker-desktop)
   - Linux/Mac: Docker와 Docker Compose 설치
   - 설치 확인:
     ```bash
     docker --version
     docker-compose --version
     ```


2. **Backend 서버 실행 중** (아직 구현안함 20260110)
   - Backend가 `http://localhost:8000`에서 실행 중이어야 합니다
   - `/metrics` 엔드포인트가 활성화되어 있어야 합니다
   - 확인 방법:
     ```bash
     curl http://localhost:8000/metrics
     ```

---

### 1단계: 모니터링 서비스 시작

```bash
# 프로젝트 루트 디렉토리에서 실행
docker-compose up -d
```

이 명령은 다음 서비스들을 시작합니다:
- **Prometheus** (포트 9090) - 메트릭 수집 및 저장
- **Grafana** (포트 3001) - 대시보드 시각화

### 2단계: 서비스 상태 확인

```bash
# 모든 서비스가 실행 중인지 확인
docker-compose ps

**예상 출력**:
```
NAME                STATUS              PORTS
grafana             Up 2 minutes        0.0.0.0:3001->3000/tcp
prometheus          Up 2 minutes        0.0.0.0:9090->9090/tcp
```

```

### 3단계: 브라우저에서 접속

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001
  - 사용자명: `admin`
  - 비밀번호: `admin` (첫 로그인 후 변경 권장)

---

**대시보드가 보이지 않으면**:
- `monitoring/grafana/dashboards/` 폴더에 JSON 파일이 있는지 확인
- Grafana 로그에서 에러 메시지 확인: `docker-compose logs grafana`

---




## 서비스 관리 명령어

### 서비스 시작/중지

```bash
# 모든 서비스 시작
docker-compose up -d

# 모든 서비스 중지
docker-compose down

# 중지 + 데이터 삭제 (주의: 모든 메트릭 데이터 삭제됨)
docker-compose down -v
```

### 특정 서비스 재시작

```bash
# Prometheus만 재시작
docker-compose restart prometheus

# Grafana만 재시작
docker-compose restart grafana
```

### 로그 확인

```bash
# 모든 서비스 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f prometheus
docker-compose logs -f grafana
```

### 서비스 상태 확인

```bash
# 실행 중인 서비스 목록
docker-compose ps

# 서비스 상태 상세 확인
docker-compose ps -a
```

---

## 다음 단계

모니터링이 정상적으로 작동하는지 확인한 후:

1. **대시보드 커스터마이징**
   - Grafana에서 대시보드 편집하여 필요한 메트릭 추가

2. **알림 설정** (선택사항)
   - Grafana Alerting을 사용하여 임계값 초과 시 알림 설정

3. **메트릭 추가**
   - Backend 코드에 새로운 메트릭 추가하여 더 상세한 모니터링


---

## 참고 자료

- [Prometheus 공식 문서](https://prometheus.io/docs/)
- [Grafana 공식 문서](https://grafana.com/docs/)
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)

---
