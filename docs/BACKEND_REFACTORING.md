# Backend 폴더 구조 리팩토링 가이드

**날짜**: 2026년 1월 17일  
**목적**: Clean Architecture 기반의 계층화된 구조로 전환

---

## 📁 새로운 폴더 구조

```
backend/app/
  main.py                    # FastAPI 앱 팩토리
  
  core/                      # 핵심 설정
    settings.py              # 환경 변수, 설정
    logging.py               # 로깅 설정
  
  api/                       # HTTP 인터페이스
    routers/
      chat.py                # 채팅 엔드포인트
      ingest.py              # CSV/URL 업로드/수집
      health.py              # 헬스체크, 메트릭
    schemas/
      requests.py            # 요청 스키마
      responses.py           # 응답 스키마
  
  domain/                    # 비즈니스 로직 (Pure Python)
    dialogue/
      session.py             # DialogueSession (수렴 로직 포함)
      types.py               # 타입 정의
    reg/
      store.py               # reg_factor/reg_question 로드/파싱
      matching.py            # 질문->factor 매칭
    review/
      scoring.py             # factor scoring
      retrieval.py           # evidence 추출 + label/quote
      normalize.py           # 리뷰 데이터 정규화
  
  services/                  # 유스케이스 조율
    chat_service.py          # "세션/대화" 유스케이스
    review_service.py        # "리뷰 수집/분석" 유스케이스
    prompt_service.py        # LLM context/prompt 생성
    llm_service.py           # LLM 클라이언트 추상화
  
  infra/                     # 외부 의존성
    persistence/
      session_repo.py        # SessionStore 추상화
      db.py                  # DB 연결 (미래 확장)
    collectors/
      smartstore.py          # 스마트스토어 크롤러
    cache/
      review_cache.py        # 리뷰 캐시 관리
    observability/
      metrics.py             # Prometheus 메트릭
      tracing.py             # 분산 트레이싱
```

---

## 🎯 설계 원칙

### 1. 계층 분리 (Layered Architecture)

**외부 → 내부 의존성 방향**

```
API Layer (routers/)
    ↓
Service Layer (services/)
    ↓
Domain Layer (domain/)
    ↑
Infrastructure Layer (infra/)
```

### 2. 의존성 규칙

- ✅ **Domain은 순수 Python** - FastAPI, DB, 외부 라이브러리 의존 없음
- ✅ **Service가 조율** - Domain + Infra를 조합하여 유스케이스 구현
- ✅ **API는 얇게** - HTTP 요청/응답 변환만, 비즈니스 로직은 Service에 위임
- ✅ **Infra는 교체 가능** - 인터페이스(추상 클래스)를 통해 구현체 교체

### 3. 단일 책임 원칙 (SRP)

| 계층 | 책임 |
|------|------|
| **API** | HTTP 프로토콜, 요청 검증, 응답 포맷팅 |
| **Service** | 유스케이스 흐름 제어, 트랜잭션 관리 |
| **Domain** | 비즈니스 규칙, 도메인 로직 |
| **Infra** | DB, 외부 API, 파일 I/O, 캐싱 |

---

## 📦 주요 컴포넌트 설명

### Domain Layer

**`domain/dialogue/session.py`**
- DialogueSession 클래스
- 대화 턴 관리, 수렴 로직
- Factor selection 판단

**`domain/reg/store.py`**
- Factor/Question 데이터 로드
- CSV 파싱 및 검증

**`domain/reg/matching.py`**
- 질문 텍스트 → Factor 매칭 알고리즘
- 유사도 계산

**`domain/review/scoring.py`**
- Factor별 점수 계산
- Evidence 가중치 적용

**`domain/review/retrieval.py`**
- 리뷰에서 Evidence 추출
- Label/Quote 생성

**`domain/review/normalize.py`**
- 벤더별 리뷰 형식 통일
- 데이터 정제

### Service Layer

**`services/chat_service.py`**
```python
class ChatService:
    def __init__(self, session_repo, dialogue_session, prompt_service):
        ...
    
    async def create_session(self, category, product_name, vendor) -> str:
        """새 대화 세션 생성"""
        
    async def process_turn(self, session_id, user_message) -> Dict:
        """대화 턴 처리"""
        
    async def get_session(self, session_id) -> Dict:
        """세션 조회"""
```

**`services/review_service.py`**
```python
class ReviewService:
    def __init__(self, collectors, review_cache):
        ...
    
    async def collect_reviews(self, vendor, product_url) -> List:
        """리뷰 수집"""
        
    async def analyze_reviews(self, reviews, factors) -> Dict:
        """리뷰 분석"""
```

**`services/prompt_service.py`**
- LLM 프롬프트 생성
- Context 조합

### Infrastructure Layer

**`infra/persistence/session_repo.py`**
- 세션 CRUD
- 파일 기반 저장 (현재)
- 미래: DB 연동 가능

**`infra/collectors/smartstore.py`**
- 스마트스토어 크롤링
- 리뷰 데이터 수집

**`infra/cache/review_cache.py`**
- 리뷰 캐싱 (파일 기반)
- 중복 수집 방지

**`infra/observability/metrics.py`**
- Prometheus 메트릭 정의
- Counter, Histogram, Gauge

**`infra/observability/tracing.py`**
- 분산 트레이싱 (미래 확장)
- 함수 실행 추적 데코레이터

### API Layer

**`api/routers/chat.py`**
- POST /api/chat/sessions - 세션 생성
- POST /api/chat/sessions/{id}/turns - 대화 턴
- GET /api/chat/sessions/{id} - 세션 조회

**`api/routers/ingest.py`**
- POST /api/ingest/csv - CSV 업로드
- POST /api/ingest/url - URL 수집

**`api/routers/health.py`**
- GET /health - 헬스체크
- GET /metrics - Prometheus 메트릭

---

## � 현재 상태 (2026-01-17)

### ✅ 완료된 작업

1. **새 폴더 구조 생성** - Clean Architecture 기반
   - `domain/`, `services/`, `infra/` 계층 분리
   - 각 계층별 `__init__.py` 및 기본 파일 생성

2. **기존 파일 복사**
   - dialogue → domain/dialogue/session.py
   - reg_store → domain/reg/store.py
   - retrieval → domain/review/retrieval.py
   - collector → infra/collectors/smartstore.py
   - session_persistence → infra/persistence/session_repo.py

3. **새 모듈 작성**
   - services/chat_service.py, review_service.py, prompt_service.py
   - infra/cache/review_cache.py
   - infra/observability/tracing.py
   - domain/dialogue/types.py, domain/reg/matching.py, domain/review/normalize.py

4. **환경 설정**
   - Python 3.11 사용 확인
   - 패키지 의존성 정리 (langchain 제거)
   - numpy/pandas 재설치

### 🔧 진행 중인 작업

- **기존 API 유지** - routes_chat.py, routes_metrics.py를 그대로 사용
- **점진적 마이그레이션** - 새 구조와 기존 구조 병행

### ⚠️ 알려진 이슈

1. **의존성 충돌** (해결됨)
   - ~~langchain이 pydantic 2와 호환되지 않음~~ → langchain 제거
   - ~~numpy 버전 충돌~~ → numpy 2.4.1로 재설치
   - scipy 경고 (사용하지 않으므로 무시 가능)

2. **Python 버전 혼재**
   - macOS 기본: Python 3.9.6
   - Homebrew: Python 3.11.12 ✅ 사용 중
   - **권장**: 명시적으로 `python3.11` 또는 `/opt/homebrew/bin/python3.11` 사용

---

## 📋 마이그레이션 체크리스트

### 완료된 작업 ✅

- [x] 새 폴더 구조 생성
- [x] 파일 복사 (기존 파일 유지)
- [x] `main.py` import 경로 수정
- [x] 기본 __init__.py 파일 생성
- [x] Service 레이어 기본 구조 생성
- [x] Infra 레이어 기본 구조 생성

### 진행 중인 작업 🚧

- [ ] 기존 routes_chat.py → api/routers/chat.py 리팩토링
- [ ] routes_chat_helpers.py 로직 Service로 이동
- [ ] SessionStore → session_repo.py 통합
- [ ] dialogue.py → session.py 리팩토링

### 향후 작업 📋

- [ ] 모든 import 경로 업데이트
- [ ] 유닛 테스트 추가
- [ ] API 통합 테스트
- [ ] 성능 테스트
- [ ] 문서화 (docstring, type hints)

---

## 🧪 테스트 방법

### 0. Python 환경 확인

```bash
# Python 3.11 사용 확인
which python3.11
# /opt/homebrew/bin/python3.11

# 또는 Python 3 버전 확인
python3 --version
# Python 3.11.x 이상 권장
```

### 1. 패키지 설치

```bash
cd /Users/ssnko/app/python/reviewlens

# Python 3.11 사용
/opt/homebrew/bin/python3.11 -m pip install -r backend/requirements.txt

# 또는
pip3.11 install -r backend/requirements.txt
```

**의존성 충돌 해결:**
```bash
# langchain 제거 (사용하지 않음)
pip3.11 uninstall -y langchain langchainplus-sdk

# numpy/pandas 재설치
pip3.11 install --upgrade --force-reinstall numpy pandas numexpr
```

### 2. Import 경로 확인

```bash
cd /Users/ssnko/app/python/reviewlens

# Python 3.11로 테스트
/opt/homebrew/bin/python3.11 -c "
from backend.app.core.settings import settings
from backend.app.core.logging import setup_logging
from backend.core.metrics import http_requests_total
from backend.app.services.chat_service import ChatService
from backend.app.domain.dialogue.types import SessionMetadata
print('✅ All imports successful')
print(f'Settings API Title: {settings.API_TITLE}')
"
```

### 3. 서버 시작

```bash
cd /Users/ssnko/app/python/reviewlens

# 프로젝트 루트에서 실행 (중요!)
/opt/homebrew/bin/python3.11 -m backend.app.main

# 또는 uvicorn 직접 사용
/opt/homebrew/bin/python3.11 -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 엔드포인트 테스트

```bash
# 헬스체크
curl http://localhost:8000/health

# 메트릭
curl http://localhost:8000/metrics
```

---

## 📚 다음 단계

1. **routes_chat.py 리팩토링**
   - ChatService 사용하도록 변경
   - 비즈니스 로직 Service로 이동

2. **SessionStore 추상화**
   - session_repo.py에 인터페이스 정의
   - 파일 기반 구현체 작성

3. **테스트 작성**
   - Domain 로직 유닛 테스트
   - Service 통합 테스트
   - API E2E 테스트

4. **문서화**
   - API 문서 (OpenAPI)
   - 아키텍처 다이어그램
   - 개발자 가이드

---

## 🎓 참고 자료

- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [Python Layered Architecture](https://www.cosmicpython.com/)
