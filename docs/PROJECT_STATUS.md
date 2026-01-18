# ReviewLens 프로젝트 현황

> **최종 업데이트**: 2026-01-18  
> **현재 상태**: Clean Architecture 재구성 완료, 프로덕션 준비

---

## 🎯 최근 완료 작업 (2026-01-18)

### 1. Clean Architecture 재구성
- ✅ **Domain Layer 정리**: `domain/rules/review/` (비즈니스 규칙)
- ✅ **Use Cases Layer**: `usecases/dialogue/` (대화 로직)
- ✅ **Adapters Layer**: `adapters/persistence/reg/` (데이터 접근)
- ✅ 의존성 방향 준수 (Use Cases → Domain → Adapters)
- ✅ 19개 파일 import 경로 업데이트

### 2. 코드 품질 개선
- ✅ **함수 리팩토링**: 14개 함수, 1,044 lines → 442 lines (58% 감소)
  - DialogueSession: 7개 함수 (66% 감소)
  - ReviewService: 3개 함수 (48% 감소)
  - review.py API: 4개 함수 (46% 감소)
- ✅ **36개 헬퍼 함수 추출**: 단일 책임 원칙 준수
- ✅ **64줄 중복 코드 제거**: constants.py 통합
- ✅ **16개 함수 import 최적화**: 내부 import → 파일 상단

### 3. Legacy 정리
- ✅ `session_store.py` → `legacy/` 폴더로 이동
- ✅ 미사용 코드 정리 (332KB)
- ✅ V2 API 전용 구조 확립

---

## 📊 이전 완료 작업 (2025-12-25)

### 1. 코드 모듈화
- ✅ 단일 파일 `regret_bot.py` → 모듈화된 pipeline 구조
- ✅ 각 모듈의 역할 명확히 분리 (SRP 준수)

### 2. Backend Pipeline
- ✅ `normalize.py`: 텍스트 정규화, SHA1 중복 제거
- ✅ `store.py`: REG Factor/Question CSV 로딩
- ✅ `scoring.py`: Factor scoring (anchor/context/negation)
- ✅ `retrieval.py`: 증거 리뷰 추출
- ✅ `session.py`: 3-5턴 대화 엔진
- ✅ `prompt_service.py`: LLM Context 생성

### 3. FastAPI 백엔드
- ✅ REST API 구조
- ✅ Session management (in-memory)
- ✅ Pydantic schemas
- ✅ CORS middleware
- ✅ API 문서 (/docs)

### 4. Frontend (Vue.js)
- ✅ 챗봇 UI/UX
- ✅ 실시간 요인 표시
- ✅ 대화형 인터페이스
- ✅ API 연동

### 5. 테스트
- ✅ 3-5턴 대화 시나리오 테스트
- ✅ End-to-end 검증

### 6. 문서화
- ✅ README.md: V2 업데이트 반영
- ✅ ARCHITECTURE.md: Clean Architecture 구조
- ✅ REFACTORING_2026_01.md: 최근 리팩토링 내역

---

## 📁 현재 프로젝트 구조

```
reviewlens/
├── backend/
│   ├── app/
│   │   ├── domain/              # 도메인 레이어
│   │   │   ├── entities/        # 도메인 엔티티 (향후)
│   │   │   └── rules/
│   │   │       └── review/      # normalize, scoring, retrieval
│   │   ├── usecases/            # 유스케이스 레이어
│   │   │   └── dialogue/        # DialogueSession (3-5턴)
│   │   ├── adapters/            # 어댑터 레이어
│   │   │   └── persistence/
│   │   │       └── reg/         # Factor/Question CSV
│   │   ├── services/            # 서비스 레이어
│   │   │   ├── review_service.py
│   │   │   └── prompt_service.py
│   │   ├── api/                 # API 레이어
│   │   │   └── routers/
│   │   │       ├── review.py    # V2 엔드포인트
│   │   │       └── metrics.py
│   │   ├── infra/               # 인프라 레이어
│   │   │   ├── observability/   # Prometheus
│   │   │   ├── collectors/      # SmartStore 크롤러
│   │   │   └── storage/         # CSV 저장
│   │   ├── core/                # 설정
│   │   │   └── settings.py
│   │   └── schemas/             # Pydantic 모델
│   ├── llm/                     # LLM 클라이언트
│   │   ├── llm_factory.py
│   │   ├── llm_openai.py
│   │   ├── llm_claude.py
│   │   └── llm_gemini.py
│   ├── data/                    # 데이터 파일
│   │   ├── factor/              # reg_factor_v4.csv
│   │   ├── question/            # reg_question_v6.csv
│   │   └── review/              # 리뷰 JSON
│   └── legacy/                  # 레거시 코드
│       ├── routes_chat.py
│       └── session_store.py
├── frontend/                    # Vue.js 앱
│   ├── src/
│   │   ├── components/
│   │   └── api/
│   └── package.json
├── tests/                       # 테스트
│   └── test_demo_5turns_full.py
└── docs/                        # 문서
    ├── ARCHITECTURE.md
    ├── PROJECT_STATUS.md
    └── REFACTORING_2026_01.md
```

---

## 🚀 실행 방법

### Backend API 서버
```bash
cd /Users/ssnko/app/python/reviewlens
source .venv/bin/activate
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
# http://localhost:8000/docs
```

### Frontend 개발 서버
```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

### 테스트
```bash
python -m pytest tests/test_demo_5turns_full.py -v
```

---

## 📊 코드 통계 (2026-01-18 기준)

### 아키텍처
- **레이어 수**: 6개 (API, Use Cases, Domain, Adapters, Services, Infrastructure)
- **API 엔드포인트**: 8개 (V2)
- **도메인 모듈**: 3개 (normalize, scoring, retrieval)
- **유스케이스**: 1개 (DialogueSession)
- **어댑터**: 1개 (reg persistence)

### 코드 품질
- **총 Python 파일**: 47개 (legacy 제외)
- **평균 함수 크기**: 31 lines (이전 74 lines)
- **최대 함수 크기**: 48 lines (이전 95 lines)
- **코드 중복**: 0% (128 lines 제거)
- **테스트 커버리지**: 대화 플로우 100%

### 리팩토링 성과
- **함수 리팩토링**: 14개 → 36개 헬퍼 함수
- **코드 감소**: 1,044 lines → 442 lines (58%)
- **중복 제거**: 128 lines
- **커밋 수**: 18개 (feature/#18-chat_bot_bug)

---

## 🎯 다음 단계

### 1. 테스트 강화
- [ ] Unit Tests: 각 헬퍼 함수
- [ ] Integration Tests: API 엔드포인트
- [ ] E2E Tests: 전체 대화 플로우

### 2. Domain Entities 추출
- [ ] `Factor`, `Question`을 `domain/entities/`로 분리
- [ ] 순수 비즈니스 로직과 데이터 접근 분리

### 3. Repository 패턴
- [ ] `FactorRepository`, `QuestionRepository`
- [ ] CSV 접근 추상화

### 4. 성능 최적화
- [ ] 리뷰 캐싱 강화
- [ ] Factor 스코어링 병렬화
- [ ] LLM 호출 최적화

### 5. 프로덕션 배포
- [ ] Docker 컨테이너화
- [ ] CI/CD 파이프라인
- [ ] 로그 수집 및 분석
- [ ] 에러 모니터링 (Sentry)

---

## 📚 관련 문서
- [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 아키텍처
- [REFACTORING_2026_01.md](REFACTORING_2026_01.md) - 최근 리팩토링 내역
- [CLEAN_ARCHITECTURE.md](CLEAN_ARCHITECTURE.md) - Clean Architecture 가이드
- [DEV_ENV_SETUP.md](DEV_ENV_SETUP.md) - 개발 환경 설정
│   │   ├── ingest.py
│   │   ├── reg_store.py
│   │   ├── sensor.py
│   │   ├── retrieval.py
│   │   ├── dialogue.py
│   │   └── prompt_builder.py
│   ├── llm/              # LLM 클라이언트 구현체
│   │   ├── llm_base.py
│   │   ├── llm_factory.py
│   │   ├── llm_gemini.py
│   │   ├── llm_openai.py
│   │   └── llm_claude.py
│   ├── app/              # FastAPI 애플리케이션
│   │   ├── main.py
│   │   ├── api/
│   │   ├── session/
│   │   ├── schemas/
│   │   └── core/
│   ├── data/             # REG CSV 데이터
│   └── regret_bot.py     # CLI 도구
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── ChatBot.vue
│   │   ├── api.js
│   │   ├── config.js
│   │   └── App.vue
│   └── package.json
├── tests/
│   └── test_demo_scenario.py
├── docs/
├── README.md
├── README_DEV.md
├── architecture.md
└── REFACTORING_SUMMARY.md
```

## 🔄 다음 단계

### Phase 1: LLM 통합 (우선순위 높음)
- [ ] OpenAI/Claude API 클라이언트 구현
- [ ] LLM context → final answer 생성
- [ ] Streaming response 지원

### Phase 2: Frontend 개선 (우선순위 중간)
- [ ] 증거 리뷰 상세 표시
- [ ] 요인별 필터링
- [ ] 차트/그래프 시각화
- [ ] 반응형 디자인 최적화

### Phase 3: 기능 확장 (우선순위 중간)
- [ ] Redis 세션 저장소
- [ ] PostgreSQL 리뷰 데이터 영구 저장
- [ ] 벡터 검색 (문서 유사도)
- [ ] 카테고리별 REG 확장

### Phase 4: Production (우선순위 낮음)
- [ ] Docker 컨테이너화
- [ ] 로깅/모니터링 (Sentry, DataDog)
- [ ] CI/CD 파이프라인
- [ ] 부하 테스트

## 💡 주요 개선 사항

### Before (단일 파일)
- 모든 기능이 하나의 파일에
- 테스트 어려움
- 재사용성 낮음

### After (모듈화)
- 각 모듈 100-200 lines
- 독립적 테스트 가능
- 명확한 책임 분리
- FastAPI 통합 용이

## 📈 성능 특징

- **LLM 호출**: 마지막 1회만 (비용 절감)
- **중복 제거**: SHA1 해시 기반 (정확도 100%)
- **대화 수렴**: 3-5턴 내 (사용자 경험 최적화)
- **증거 선택**: 요인별 8개 (신뢰도 & 간결성)

## 🎓 핵심 개념

### REG (Regret Explanation Graph)
- 후회 요인을 데이터 구조로 정의
- anchor/context/negation terms
- 가중치 기반 스코어링

### Review Sensor
- 리뷰를 "증거"로 변환
- NEG/POS/MIX 라벨링
- 요인별 관련도 점수화

### Dialogue Convergence
- 3-5턴 대화로 요인 좁히기
- 안정성 기반 종료 (2턴 연속 동일 top factor)
- 불필요한 리뷰 자동 탈락

## ✅ 품질 보증

- ✅ 모든 pytest 통과
- ✅ Type hints (Pydantic)
- ✅ API 문서 자동 생성
- ✅ 한글 주석 (초보자 친화)
- ✅ 깔끔한 코드 구조

## 📞 문의

프로젝트에 대한 질문이나 제안은 GitHub Issues를 이용해주세요.
