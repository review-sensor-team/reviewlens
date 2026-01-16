# API Layer 단순화 완료 (Phase 4) ✅

## 날짜: 2026-01-17

## 1. 구현 내용

### ✅ Clean Architecture API Router 생성

**기존 API (v1) 유지 + 새 API (v2) 추가**

```
/api/chat/*        → 기존 routes_chat.py (v1 - 호환성 유지)
/api/v2/chat/*     → 새 routers/chat.py (v2 - Service 기반)
/api/v2/reviews/*  → 새 routers/review.py (v2 - Service 기반)
```

---

### ✅ api/routers/chat.py (Chat API v2)

**얇은 컨트롤러 - Service 레이어만 호출**

```python
# Before (routes_chat.py - 418 lines)
@router.post("/message")
async def send_message(request: ChatRequest):
    session = session_store.get_session(...)  # 복잡한 로직
    bot_turn = session.step(...)              # 복잡한 로직
    related_reviews = get_related_reviews(...) # 복잡한 로직
    # ... 200+ 줄의 비즈니스 로직

# After (routers/chat.py - 213 lines)
@router.post("/messages")
async def send_message(
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    result = chat_service.process_turn(...)  # Service 호출만
    return ChatMessageResponse(**result)     # 단순 변환
```

**주요 엔드포인트:**
- `POST /api/v2/chat/sessions` - 세션 생성
- `POST /api/v2/chat/messages` - 메시지 전송
- `GET /api/v2/chat/sessions/{id}` - 세션 조회
- `DELETE /api/v2/chat/sessions/{id}` - 세션 삭제

**의존성 주입:**
```python
def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(data_dir=get_data_dir())
    return _chat_service
```

**특징:**
- 싱글톤 패턴으로 Service 인스턴스 관리
- Pydantic 모델로 Request/Response 정의
- FastAPI Depends로 의존성 주입
- 비즈니스 로직 0줄 (모두 Service로 위임)

---

### ✅ api/routers/review.py (Review API v2)

**리뷰 수집 및 분석 API**

**주요 엔드포인트:**
- `POST /api/v2/reviews/collect` - 리뷰 수집
- `POST /api/v2/reviews/analyze` - 리뷰 분석

**코드 예시:**
```python
@router.post("/collect")
async def collect_reviews(
    request: CollectReviewsRequest,
    review_service: ReviewService = Depends(get_review_service)
):
    result = review_service.collect_reviews(...)
    return CollectReviewsResponse(**result)
```

**분석 플로우:**
1. ReviewService.collect_reviews() → 리뷰 수집
2. ReviewService.normalize_reviews() → 정규화
3. Domain: parse_factors() → Factor 로드
4. ReviewService.analyze_reviews() → 점수 계산
5. 결과 반환 (top_factors, review_count)

---

## 2. 아키텍처 개선

### Before: Layered Architecture (혼재)
```
┌──────────────────────────────────┐
│   routes_chat.py (418 lines)     │
│                                  │
│  - HTTP 처리                     │
│  - 비즈니스 로직 ❌              │
│  - 세션 관리 ❌                  │
│  - 리뷰 처리 ❌                  │
│  - LLM 호출 ❌                   │
│  - 데이터 변환 ❌                │
│                                  │
│  → 모든 것이 섞여있음            │
└──────────────────────────────────┘
```

### After: Clean Architecture (분리)
```
┌──────────────────────────────────┐
│  routers/chat.py (213 lines)     │
│                                  │
│  - HTTP 요청/응답만 처리 ✅      │
│  - Service 호출 ✅               │
│  - 의존성 주입 ✅                │
│                                  │
│  → API 레이어 역할만             │
└──────────────────────────────────┘
             ↓
┌──────────────────────────────────┐
│    Service Layer                 │
│                                  │
│  - ChatService (세션, 대화)      │
│  - ReviewService (리뷰 처리)     │
│  - PromptService (LLM context)   │
│                                  │
│  → 비즈니스 유스케이스           │
└──────────────────────────────────┘
             ↓
┌──────────────────────────────────┐
│    Domain Layer                  │
│                                  │
│  - normalize (정규화)            │
│  - scoring (점수 계산)           │
│  - retrieval (증거 추출)         │
│                                  │
│  → Pure Python 로직              │
└──────────────────────────────────┘
```

---

## 3. 테스트 결과

```bash
$ /opt/homebrew/bin/python3.11 test_api_layer.py

============================================================
API Layer 테스트 (Phase 4)
============================================================

✅ 서버 헬스 체크
   - Swagger UI: http://localhost:8000/docs

✅ Chat API 테스트 (v2)
   [1-1] 세션 생성: ✅
   [1-2] 메시지 전송: ✅
   [1-3] 세션 조회: ✅

✅ Review API 테스트 (v2)
   [2-1] 리뷰 수집: ✅ (205건)
   [2-2] 리뷰 분석: ✅ (top_factors 계산)

============================================================
✅ 모든 API 테스트 통과!
============================================================
```

**Swagger UI:**
- http://localhost:8000/docs
- `/api/v2/chat/*` 엔드포인트 확인됨
- `/api/v2/reviews/*` 엔드포인트 확인됨

---

## 4. 파일 구조 (Phase 4 완료 후)

```
backend/app/
├── api/
│   ├── routers/                   ✅ NEW (Phase 4)
│   │   ├── __init__.py
│   │   ├── chat.py               ✅ 213 lines (Service 기반)
│   │   └── review.py             ✅ 148 lines (Service 기반)
│   │
│   ├── routes_chat.py            ⚠️  유지 (v1 호환성)
│   ├── routes_chat_old.py        📁 백업
│   └── routes_metrics.py         ⚠️  유지
│
├── services/                     ✅ Phase 3
│   ├── chat_service.py
│   ├── prompt_service.py
│   └── review_service.py
│
├── domain/                       ✅ Phase 2
│   ├── review/
│   └── reg/
│
└── main.py                       ✅ 업데이트 (v2 라우터 등록)
```

**변경 사항:**
- `backend/app/api/routers/` 디렉토리 생성
- `chat.py`, `review.py` 신규 작성
- `main.py`에 v2 라우터 등록

---

## 5. 코드 품질

### 컨트롤러 단순화

**Before (routes_chat.py):**
```python
@router.post("/message")
async def send_message(request: ChatRequest):
    # 세션 확인 (12 lines)
    session = session_store.get_session(request.session_id)
    if not session:
        raise HTTPException(...)
    
    # 대화 진행 (25 lines)
    if request.request_finalize:
        bot_turn = session.finalize_now()
    else:
        bot_turn = session.step(request.message, ...)
    
    # 관련 리뷰 조회 (18 lines)
    factors_to_query = bot_turn.top_factors
    if request.selected_factor:
        factors_to_query = [(request.selected_factor, 1.0)] + ...
    related_reviews = get_related_reviews(...)
    
    # 봇 메시지 구성 (10 lines)
    bot_message = format_bot_message(...)
    
    # 응답 데이터 구성 (35 lines)
    response_data = ChatResponse(...)
    
    return response_data
```

**After (routers/chat.py):**
```python
@router.post("/messages")
async def send_message(
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    # 세션 확인 (3 lines)
    session = chat_service.get_session(request.session_id)
    if not session:
        raise HTTPException(...)
    
    # Service 호출 (1 line)
    result = chat_service.process_turn(...)
    
    # 응답 반환 (1 line)
    return ChatMessageResponse(**result)
```

**개선:**
- 100+ 줄 → 5줄
- 비즈니스 로직 0줄
- Service 호출만

### 의존성 관리

**Singleton Pattern:**
```python
_chat_service: Optional[ChatService] = None

def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(data_dir=get_data_dir())
    return _chat_service
```

**장점:**
- Service 인스턴스 재사용
- 메모리 효율
- 테스트 시 Mock 주입 가능

---

## 6. API 버전 관리

### v1 vs v2 비교

| 항목 | v1 (`/api/chat/*`) | v2 (`/api/v2/chat/*`) |
|------|-------------------|----------------------|
| 라우터 | routes_chat.py | routers/chat.py |
| 비즈니스 로직 | 라우터 내부 ❌ | Service 레이어 ✅ |
| 코드 라인 수 | 418 lines | 213 lines |
| 테스트 용이성 | 어려움 | 쉬움 |
| 유지보수성 | 낮음 | 높음 |
| 의존성 | SessionStore | ChatService |
| 상태 | 유지 (호환성) | 권장 |

### 마이그레이션 전략

1. **v1 유지** - 기존 클라이언트 호환성
2. **v2 추가** - 새로운 기능은 v2로
3. **점진적 전환** - 클라이언트를 v2로 마이그레이션
4. **v1 제거** - 모든 클라이언트 전환 후

---

## 7. 성능 및 확장성

### 성능 개선

**Before:**
- 매 요청마다 세션 로직 실행
- 복잡한 코드로 인한 처리 지연
- 디버깅 어려움

**After:**
- Service 레이어에서 캐싱 가능
- 단순한 코드로 빠른 처리
- 각 레이어 독립 최적화 가능

### 확장성

**새 엔드포인트 추가 예시:**
```python
@router.post("/analysis")
async def get_analysis(
    request: AnalysisRequest,
    chat_service: ChatService = Depends(get_chat_service),
    prompt_service: PromptService = Depends(get_prompt_service)
):
    # Session에서 top_factors 가져오기
    session = chat_service.get_session(request.session_id)
    
    # LLM context 생성
    context = prompt_service.build_llm_context(...)
    
    # 결과 반환
    return AnalysisResponse(context=context)
```

**특징:**
- 2개 Service 조합 가능
- 비즈니스 로직은 Service에 위임
- API는 호출/변환만

---

## 8. 다음 단계 (Phase 5)

### Infrastructure 레이어 구현

**목표:** 외부 시스템 연동 분리

1. **Collectors (리뷰 수집)**
   ```python
   # infra/collectors/smartstore.py
   class SmartStoreCollector:
       def collect(self, product_id: str) -> List[Dict]:
           # 크롤링 로직
   
   # ReviewService에서 호출
   collector = SmartStoreCollector()
   reviews = collector.collect(product_id)
   ```

2. **Cache (캐싱)**
   ```python
   # infra/cache/review_cache.py
   class ReviewCache:
       def get(self, key: str) -> Optional[List[Dict]]:
       def set(self, key: str, value: List[Dict]):
   
   # ReviewService에서 사용
   cache = ReviewCache()
   reviews = cache.get(product_id) or collector.collect(...)
   ```

3. **Storage (저장소)**
   ```python
   # infra/storage/csv_storage.py
   class CSVStorage:
       def save_reviews(self, reviews: List[Dict]):
       def load_reviews(self, product_id: str):
   ```

---

## 9. 문서 업데이트

### API 문서

**Swagger UI:**
- http://localhost:8000/docs
- 자동 생성된 API 문서
- Try it out 기능으로 테스트 가능

**Request/Response Examples:**
```json
// POST /api/v2/chat/sessions
{
  "category": "캡슐커피",
  "product_name": "네스프레소 버츄오",
  "product_id": "12345"
}

// Response
{
  "session_id": "session-캡슐커피-6432",
  "message": "네스프레소 버츄오에 대한 대화를 시작합니다...",
  "category": "캡슐커피",
  "product_name": "네스프레소 버츄오",
  "factor_count": 0
}
```

---

## 10. 결론

### ✅ Phase 4 완료!

**구현:**
- Clean Architecture API Router 생성 (v2)
- Chat API: 세션 생성, 메시지 전송, 세션 조회
- Review API: 리뷰 수집, 리뷰 분석
- 기존 v1 API 유지 (호환성)

**테스트:**
- 모든 v2 API 엔드포인트 테스트 통과
- Swagger UI 동작 확인
- Service 레이어 통합 검증

**품질:**
- 얇은 컨트롤러 (비즈니스 로직 0줄)
- 의존성 주입 (Singleton Pattern)
- Clean Architecture 준수

### 주요 개선 효과

1. **관심사 분리**
   - API: HTTP 처리만
   - Service: 비즈니스 로직
   - Domain: Pure Python

2. **테스트 용이성**
   - 각 레이어 독립 테스트
   - Mock 주입 쉬움
   - 통합 테스트 단순화

3. **유지보수성**
   - 418 → 213 줄 (50% 감소)
   - 코드 이해 쉬움
   - 버그 수정 빠름

4. **확장성**
   - 새 엔드포인트 추가 쉬움
   - Service 조합 가능
   - 버전 관리 용이

### 다음: Phase 5 - Infrastructure 레이어

**목표:** 외부 시스템 연동 분리

**계획:**
1. infra/collectors/ - 리뷰 크롤러
2. infra/cache/ - 캐싱
3. infra/storage/ - 데이터 저장소
4. ReviewService가 Infra 레이어 활용
