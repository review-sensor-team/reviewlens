# Render.com 배포 가이드

## Render.com이란?

Render는 GitHub과 연동하여 자동으로 애플리케이션을 배포하는 PaaS(Platform as a Service)입니다.
- **자동 배포**: Git 푸시만으로 배포
- **무료 플랜**: 제한적이지만 테스트/개발용으로 충분
- **관리 편의성**: 서버 관리 불필요

## 배포 방식 비교

### GitHub Actions (현재 설정)
- 직접 서버 SSH 접근
- 수동 서버 관리 필요
- 완전한 제어권
- 비용: 서버 비용만

### Render.com
- Git 연동 자동 배포
- 서버 관리 불필요
- 간편한 설정
- 비용: 무료 플랜 제공

## Render.com 배포 설정

### 1. Render 계정 생성

1. [Render.com](https://render.com) 접속
2. GitHub 계정으로 가입
3. ReviewLens 저장소 접근 권한 부여

### 2. Blueprint 배포 (자동 설정)

render.yaml 파일이 이미 준비되어 있으므로:

1. Render 대시보드에서 `New` → `Blueprint` 선택
2. GitHub 저장소 `reviewlens` 선택
3. `render.yaml` 파일 자동 인식
4. 환경 변수 설정:
   - `VITE_API_URL`: Backend 서비스 URL (배포 후 자동 생성)
   - `ALLOWED_ORIGINS`: Frontend URL
   - `OPENAI_API_KEY`: OpenAI API 키 (선택)
   - `ANTHROPIC_API_KEY`: Claude API 키 (선택)
   - `GOOGLE_API_KEY`: Gemini API 키 (선택)
5. `Apply` 클릭

### 3. 개별 서비스 수동 생성

Blueprint를 사용하지 않고 개별로 생성하려면:

#### Backend 서비스

1. `New` → `Web Service` 선택
2. 저장소 연결: `reviewlens` 선택
3. 설정:
   - **Name**: `reviewlens-backend`
   - **Region**: Singapore (또는 가까운 지역)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: Free

4. 환경 변수 추가:
   ```
   PYTHON_VERSION=3.9.18
   DATA_SOURCE_MODE=file
   DATA_DIR=/opt/render/project/src/backend/data
   PYTHONPATH=/opt/render/project/src/backend
   ```

5. Advanced 설정:
   - **Health Check Path**: `/metrics`
   - **Auto-Deploy**: Yes

#### Frontend 서비스

1. `New` → `Static Site` 선택
2. 저장소 연결: `reviewlens` 선택
3. 설정:
   - **Name**: `reviewlens-frontend`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**:
     ```bash
     npm ci && npm run build
     ```
   - **Publish Directory**: `dist`

4. 환경 변수:
   ```
   NODE_VERSION=18
   VITE_API_URL=https://reviewlens-backend.onrender.com
   ```

5. Rewrite Rules 추가 (SPA 라우팅):
   - Source: `/*`
   - Destination: `/index.html`
   - Action: `Rewrite`

### 4. 데이터베이스 (선택사항)

PostgreSQL이 필요한 경우:

1. `New` → `PostgreSQL` 선택
2. 설정:
   - **Name**: `reviewlens-postgres`
   - **Database**: `reviewlens`
   - **User**: `reviewlens`
   - **Region**: Singapore
   - **Plan**: Free

3. 생성 후 연결 정보를 Backend 환경 변수에 추가:
   ```
   DATA_SOURCE_MODE=database
   DB_HOST=<자동생성>
   DB_PORT=5432
   DB_NAME=reviewlens
   DB_USER=reviewlens
   DB_PASSWORD=<자동생성>
   ```

## 자동 배포 동작

### Backend 자동 배포

`backend/` 디렉토리 변경 감지 시:
```bash
git add backend/
git commit -m "feat: update backend"
git push origin main
# → Render가 자동으로 Backend만 재배포
```

### Frontend 자동 배포

`frontend/` 디렉토리 변경 감지 시:
```bash
git add frontend/
git commit -m "feat: update UI"
git push origin main
# → Render가 자동으로 Frontend만 재빌드 및 배포
```

### 주의사항

**Render는 기본적으로 전체 저장소 변경을 감지합니다.**
- `backend/` 변경 → Backend만 재배포 ❌ (전체 감지)
- `frontend/` 변경 → Frontend만 재배포 ❌ (전체 감지)

**해결 방법**: render.yaml에 `rootDirectory` 설정으로 각 서비스가 자신의 디렉토리만 감시하도록 설정됨

## 배포 URL

배포 후 자동 생성되는 URL:

- **Backend**: `https://reviewlens-backend.onrender.com`
- **Frontend**: `https://reviewlens-frontend.onrender.com`

Frontend의 API 호출을 Backend URL로 업데이트:

```javascript
// frontend/src/config.js
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://reviewlens-backend.onrender.com'
```

## 모니터링

### Render 대시보드

1. 로그 실시간 확인
2. 메트릭 모니터링 (CPU, 메모리, 네트워크)
3. 배포 히스토리
4. 환경 변수 관리

### 커스텀 도메인 (유료 플랜)

1. Render 대시보드에서 서비스 선택
2. `Settings` → `Custom Domain`
3. 도메인 추가 및 DNS 설정

## 무료 플랜 제한사항

- **Backend (Web Service)**:
  - 15분 비활성 시 자동 중지
  - 첫 요청 시 콜드 스타트 (30초~1분)
  - 750시간/월 무료 (31일 = 744시간)
  - 512MB RAM

- **Frontend (Static Site)**:
  - 무제한 트래픽
  - CDN 자동 적용
  - 완전 무료

- **PostgreSQL**:
  - 90일 후 자동 삭제 (무료 플랜)
  - 1GB 스토리지

## 유료 플랜 업그레이드

프로덕션 사용 시 권장:

- **Starter ($7/월)**:
  - 항상 실행 (콜드 스타트 없음)
  - 512MB RAM

- **Standard ($25/월)**:
  - 2GB RAM
  - 자동 스케일링
  - 우선 지원

## GitHub Actions vs Render

### 함께 사용하기

두 가지 배포 방식을 병행할 수 있습니다:

1. **개발/스테이징**: Render.com 자동 배포
2. **프로덕션**: GitHub Actions로 직접 서버 배포

`.github/workflows/deploy.yml` 수정:
```yaml
on:
  push:
    branches:
      - production  # main 대신 production 브랜치
```

## 롤백

### Render에서 이전 버전으로 롤백

1. 서비스 선택
2. `Deploys` 탭
3. 이전 배포 선택
4. `Redeploy` 클릭

## 트러블슈팅

### 배포 실패

1. **로그 확인**: Render 대시보드 → Logs
2. **빌드 명령 확인**: render.yaml 또는 서비스 설정
3. **환경 변수 확인**: 필수 변수 누락 여부

### 콜드 스타트 느림 (무료 플랜)

- 해결: Starter 플랜 업그레이드 ($7/월)
- 임시 해결: Cron job으로 15분마다 핑

### CORS 에러

Backend 환경 변수 업데이트:
```
ALLOWED_ORIGINS=https://reviewlens-frontend.onrender.com
```

## 비용 예측

### 무료로 운영 가능한 구성

- Frontend (Static Site): 완전 무료
- Backend (Web Service): 무료 (콜드 스타트 있음)
- **총 비용**: $0/월

### 프로덕션 구성

- Frontend: 완전 무료
- Backend (Starter): $7/월
- PostgreSQL (Starter): $7/월
- **총 비용**: $14/월

## 참고 자료

- [Render 공식 문서](https://render.com/docs)
- [render.yaml 스펙](https://render.com/docs/yaml-spec)
- [Python 배포 가이드](https://render.com/docs/deploy-fastapi)
- [Static Site 가이드](https://render.com/docs/static-sites)
