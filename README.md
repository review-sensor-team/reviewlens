# ReviewLens V2
### 후회를 줄이기 위한 대화형 리뷰 분석 챗봇

> **V2 업데이트 (2026-01-18)**: Clean Architecture 재구성 완료, 코드 품질 개선

---

## 한 줄 요약
**ReviewLens는 리뷰를 요약하지 않는다.**  
대신, 리뷰 속 *후회 요인(Regret Factor)*을 기준으로  
**사용자와 3~5턴 대화를 통해 판단에 필요한 근거만 추출**한다.

---

## 주요 변경사항 (V2)

### ✅ Clean Architecture 재구성 (2026-01-18)
- **Domain Layer**:
  - `domain/entities/` - 순수 도메인 엔티티 (향후 확장)
  - `domain/rules/review/` - 도메인 비즈니스 규칙 (normalize, scoring, retrieval)
- **Use Cases Layer**:
  - `usecases/dialogue/` - DialogueSession (3-5턴 대화 로직)
- **Adapters Layer**:
  - `adapters/persistence/reg/` - Factor/Question CSV 로딩
- **Infrastructure Layer**: 외부 연동 (observability, collectors, storage)
- **API Layer**: REST 엔드포인트 (v2)

### ✅ 코드 품질 개선
- **함수 리팩토링**: 14개 대형 함수 분리 (평균 60+ 라인 → 20-30 라인)
  - DialogueSession: 7개 함수 (66% 코드 감소)
  - ReviewService: 3개 함수 (48% 코드 감소)
  - review.py: 4개 함수 (46% 코드 감소)
- **중복 코드 제거**: 64줄의 중복 상수를 constants.py로 통합
- **Import 최적화**: 모든 내부 import를 파일 상단으로 이동
- **Legacy 정리**: 332KB 미사용 코드를 legacy 폴더로 이동

### ✅ 3-5턴 대화 플로우
- 질문별 question_id 추적
- 중복 질문 자동 필터링 (텍스트 기반)
- Fallback 질문 시스템 (카테고리별 10개)
- LLM 분석 통합 (GPT-4o-mini)

### ✅ API 구조
- `/api/v2/reviews/*` - V2 Clean Architecture 엔드포인트
- 세션 기반 상태 관리 (in-memory cache)
- 증거 리뷰 추출 최적화

---

## 해결하려는 문제
- 리뷰는 수백~수천 개지만, **내 상황에 중요한 리뷰는 극히 일부**
- 다 읽고도 남는 질문: *“그래서 나한테는 괜찮다는 거야?”*
- LLM 전체 요약은 비용이 크고, **왜 그런 결론인지 설명이 약함**

---

## 핵심 접근 방식

### 1️⃣ REG (Regret Explanation Graph)
사람들이 실제로 후회하는 요인을 **데이터 구조로 정의**
- 예: 소음 / 관리 번거로움 / 안전 / 기대 대비 성능

→ 모델이 아니라 **사고 프레임**

---

### 2️⃣ 리뷰 센서 (Review Sensor)
각 리뷰를 다음으로 분해:
- 어떤 후회 요인과 관련 있는가?
- 불만(NEG) / 우려 해소(POS) / 조건부(MIX) 중 어디인가?

→ 리뷰를 **요약 대상이 아닌 ‘증거’로 변환**

---

### 3️⃣ 대화 기반 수렴
챗봇이 정답을 말하지 않고 **질문을 던져 조건을 좁힘**
- 3~5턴 대화로 중요 factor 수렴
- 불필요한 리뷰는 자동 탈락

---

## 데이터 파이프라인 (요약)

```
상품 선택 (reg_factor_v4.csv)
  ↓
리뷰 JSON 로드 (미리 수집된 파일)
  ↓
Factor 매칭 (FactorAnalyzer)
  ↓
정규화 · 중복 제거
  ↓
REG factor 스코어링
  ↓
리뷰 분류 (NEG / POS / MIX)
  ↓
대화 (3~5턴)
  ↓
근거 리뷰 추출
  ↓
LLM 호출 직전 Context 생성
  ↓
(선택) LLM 1회 요약
```

---

## 왜 이 구조가 중요한가

| 항목 | 기존 리뷰 요약 | ReviewLens |
|---|---|---|
| LLM 사용 | 리뷰 전체 | **마지막 1회** |
| 비용 | 리뷰 수에 비례 | **거의 고정** |
| 설명력 | 낮음 | **근거 리뷰 명확** |
| 사용자 역할 | 읽기 | **판단 참여** |

---

## 결과
- “많은 리뷰를 요약해주는 서비스” ❌  
- **“내 상황에서 후회할 가능성을 구조적으로 보여주는 서비스” ⭕**

---

## 핵심 메시지
> **ReviewLens는  
> 리뷰를 읽게 하지 않고,  
> 후회를 미리 생각하게 만든다.**

---

## 현재 구현 상태 (Implementation Status)

### ✅ 구현 완료 (MVP)

#### Backend Architecture (Clean Architecture - V2)
```
backend/
├── app/                      # Application Layer
│   ├── main.py              # FastAPI app (V2 only)
│   ├── core/
│   │   ├── settings.py      # 환경 설정
│   │   └── logging.py       # 로깅 설정
│   ├── api/
│   │   └── routers/
│   │       ├── health.py    # Health check
│   │       └── review.py    # V2 리뷰 분석 API
│   │           # POST /api/v2/reviews/analyze-product - 상품 분석 시작
│   │           # POST /api/v2/reviews/answer-question - 질문 답변
│   │           # GET  /api/v2/reviews/factor-reviews - Factor별 리뷰
│   │           # GET  /api/v2/reviews/products - 상품 목록
│   │           # GET  /api/v2/reviews/config - 앱 설정
│   ├── domain/              # Domain Layer (비즈니스 로직)
│   │   ├── dialogue/
│   │   │   └── session.py   # 3-5턴 대화 엔진
│   │   ├── reg/
│   │   │   ├── store.py     # Factor/Question CSV 로딩
│   │   │   └── matching.py  # 질문-팩터 매칭
│   │   └── review/
│   │       ├── normalize.py # 리뷰 정규화
│   │       ├── scoring.py   # Factor 점수 계산
│   │       └── retrieval.py # 증거 리뷰 추출
│   ├── infra/               # Infrastructure Layer
│   │   ├── observability/
│   │   │   └── metrics.py   # Prometheus 메트릭
│   │   └── session/
│   │       └── store.py     # 세션 저장소
│   └── services/            # Application Services
│       └── review_loader.py # 리뷰 파일 로딩
├── llm/                     # LLM 통합 (독립 모듈)
│   ├── llm_factory.py
│   ├── llm_openai.py        # GPT-4o-mini
│   ├── llm_claude.py
│   └── llm_gemini.py
├── data/
│   ├── factor/
│   │   └── reg_factor_v4.csv    # 10개 상품, 100개 factors
│   ├── question/
│   │   └── reg_question_v6.csv  # 100개 질문
│   └── review/
│       └── reviews_*.json       # 사전 수집된 리뷰
├── legacy/                  # V1 레거시 코드 (332KB)
│   ├── dialogue_old/
│   ├── core_old/
│   ├── collector_old/
│   └── session_old/
└── out/                     # LLM 컨텍스트 출력
    ├── llm_context_*.json
    └── llm_prompt_*.txt
```

#### Frontend (Vue.js + Vite)
```
frontend/
├── src/
│   ├── components/
│   │   └── ReviewLens.vue    # V2 리뷰 분석 UI
│   │       # - 3-5턴 대화 플로우
│   │       # - 질문 선택지 표시
│   │       # - 증거 리뷰 표시
│   │       # - LLM 분석 결과 (Markdown)
│   │       # - 모바일 반응형
│   ├── api/
│   │   └── chat.js          # V2 API 호출
│   ├── config.js
│   └── main.js
├── index.html
├── package.json
└── vite.config.js
```

**주요 기능:**
- ✅ **상품 선택 모드**
  - 10개 카테고리 제품 (reg_factor_v4.csv)
  - 카테고리별 factor 자동 필터링
- ✅ **3-5턴 대화 플로우**
  - 질문-답변 추적 (question_id 기반)
  - 중복 질문 자동 스킵
  - Fallback 질문 지원
- ✅ **증거 기반 분석**
  - Factor별 리뷰 추출
  - POS/NEG/MIX 라벨링
  - Anchor term 매칭
  - 미리 수집된 JSON 파일에서 리뷰 로드
- ✅ 3-5턴 대화형 UI
- ✅ 실시간 후회 요인 뱃지 표시
- ✅ 분석 완료 시 계산 공식 및 누적 점수 표시
- ✅ 모바일/태블릿 반응형 디자인
- ✅ 대화 히스토리 유지 (스크롤 가능)
- ✅ 세션 재분석 ("상품 재분석" 버튼)
- ✅ 분석 초기화 ("분석 초기화" 버튼)
- ✅ Category 자동 매핑 (CSV category → JSON filename)

#### Test Suite
- ✅ **tests/test_demo_scenario.py**: 3-5 turn dialogue pytest PASSED
- ✅ **tests/test_demo_5turns_full.py**: DEMO_SCENARIO_5TURNS.md 시나리오 검증
- 대화형 시나리오 검증 완료

### 🚧 진행 중
- UI/UX 디자인 적용
- LLM API 통합

### 📋 계획 중
- 팩터와 질문 데이터 자동 생성(백그라운드 잡)
- LLM 프롬프트 최적화
- 벡터 기반 후회 리뷰 추출
- 멀티 카테고리 확장

---

## 개발 환경 설정

### 1. Virtual Environment 생성 및 활성화
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or .venv\Scripts\activate on Windows
```

### 2. 의존성 설치
```bash
pip install -r backend/requirements.txt
```

### 3. 테스트 실행
```bash
# 3-5 turn dialogue test
python -m pytest tests/test_demo_scenario.py -v

# CLI 테스트
python -m backend.regret_bot
```

### 4. FastAPI 서버 실행
```bash
uvicorn backend.app.main:app --reload
# API Docs: http://localhost:8000/docs
# Test endpoints:
#   POST /api/chat/start - 세션 시작
#   POST /api/chat/message - 메시지 전송
```

### 5. 프론트엔드 개발 서버 실행
```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

### 6. 모니터링 시작 (선택사항)
```bash
# Docker로 Prometheus + Grafana 시작
docker-compose -f docker-compose.monitoring.yml up -d

# 또는 로컬 바이너리로 시작
./scripts/start_monitoring.sh

# 접속:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3001 (admin/admin)
# - Metrics: http://localhost:8000/metrics
```

> 📊 모니터링 상세 가이드: [MONITORING_ARCHITECTURE.md](docs/MONITORING_ARCHITECTURE.md)

---

## 현재 구현 범위 (MVP)
- ✅ **상품 선택 모드** (URL 크롤링 → 상품 선택으로 전환)
  - reg_factor_v4.csv 기반 상품 목록 (10개 제품, 10개 카테고리)
  - Category 매핑 (earbuds→earphone, coffee_machine, induction 등)
  - FactorAnalyzer를 통한 리뷰-Factor 매칭
  - JSON 파일 자동 로드 (backend/data/review/*.json)
- ✅ 리뷰 정규화 및 factor 매칭
- ✅ REG 기반 factor 스코어링 (category, display_name 포함)
- ✅ POS / NEG / MIX / NEU 리뷰 분류 및 라벨링
- ✅ 3~5턴 대화 기반 factor 수렴
- ✅ 카테고리별 맞춤 fallback 질문 (10개 카테고리)
- ✅ 대화 히스토리 추적
- ✅ LLM API용 컨텍스트 (JSON) 생성
- ✅ LLM 프롬프트 (TXT) 자동 생성
- ✅ 타임스탬프 기반 파일 저장
- ✅ Safety rules 포함
- ✅ Vue.js 챗봇 UI (모바일 반응형)
- ✅ **세션 영속성 (JSON 파일 기반)**
  - 서버 재시작 후에도 세션 복원
  - 리뷰 캐싱으로 빠른 재분석
  - Term 변환 (6가지 한글 형태소 규칙)
- ✅ **Prometheus + Grafana 모니터링 스택**
  - HTTP 요청 메트릭 (latency, throughput, error rate)
  - 대화 세션/턴 추적
  - LLM API 성능 모니터링
  - 파이프라인 단계별 latency 측정
- ✅ **CORS 다중 포트 지원** (5173, 5174, 3000)

---

## 향후 확장
- 카테고리별 REG 세트 확장
- 벡터 기반 유사 리뷰 제거 필터 사용(비슷란 리뷰를 제거하는 용도)
- 프런트엔드 UI 연결
- 실제 구매 링크 연동
