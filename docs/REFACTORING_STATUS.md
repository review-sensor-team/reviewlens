# Backend 리팩토링 현황 (2026-01-17)

## ✅ 완료 상태

### 1. 폴더 구조 생성 완료 ✅

### 2. Domain 레이어 분리 완료 ✅

**Pure Python 비즈니스 로직 (외부 의존성 제거)**

- ✅ **domain/review/normalize.py**
  - `normalize_text()` - 텍스트 정규화
  - `dedupe_reviews()` - 중복 제거
  - `normalize_review()` - 벤더별 리뷰 정규화

- ✅ **domain/reg/store.py**
  - `Factor`, `Question` 데이터 클래스
  - `load_csvs()` - CSV 로드
  - `parse_factors()`, `parse_questions()` - 파싱

- ✅ **domain/review/scoring.py**
  - `score_text_against_factor()` - Factor 점수 계산
  - `compute_review_factor_scores()` - 전체 리뷰 스코어링
  - Anchor/Context/Negation 로직

- ✅ **domain/review/retrieval.py**
  - `retrieve_evidence_reviews()` - Evidence 추출
  - Quota, Label, Excerpt 생성

**테스트 완료:**
```bash
✅ Normalized: 테스트!! ㅋㅋ
✅ Score: 1.0, Reasons: ['anchor']
✅ Domain layer working!
```

### 3. 환경 설정 완료 ✅

- ✅ Python 3.11.12 (Homebrew)
- ✅ 패키지 의존성 정리
  - langchain 제거 (pydantic 2 충돌)
  - numpy 2.4.1, pandas 2.3.3
- ✅ Import 경로 검증 완료

### 3. 서버 시작 가능

```bash
cd /Users/ssnko/app/python/reviewlens
/opt/homebrew/bin/python3.11 -m backend.app.main
```

---

## 🎯 전략: 점진적 마이그레이션

기존 코드를 유지하면서 새 구조로 점진적으로 전환:

### Phase 1: 인프라 준비 ✅ (완료)
- 새 폴더 구조 생성
- 기본 모듈 파일 작성
- 환경 설정 완료

### Phase 2: Domain 레이어 분리 ✅ (완료)
1. **dialogue.py → domain/dialogue/session.py** (진행 예정)
   - DialogueSession 클래스 분리
   - 순수 비즈니스 로직만 유지
   - FastAPI 의존성 제거

2. **reg_store.py → domain/reg/store.py** ✅
   - Factor/Question 로드 로직
   - CSV 파싱 로직
   - 외부 의존성 제거 완료

3. **retrieval.py, sensor.py → domain/review/** ✅
   - scoring.py: Factor 점수 계산 ✅
   - retrieval.py: Evidence 추출 ✅
   - normalize.py: 리뷰 정규화 ✅
   - 모든 순수 Python 함수로 전환 완료

### Phase 3: Service 레이어 구현 ✅ (완료)

**비즈니스 유스케이스 오케스트레이션 레이어**

- ✅ **services/chat_service.py**
  - `ChatService` - 대화 세션 관리
  - `create_session()` - 세션 생성 및 Factor/Question 로드
  - `process_turn()` - 사용자 메시지 처리, Factor 점수 추출
  - `DialogueSessionState` - 세션 상태 관리 (turn_count, cumulative_scores)
  - 질문 생성, Top factors 계산, 분석 준비 체크

- ✅ **services/prompt_service.py**
  - `PromptService` - LLM context/prompt 생성
  - `build_llm_context()` - LLM용 JSON context (meta, top_factors, evidence_reviews, safety_rules)
  - `build_prompt()` - LLM 프롬프트 텍스트 생성
  - `format_analysis_response()` - LLM 응답 포맷팅
  - Schema versioning (v2)

- ✅ **services/review_service.py**
  - `ReviewService` - 리뷰 수집 및 분석
  - `collect_reviews()` - 리뷰 수집 (현재: 샘플 데이터 로드)
  - `normalize_reviews()` - 리뷰 정규화 및 중복 제거
  - `analyze_reviews()` - Factor scoring, 점수 집계
  - `get_evidence_reviews()` - 증거 리뷰 추출
  - Domain 레이어 함수 호출 (normalize, scoring, retrieval)

**테스트 완료:**
```bash
✅ ChatService: 세션 생성, 턴 처리, 분석 준비
✅ PromptService: LLM context, 프롬프트, 응답 포맷팅
✅ ReviewService: 리뷰 수집, 정규화, 분석, 증거 추출
✅ 모든 Service 레이어 테스트 통과!
```

### Phase 4: API 레이어 단순화 ✅ (완료)

**얇은 컨트롤러 - Service 레이어만 호출**

- ✅ **api/routers/chat.py** (v2 - Clean Architecture)
  - `POST /api/v2/chat/sessions` - 세션 생성
  - `POST /api/v2/chat/messages` - 메시지 전송
  - `GET /api/v2/chat/sessions/{id}` - 세션 조회
  - `DELETE /api/v2/chat/sessions/{id}` - 세션 삭제
  - 의존성 주입: `Depends(get_chat_service)`
  - 비즈니스 로직 0줄 (모두 Service로 위임)
  - 418 lines → 213 lines (50% 감소)

- ✅ **api/routers/review.py** (v2 - Clean Architecture)
  - `POST /api/v2/reviews/collect` - 리뷰 수집
  - `POST /api/v2/reviews/analyze` - 리뷰 분석
  - ReviewService 통합
  - Domain 레이어 활용 (parse_factors, normalize, scoring)

- ✅ **main.py 업데이트**
  - v1 라우터 유지 (`/api/chat/*`) - 기존 호환성
  - v2 라우터 추가 (`/api/v2/chat/*`, `/api/v2/reviews/*`)
  - Swagger UI: http://localhost:8000/docs

**테스트 완료:**
```bash
✅ Chat API: 세션 생성, 메시지 전송, 세션 조회
✅ Review API: 리뷰 수집 (205건), 리뷰 분석 (top_factors)
✅ 모든 API 테스트 통과!
```

**아키텍처 개선:**
- Before: 모든 로직이 routes_chat.py에 혼재 (418 lines)
- After: API는 HTTP만, Service는 비즈니스 로직 (213 lines)
- 의존성 주입, 싱글톤 패턴, Clean Architecture 준수

### Phase 5: Infrastructure 레이어 (진행 예정)

**외부 시스템 연동 및 캐시**

1. **infra/collectors/** - 리뷰 수집기
   - `smartstore.py` - 스마트스토어 크롤러
   - `coupang.py` - 쿠팡 크롤러 (TODO)
   - ReviewService에서 호출

2. **infra/cache/** - 캐시 관리
   - `review_cache.py` - 리뷰 캐싱
   - `session_cache.py` - 세션 캐싱

3. **infra/storage/** - 데이터 저장
   - `csv_storage.py` - CSV 저장소
   - `backup_storage.py` - 백업 관리

### Phase 6: LLM Service 통합 (진행 예정)
   - 리뷰 수집 로직
   - 리뷰 분석 로직

3. **PromptService**
   - LLM 프롬프트 생성
   - Context 조합

### Phase 4: API 레이어 간소화 (진행 예정)
- routes_chat.py를 얇게 만들기
- Service만 호출하도록 변경
- 비즈니스 로직 제거

---

## 🔧 개발 가이드

### 실행 방법

```bash
# 1. 프로젝트 루트로 이동
cd /Users/ssnko/app/python/reviewlens

# 2. 서버 시작 (Python 3.11 필수)
/opt/homebrew/bin/python3.11 -m backend.app.main

# 3. 또는 uvicorn 직접 사용
/opt/homebrew/bin/python3.11 -m uvicorn backend.app.main:app \
  --reload \
  --host 0.0.0.0 \
  --port 8000
```

### 테스트

```bash
# Import 테스트
/opt/homebrew/bin/python3.11 -c "
import backend.app.main
print('✅ Server can start')
"

# API 테스트
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

### Python 버전 주의사항

**❌ 사용하지 말 것:**
```bash
python3 -m backend.app.main   # macOS 기본 Python 3.9 사용 (오류 발생)
```

**✅ 올바른 방법:**
```bash
/opt/homebrew/bin/python3.11 -m backend.app.main  # Python 3.11 명시
python3.11 -m backend.app.main                     # python3.11이 PATH에 있는 경우
```

---

## 📚 참고 문서

1. **[BACKEND_REFACTORING.md](BACKEND_REFACTORING.md)**
   - 상세 리팩토링 가이드
   - Clean Architecture 설명
   - 마이그레이션 체크리스트

2. **[FastAPI_리팩토링_및_팀별_개발가이드.md](FastAPI_리팩토링_및_팀별_개발가이드.md)**
   - 팀별 역할 분담
   - API/ML/FE/인프라 팀 가이드
   - 인터페이스 설계

---

## ⚠️ 주의사항

1. **기존 코드는 유지됩니다**
   - routes_chat.py, routes_metrics.py는 그대로 동작
   - 새 구조는 병행 개발

2. **의존성 충돌 해결됨**
   - langchain 제거 (불필요)
   - pydantic 2.10.0 사용
   - numpy 2.4.1 사용

3. **Python 버전 혼재**
   - 반드시 Python 3.11 사용
   - Homebrew Python 경로: `/opt/homebrew/bin/python3.11`

---

## 📞 다음 액션

### 우선순위 1: 서버 동작 확인
```bash
/opt/homebrew/bin/python3.11 -m backend.app.main
```
- [ ] 서버 시작 확인
- [ ] `/health` 엔드포인트 테스트
- [ ] `/metrics` 엔드포인트 테스트

### 우선순위 2: Domain 레이어 분리
- [ ] DialogueSession 순수 클래스화
- [ ] Factor scoring 로직 분리
- [ ] Evidence retrieval 로직 분리

### 우선순위 3: Service 레이어 구현
- [ ] ChatService 기본 구현
- [ ] ReviewService 기본 구현
- [ ] API에서 Service 호출하도록 변경

---

**마지막 업데이트**: 2026년 1월 17일  
**상태**: 환경 설정 완료, 서버 시작 가능, 점진적 마이그레이션 준비 완료
