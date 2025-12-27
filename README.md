# ReviewLens
### 후회를 줄이기 위한 대화형 리뷰 분석 챗봇

---

## 한 줄 요약
**ReviewLens는 리뷰를 요약하지 않는다.**  
대신, 리뷰 속 *후회 요인(Regret Factor)*을 기준으로  
**사용자와 3~5턴 대화를 통해 판단에 필요한 근거만 추출**한다.

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
리뷰 CSV
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

#### Backend Pipeline (Modular Architecture)
```
backend/
├── pipeline/
│   ├── ingest.py          # 리뷰 정규화 및 중복 제거
│   ├── reg_store.py       # REG Factor/Question CSV 로딩
│   │                      # Factor: category, display_name 포함
│   ├── sensor.py          # Factor scoring & review classification (POS/NEG/MIX/NEU)
│   ├── retrieval.py       # Evidence review selection
│   ├── dialogue.py        # 3-5 turn conversation engine
│   │                      # - dialogue_history 추적
│   │                      # - calculation_info 생성 (프론트엔드용)
│   │                      # - LLM 프롬프트 생성
│   │                      # - 타임스탬프 기반 파일 저장
│   └── prompt_builder.py  # LLM context JSON generation
├── app/
│   ├── main.py           # FastAPI application
│   ├── api/
│   │   └── routes_chat.py  # Chat session API endpoints
│   │       # POST /api/chat/start - 세션 시작
│   │       # POST /api/chat/message - 메시지 전송
│   ├── services/
│   │   └── session_store.py  # Session management (in-memory)
│   └── schemas/          # Request/Response models
├── data/
│   ├── factor/
│   │   ├── reg_factor.csv    # category, display_name 포함
│   │   └── reg_question.csv
│   └── review/
│       └── review_sample.csv
├── out/                  # 생성 파일 디렉터리
│   ├── llm_context_demo.{timestamp}.json  # LLM API용 (calculation_info 제외)
│   └── prompt_demo.{timestamp}.txt        # LLM 프롬프트
└── regret_bot.py         # CLI tool for testing
```

#### Frontend (Vue.js + Vite)
```
frontend/
├── src/
│   ├── components/
│   │   └── ChatBot.vue       # 챗봇 UI 컴포넌트
│   │       # - 대화 메시지 표시
│   │       # - 후회 요인 뱃지 실시간 표시
│   │       # - 분석 결과 섹션 (계산 공식 포함)
│   │       # - 모바일 반응형 디자인
│   ├── api.js               # API 호출 wrapper
│   ├── config.js            # API 베이스 URL
│   └── main.js
├── index.html
├── package.json
└── vite.config.js
```

**주요 기능:**
- ✅ 3-5턴 대화형 UI
- ✅ 실시간 후회 요인 뱃지 표시
- ✅ 분석 완료 시 계산 공식 및 누적 점수 표시
- ✅ 모바일/태블릿 반응형 디자인
- ✅ 대화 히스토리 유지 (스크롤 가능)

#### Test Suite
- ✅ **tests/test_demo_scenario.py**: 3-5 turn dialogue pytest PASSED
- ✅ **tests/test_demo_5turns_full.py**: DEMO_SCENARIO_5TURNS.md 시나리오 검증
- 대화형 시나리오 검증 완료

### 🚧 진행 중
- LLM API 통합 (OpenAI/Claude)
- 데이터베이스 연동 (Redis/PostgreSQL)

### 📋 계획 중
- LLM Integration (OpenAI/Claude API)
- Production deployment
- Database persistence (PostgreSQL/Redis)

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

---

## 현재 구현 범위 (MVP)
- ✅ 리뷰 CSV 입력 및 정규화
- ✅ REG 기반 factor 스코어링 (category, display_name 포함)
- ✅ POS / NEG / MIX / NEU 리뷰 분류 및 라벨링
- ✅ 3~5턴 대화 기반 factor 수렴
- ✅ 대화 히스토리 추적
- ✅ LLM API용 컨텍스트 (JSON) 생성
- ✅ LLM 프롬프트 (TXT) 자동 생성
- ✅ 타임스탬프 기반 파일 저장
- ✅ Safety rules 포함
- ✅ Vue.js 챗봇 UI (모바일 반응형)

---

## 향후 확장
- 카테고리별 REG 세트 확장
- 벡터 기반 유사 리뷰 제거 필터 사용(비슷란 리뷰를 제거하는 용도)
- 프런트엔드 UI 연결
- 실제 구매 링크 연동
