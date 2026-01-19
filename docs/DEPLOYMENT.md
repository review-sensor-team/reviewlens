# GitHub Actions 자동 배포 가이드

## 개요

ReviewLens는 GitHub Actions를 사용하여 main 브랜치에 푸시할 때 **Frontend와 Backend를 개별적으로** 자동 배포합니다.

## 배포 워크플로우

### 1. 스마트 배포 파이프라인

```
Push to main
  ↓
변경 파일 감지 (Backend / Frontend)
  ↓
┌─────────────────┬─────────────────┐
│ Backend 변경시  │ Frontend 변경시 │
├─────────────────┼─────────────────┤
│ Backend 테스트  │ Frontend 테스트 │
│       ↓         │       ↓         │
│ Backend 배포    │ Frontend 배포   │
└─────────────────┴─────────────────┘
  ↓
Health Check
  ↓
Complete
```

### 2. 개별 배포 동작

- **Backend만 변경**: Backend만 테스트 및 배포
- **Frontend만 변경**: Frontend만 테스트 및 배포
- **둘 다 변경**: 병렬로 각각 테스트 및 배포
- **수동 트리거**: 원하는 대상(all/backend/frontend) 선택 가능

### 3. 워크플로우 파일

- `.github/workflows/ci.yml` - CI (테스트 자동화)
- `.github/workflows/deploy.yml` - CD (개별 배포 자동화)

## GitHub Secrets 설정

배포를 위해 다음 Secrets를 GitHub 저장소에 설정해야 합니다:

### 필수 Secrets

1. **DEPLOY_SSH_KEY**
   - 서버 접속용 SSH private key
   - 생성 방법:
     ```bash
     ssh-keygen -t ed25519 -C "github-actions@reviewlens" -f ~/.ssh/reviewlens_deploy
     # Public key를 서버의 ~/.ssh/authorized_keys에 추가
     cat ~/.ssh/reviewlens_deploy.pub
     # Private key를 GitHub Secret에 추가
     cat ~/.ssh/reviewlens_deploy
     ```

2. **DEPLOY_USER**
   - 서버 SSH 사용자명
   - 예: `ubuntu`, `deploy`, `app`

3. **DEPLOY_HOST**
   - 서버 IP 주소 또는 도메인
   - 예: `123.456.789.0` 또는 `reviewlens.example.com`

4. **DEPLOY_PATH**
   - 서버의 프로젝트 디렉토리 절대 경로
   - 예: `/home/ubuntu/reviewlens`

### Docker Hub 배포용 Secrets (선택사항)

5. **DOCKER_USERNAME**
   - Docker Hub 사용자명

6. **DOCKER_PASSWORD**
   - Docker Hub 액세스 토큰 또는 패스워드

### GitHub Secrets 등록 방법

1. GitHub 저장소 페이지 이동
2. `Settings` → `Secrets and variables` → `Actions`
3. `New repository secret` 클릭
4. Name과 Value 입력 후 `Add secret`

## 배포 방법

### 자동 배포 (기본)

```bash
# Backend만 수정한 경우
git add backend/
git commit -m "feat: update backend logic"
git push origin main
# → Backend만 자동 배포

# Frontend만 수정한 경우
git add frontend/
git commit -m "feat: update UI"
git push origin main
# → Frontend만 자동 배포

# 둘 다 수정한 경우
git add backend/ frontend/
git commit -m "feat: update both backend and frontend"
git push origin main
# → Backend와 Frontend 병렬 배포
```

### 수동 배포

1. GitHub 저장소의 `Actions` 탭 이동
2. `CD - Deploy to Production` 워크플로우 선택
3. `Run workflow` 버튼 클릭
4. 배포 대상 선택:
   - `all` - Backend와 Frontend 모두 배포
   - `backend` - Backend만 배포
   - `frontend` - Frontend만 배포
5. `Run workflow` 클릭

## 배포 모드

### 1. 일반 배포 (기본) - 개별 배포 지원

SSH로 서버 접속하여 변경된 부분만 업데이트 및 재시작

**장점:**
- 빠른 배포
- 변경되지 않은 서비스는 중단 없음
- 서버 리소스 효율적 사용

**동작:**
- Backend 변경: Backend만 재시작
- Frontend 변경: Frontend만 재빌드 및 재시작
- 둘 다 변경: 각각 독립적으로 재시작

**단점:**
- 서버 환경 의존적

### 2. Docker 배포 - 개별 컨테이너 배포

Docker 이미지 빌드 후 변경된 컨테이너만 재배포

**활성화 방법:**
```yaml
# .github/workflows/deploy.yml
deploy-backend-docker:
  if: github.ref == 'refs/heads/main' && false  # false 제거

deploy-frontend-docker:
  if: github.ref == 'refs/heads/main' && false  # false 제거
```

**장점:**
- 환경 일관성
- 롤백 용이
- 확장성
- 개별 컨테이너 독립 배포

**단점:**
- 느린 초기 빌드

## 서버 사전 준비

### 1. SSH 키 설정

```bash
# 서버에서 실행
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# GitHub Actions에서 생성한 public key 추가
echo "ssh-ed25519 AAAA..." >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 2. 프로젝트 클론

```bash
cd /home/ubuntu  # DEPLOY_PATH의 상위 디렉토리
git clone https://github.com/your-username/reviewlens.git
cd reviewlens
```

### 3. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env
# 필요한 설정 수정
nano .env
```

### 4. 초기 의존성 설치

```bash
# Python 의존성
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Node.js 의존성
cd frontend
npm install
npm run build
cd ..
```

### 5. 서비스 권한 확인

```bash
# 스크립트 실행 권한
chmod +x local_restart.sh local_stop.sh
chmod +x db_start.sh db_stop.sh
chmod +x scripts/*.sh
```

## Docker 배포 (선택)

### 서버 Docker 설치

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Docker 배포 실행

```bash
# 기본 배포 (Backend + Frontend)
docker-compose -f docker-compose.prod.yml up -d

# DB 모드 포함
docker-compose -f docker-compose.prod.yml --profile database up -d

# 모니터링 포함
docker-compose -f docker-compose.prod.yml --profile monitoring up -d

# 모두 포함
docker-compose -f docker-compose.prod.yml --profile database --profile monitoring up -d
```

## 배포 확인

### 헬스체크

```bash
# 백엔드 확인
curl http://your-server:8000/metrics

# 프론트엔드 확인
curl http://your-server/

# Docker 상태 확인 (Docker 배포 시)
docker-compose -f docker-compose.prod.yml ps
```

### 로그 확인

```bash
# 일반 배포
tail -f logs/backend.log
tail -f logs/frontend.log

# Docker 배포
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
```

## 롤백

### Git 기반 롤백

```bash
# 서버에서 실행
cd /home/ubuntu/reviewlens
git log --oneline -5  # 커밋 확인
git reset --hard <previous-commit-hash>
./local_restart.sh
```

### Docker 기반 롤백

```bash
# 이전 이미지로 롤백
docker-compose -f docker-compose.prod.yml down
docker pull your-username/reviewlens-backend:<previous-tag>
docker-compose -f docker-compose.prod.yml up -d
```

## 트러블슈팅

### 배포 실패 시

1. **GitHub Actions 로그 확인**
   - Actions 탭에서 실패한 워크플로우 클릭
   - 각 step의 로그 확인

2. **SSH 연결 실패**
   ```bash
   # 로컬에서 SSH 연결 테스트
   ssh -i ~/.ssh/reviewlens_deploy user@host
   ```

3. **서버 로그 확인**
   ```bash
   # 서버에서 실행
   tail -f logs/backend.log
   systemctl status reviewlens  # systemd 사용 시
   ```

4. **포트 충돌**
   ```bash
   # 포트 사용 확인
   sudo lsof -i :8000
   sudo lsof -i :5173
   ```

## 모니터링

### Prometheus 메트릭

```
http://your-server:9090
```

### Grafana 대시보드

```
http://your-server:3001
기본 계정: admin / admin
```

## 보안 권장사항

1. **SSH 키 관리**
   - Private key는 절대 공개하지 마세요
   - GitHub Secrets에만 저장
   - 정기적으로 키 교체

2. **방화벽 설정**
   ```bash
   # UFW 예시
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 80/tcp   # HTTP
   sudo ufw allow 443/tcp  # HTTPS
   sudo ufw enable
   ```

3. **.env 파일 보안**
   - 서버에만 보관
   - Git에 커밋하지 않기
   - 민감한 정보는 환경변수로 관리

4. **HTTPS 설정**
   ```bash
   # Let's Encrypt 사용
   sudo apt install certbot
   sudo certbot --nginx -d reviewlens.example.com
   ```

## 참고

- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Nginx 설정](https://nginx.org/en/docs/)
