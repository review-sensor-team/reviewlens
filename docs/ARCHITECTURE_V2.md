# ReviewLens V2 Architecture

> **Last Updated**: 2026-01-17  
> **Version**: 2.0.0  
> **Architecture Style**: Clean Architecture

## 목차

- [개요](#개요)
- [Clean Architecture 구조](#clean-architecture-구조)
- [API 엔드포인트](#api-엔드포인트)
- [대화 플로우](#대화-플로우)
- [세션 관리](#세션-관리)
- [LLM 통합](#llm-통합)
- [마이그레이션 가이드](#마이그레이션-가이드)

---

## 개요

### V2 주요 변경사항

| 항목 | V1 | V2 |
|------|----|----|
| 아키텍처 | Modular | Clean Architecture |
| API 버전 | `/api/chat/*` | `/api/v2/reviews/*` |
| 대화 플로우 | 단일 메시지 기반 | 3-5턴 질문-답변 |
| 중복 코드 | 332KB 분산 | Legacy 폴더로 이동 |
| 세션 관리 | 파일 기반 | In-memory cache |
| LLM 호출 | 매 턴마다 | 수렴 시 1회 |

### 디렉토리 구조

```
backend/
├── app/                          # Application Layer
│   ├── main.py                  # FastAPI 앱 (V2 only)
│   ├── core/
│   │   ├── settings.py          # 환경 설정
│   │   └── logging.py
│   ├── api/
│   │   └── routers/
│   │       ├── health.py        # /health, /metrics
│   │       └── review.py        # /api/v2/reviews/*
│   ├── domain/                  # Domain Layer
│   │   ├── dialogue/
│   │   │   └── session.py       # DialogueSession
│   │   ├── reg/
│   │   │   ├── store.py         # CSV 로딩
│   │   │   └── matching.py      # 질문-팩터 매칭
│   │   └── review/
│   │       ├── normalize.py     # 리뷰 정규화
│   │       ├── scoring.py       # Factor 점수 계산
│   │       └── retrieval.py     # 증거 리뷰 추출
│   ├── infra/                   # Infrastructure Layer
│   │   ├── observability/
│   │   │   └── metrics.py       # Prometheus 메트릭
│   │   └── session/
│   │       └── store.py         # 세션 저장소
│   └── services/
│       └── review_loader.py     # 리뷰 파일 로더
├── llm/                         # LLM 통합 (독립 모듈)
│   ├── llm_factory.py
│   ├── llm_openai.py
│   ├── llm_claude.py
│   └── llm_gemini.py
├── data/
│   ├── factor/
│   │   └── reg_factor_v4.csv    # 10개 상품, 100개 factors
│   ├── question/
│   │   └── reg_question_v6.csv  # 100개 질문
│   └── review/
│       └── reviews_*.json       # 사전 수집 리뷰
└── legacy/                      # V1 레거시 (332KB)
    ├── dialogue_old/
    ├── core_old/
    ├── collector_old/
    └── session_old/
```

---

## Clean Architecture 구조

### 의존성 방향

```
API Layer (FastAPI)
    ↓ depends on
Domain Layer (Pure Python)
    ↓ depends on
Infrastructure Layer (External)
```

### 계층별 책임

#### 1. Domain Layer (`backend/app/domain/`)

**순수 비즈니스 로직** - FastAPI, 외부 라이브러리 독립

- **dialogue/session.py**: 3-5턴 대화 엔진
  - `generate_analysis()`: 질문 선택 및 수렴 판단
  - `_select_next_question()`: 다음 질문 선택
  - `_generate_llm_summary()`: LLM 분석 호출

- **review/scoring.py**: Factor 점수 계산
  - `compute_review_factor_scores()`: Anchor term 매칭
  - `score_text_against_factor()`: 텍스트-Factor 점수

- **review/retrieval.py**: 증거 리뷰 추출
  - `retrieve_evidence_reviews()`: POS/NEG/MIX 분류
  - `classify_text_label()`: 라벨링

- **reg/store.py**: CSV 데이터 로딩
  - `load_csvs()`: Factor/Question CSV 로드
  - `parse_factors()`: Factor 객체 생성

#### 2. API Layer (`backend/app/api/routers/`)

**HTTP 엔드포인트** - Request/Response 변환

- **review.py**: V2 리뷰 분석 API
  ```python
  POST   /api/v2/reviews/analyze-product      # 상품 분석 시작
  POST   /api/v2/reviews/answer-question      # 질문 답변
  GET    /api/v2/reviews/factor-reviews       # Factor별 리뷰
  GET    /api/v2/reviews/products             # 상품 목록
  GET    /api/v2/reviews/config               # 앱 설정
  ```

#### 3. Infrastructure Layer (`backend/app/infra/`)

**외부 시스템 연동**

- **observability/metrics.py**: Prometheus 메트릭
  - `dialogue_sessions_total`
  - `http_requests_total`
  - `llm_calls_total`

- **session/store.py**: 세션 저장 (In-memory)
  ```python
  _session_cache = {
      session_id: {
          "scored_df": DataFrame,
          "normalized_df": DataFrame,
          "factors": List[Factor],
          "top_factors": List[Tuple[str, float]],
          "category": str,
          "product_name": str,
          "question_history": List[Dict],
          "asked_fallback_questions": List[str],
          "current_question": Dict
      }
  }
  ```

---

## API 엔드포인트

### 1. 상품 분석 시작

```http
POST /api/v2/reviews/analyze-product?product_name={name}
```

**응답:**
```json
{
  "session_id": "session-coffee_machine-12345",
  "top_factors": [
    {
      "factor_key": "price_regret",
      "display_name": "가격 후회",
      "score": 15.2,
      "review_count": 8
    }
  ],
  "first_question": {
    "question_id": "1003",
    "question_text": "최저가 비교를 꼼꼼히 하시는 편인가요?",
    "answer_type": "choice",
    "choices": ["매우 꼼꼼함", "꼼꼼히 비교함", "대충 비교함"],
    "factor_key": "price_regret"
  }
}
```

### 2. 질문 답변

```http
POST /api/v2/reviews/answer-question/{session_id}
Content-Type: application/json

{
  "answer": "꼼꼼히 비교함",
  "question_id": "1003",
  "factor_key": "price_regret"
}
```

**응답 (수렴 전):**
```json
{
  "next_question": {
    "question_id": "5007",
    "question_text": "이 가격대에 어느 정도 성능을 기대하시나요?",
    "choices": ["완벽해야 함", "적당하면 됨", "가격 감안함"],
    "factor_key": "price_regret"
  },
  "related_reviews": [],
  "review_message": "",
  "is_converged": false,
  "turn_count": 2
}
```

**응답 (수렴 후, turn_count >= 3):**
```json
{
  "is_converged": true,
  "turn_count": 3,
  "analysis": {
    "product_name": "네스프레소 버츄오플러스",
    "category": "coffee_machine",
    "total_reviews": 40,
    "top_factors": [...],
    "llm_summary": "{\"overall_sentiment\":\"...\",\"key_concerns\":[...]}",
    "evidence_reviews": [...]
  }
}
```

### 3. Factor별 리뷰 조회

```http
GET /api/v2/reviews/factor-reviews/{session_id}/{factor_key}?limit=5
```

---

## 대화 플로우

### 3-5턴 수렴 알고리즘

```python
# backend/app/api/routers/review.py

MIN_TURNS = 3  # 최소 질문 답변 횟수

def answer_question(session_id, request):
    # 1. 질문 히스토리에 추가
    session_data["question_history"].append({
        "question_id": request.question_id,
        "question_text": question_text,
        "answer": request.answer,
        "factor_key": request.factor_key
    })
    
    turn_count = len(session_data["question_history"])
    
    # 2. 수렴 체크
    is_converged = turn_count >= MIN_TURNS
    
    if not is_converged:
        # 3. 다음 질문 선택
        next_question = select_next_question(
            session_data, 
            request.factor_key
        )
        return {
            "next_question": next_question,
            "is_converged": False,
            "turn_count": turn_count
        }
    else:
        # 4. LLM 분석 실행
        dialogue_session = DialogueSession(...)
        analysis = dialogue_session.generate_analysis(
            top_factors=session_data["top_factors"][:3],
            turn_count=turn_count
        )
        return {
            "is_converged": True,
            "analysis": analysis
        }
```

### 중복 질문 필터링

```python
# backend/app/api/routers/review.py

# 이미 물어본 질문 ID와 텍스트 추적
asked_ids = {q["question_id"] for q in question_history}
asked_texts = {q["question_text"] for q in question_history}

# ID와 텍스트 둘 다 체크 (CSV에 중복 텍스트 있을 수 있음)
related_questions = all_questions[
    (~all_questions['question_id'].isin(asked_ids)) &
    (~all_questions['question_text'].isin(asked_texts))
]
```

### Fallback 질문

카테고리별 질문이 소진되면 일반적인 질문 사용:

```python
category_questions = {
    'coffee_machine': [
        "하루에 커피를 몇 잔 정도 드시나요?",
        "어떤 종류의 커피를 선호하시나요?",
        "커피머신 구매 시 가장 중요한 요소는?"
    ],
    'mattress': [
        "평소 어떤 자세로 주로 주무시나요?",
        "현재 매트리스에서 가장 불편한 점은?",
        "매트리스 구매 시 중요 요소는?"
    ],
    # ... 10개 카테고리
}
```

---

## 세션 관리

### In-Memory Cache 구조

```python
# backend/app/api/routers/review.py

_session_cache = {}  # Global cache

def create_session(product_name):
    session_id = f"session-{category}-{random_id}"
    
    _session_cache[session_id] = {
        "scored_df": scored_df,           # Factor 점수
        "normalized_df": normalized_df,   # 정규화된 리뷰
        "factors": factors,               # Factor 객체 리스트
        "top_factors": top_factors,       # Top 5 factors
        "category": category,
        "product_name": product_name,
        "question_history": [],           # 질문-답변 기록
        "asked_fallback_questions": [],   # Fallback 질문 기록
        "current_question": {}            # 현재 질문 (다음 답변 시 사용)
    }
    
    return session_id
```

### 세션 라이프사이클

1. **생성**: `POST /api/v2/reviews/analyze-product`
2. **사용**: `POST /api/v2/reviews/answer-question` (3-5회)
3. **종료**: 수렴 후 자동 종료 (메모리에서 유지, 명시적 삭제 없음)

---

## LLM 통합

### 호출 시점

- **V1**: 매 턴마다 LLM 호출 (비효율적)
- **V2**: 3턴 수렴 후 1회만 호출 (효율적)

### LLM 프롬프트 구조

```python
# backend/app/domain/dialogue/session.py

def _generate_llm_summary(top_factors, evidence_reviews):
    context = {
        "product_name": "네스프레소 버츄오플러스",
        "category": "커피머신",
        "total_reviews": 40,
        "top_factors": [
            {
                "factor_key": "price_regret",
                "display_name": "가격 후회",
                "pos_count": 2,
                "neg_count": 8,
                "score": 15.2
            }
        ],
        "evidence_reviews": [
            {
                "review_id": "rev_123",
                "text": "가격 대비 성능이 아쉬워요",
                "rating": 3,
                "label": "NEG"
            }
        ]
    }
    
    # LLM 프롬프트
    prompt = f"""
    제품: {context['product_name']}
    총 리뷰: {context['total_reviews']}개
    
    주요 후회 요인:
    {format_factors(context['top_factors'])}
    
    증거 리뷰:
    {format_reviews(context['evidence_reviews'])}
    
    다음 형식으로 분석해주세요:
    {{
      "overall_sentiment": "긍정/부정/중립",
      "key_concerns": ["concern1", "concern2"],
      "recommendations": ["rec1", "rec2"]
    }}
    """
    
    return llm_client.generate(prompt)
```

### 지원 LLM

- **OpenAI**: `gpt-4o-mini` (기본값)
- **Claude**: `claude-3-5-sonnet-20241022`
- **Gemini**: `gemini-2.0-flash-exp`

설정: `.env` 파일에서 `LLM_PROVIDER` 지정

---

## 마이그레이션 가이드

### V1 → V2 전환

1. **API 엔드포인트 변경**
   ```diff
   - POST /api/chat/analyze-product
   + POST /api/v2/reviews/analyze-product
   
   - POST /api/chat/message
   + POST /api/v2/reviews/answer-question
   ```

2. **세션 관리**
   ```diff
   - 파일 기반 (.cache/ 디렉토리)
   + In-memory cache (메모리)
   ```

3. **대화 플로우**
   ```diff
   - 단일 메시지 전송
   + 질문-답변 3-5턴
   ```

4. **Import 경로**
   ```diff
   - from backend.dialogue.dialogue import DialogueSession
   + from backend.app.domain.dialogue.session import DialogueSession
   
   - from backend.dialogue.sensor import compute_review_factor_scores
   + from backend.app.domain.review.scoring import compute_review_factor_scores
   ```

### 레거시 코드 위치

V1 코드는 `backend/legacy/`에 보관:
- `dialogue_old/` (184KB)
- `core_old/` (28KB)
- `collector_old/` (52KB)
- `session_old/` (8KB)

---

## 성능 최적화

### 병목 지점

1. **CSV 로딩**: 매 요청마다 로드 → 캐싱 추천
2. **리뷰 정규화**: 100개 리뷰 × 정규화 시간
3. **Factor 점수 계산**: O(n×m) - n개 리뷰 × m개 factors

### 개선 방안

```python
# CSV 캐싱 (현재는 매번 로드)
import functools

@functools.lru_cache(maxsize=1)
def load_csvs_cached(data_dir):
    return load_csvs(data_dir)
```

---

## 다음 단계

- [ ] CSV 캐싱 구현
- [ ] 세션 TTL 추가 (현재 무제한)
- [ ] 질문 우선순위 알고리즘 개선
- [ ] 다중 세션 동시 처리 테스트
- [ ] Redis 세션 저장소 연동

---

**작성자**: ReviewLens Team  
**문서 버전**: 2.0.0  
**최종 업데이트**: 2026-01-17
