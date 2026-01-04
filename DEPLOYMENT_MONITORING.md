# ReviewLens 모니터링 배포 가이드

## 환경별 배포 전략

### 개발 환경 (로컬)
✅ **로컬 바이너리 방식** - 간단하고 빠름

```bash
./scripts/start_monitoring.sh
```

### 프로덕션 환경
✅ **Docker Compose 방식** (추천) - 안정적이고 이식성 높음

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

---

## 배포 시나리오별 가이드

### 1️⃣ AWS EC2 / GCP VM (일반 서버)

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

---

### 2️⃣ AWS ECS / GCP Cloud Run (컨테이너 플랫폼)

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

---

### 3️⃣ Kubernetes (EKS, GKE, AKS)

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

---

### 4️⃣ 클라우드 관리형 서비스 (가장 간단)

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

---

## 환경 변수 기반 설정

현재 코드를 환경에 따라 자동 선택하도록 개선:

```bash
# .env에 추가
MONITORING_MODE=local  # local | docker | cloud
```

```python
# backend/core/settings.py
MONITORING_MODE = os.getenv("MONITORING_MODE", "local")

if MONITORING_MODE == "cloud":
    # CloudWatch/Grafana Cloud 사용
    USE_PROMETHEUS_CLIENT = False
elif MONITORING_MODE == "docker":
    # Docker Compose Prometheus 사용
    USE_PROMETHEUS_CLIENT = True
else:
    # 로컬 바이너리 Prometheus 사용
    USE_PROMETHEUS_CLIENT = True
```

---

## 프로덕션 체크리스트

### 필수 설정

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

### 성능 튜닝

- [ ] Prometheus retention 기간 조정 (기본 15일)
- [ ] Scrape interval 조정 (트래픽에 따라)
- [ ] Grafana query timeout 설정

---

## 추천 배포 전략

| 환경 | 추천 방식 | 이유 |
|------|----------|------|
| **로컬 개발** | 로컬 바이너리 | 간단, 빠름 |
| **스테이징** | Docker Compose | 프로덕션과 동일 환경 |
| **프로덕션 (소규모)** | Docker Compose | 관리 간편, 비용 낮음 |
| **프로덕션 (중규모)** | Kubernetes | 스케일링, HA |
| **프로덕션 (대규모)** | 클라우드 관리형 | 운영 부담 최소화 |

---

## 마이그레이션 가이드

### 로컬 바이너리 → Docker Compose

```bash
# 1. 로컬 모니터링 중지
./scripts/stop_monitoring.sh

# 2. Docker Compose로 시작
docker-compose -f docker-compose.monitoring.yml up -d

# 3. 데이터 마이그레이션 (필요시)
docker cp monitoring/data/prometheus/. reviewlens_prometheus:/prometheus/
```

### Docker Compose → Kubernetes

```bash
# 1. Helm으로 Prometheus 설치
helm install prometheus prometheus-community/kube-prometheus-stack

# 2. 대시보드 ConfigMap 생성
kubectl create configmap reviewlens-dashboard \
  --from-file=monitoring/grafana/dashboards/reviewlens_dashboard.json

# 3. ServiceMonitor 배포
kubectl apply -f deploy/k8s/
```

---

## 비용 비교

| 방식 | 월 비용 (예상) | 관리 난이도 |
|------|---------------|------------|
| 로컬 바이너리 | $0 | 낮음 |
| Docker Compose | $0 (서버 비용만) | 중간 |
| Kubernetes | $50-200 (클러스터) | 높음 |
| Grafana Cloud | $0-50 (트래픽) | 낮음 |
| AWS CloudWatch | $10-100 (메트릭 수) | 중간 |

---

## FAQ

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
