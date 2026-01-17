# ReviewLens 인터페이스 명세서

각 개발 영역 간 주고받는 데이터 인터페이스를 정의합니다.

## 목차

- [1. 프론트엔드 ↔ 백엔드 API](#1-프론트엔드--백엔드-api)
- [2. 백엔드 API ↔ Dialogue Engine](#2-백엔드-api--dialogue-engine)
- [3. Dialogue Engine ↔ LLM Services](#3-dialogue-engine--llm-services)
- [4. Dialogue Engine ↔ Retrieval Pipeline](#4-dialogue-engine--retrieval-pipeline)
- [5. 크롤러 ↔ 백엔드](#5-크롤러--백엔드)
- [6. 백엔드 ↔ Monitoring](#6-백엔드--monitoring)

---

## 1. 프론트엔드 ↔ 백엔드 API

### 1.1 리뷰 수집 (POST /api/collect-reviews)

**요청 (Request)**:
```typescript
interface CollectReviewsRequest {
  product_url: string;           // 네이버 스마트스토어 상품 URL
  max_reviews?: number;          // 최대 수집 리뷰 수 (기본값: 100)
  sort_by_low_rating?: boolean;  // 낮은 평점 우선 정렬 (기본값: true)
  category?: string;             // 카테고리 강제 지정 (선택사항)
}
```

**응답 (Response)**:
```typescript
interface CollectReviewsResponse {
  success: boolean;
  message: string;
  session_id?: string;           // 생성된 세션 ID
  reviews: Review[];
  total_count: number;
  
  // 카테고리 감지 정보
  detected_category?: string;    // 감지된 카테고리 키
  category_confidence: 'high' | 'low' | 'failed';
  available_categories?: Array<{
    key: string;                 // 예: 'appliance_induction'
    name: string;                // 예: '인덕션'
  }>;
  
  // 상품 정보
  product_name?: string;         // 페이지 제목에서 추출
}

interface Review {
  review_id: number;
  rating?: number;               // 1-5
  text: string;
  created_at: string;            // ISO 8601 format
  factor_matches?: FactorMatch[];
}

interface FactorMatch {
  factor_id?: number;            // Factor 고유 ID
  factor_key: string;            // Factor 키
  display_name: string;          // Factor 표시명
  description?: string;          // Factor 설명
  sentences: string[];           // 매칭된 문장들
  matched_terms: string[];       // 매칭된 키워드들
}
```

**에러 응답**:
```typescript
interface ErrorResponse {
  detail: string;                // 에러 메시지
}
```

**HTTP 상태 코드**:
- `200 OK`: 성공
- `400 Bad Request`: 잘못된 URL 형식
- `500 Internal Server Error`: 크롤링 실패

---

### 1.2 세션 시작 (POST /api/chat/start)

**요청**:
```typescript
interface SessionStartRequest {
  category: string;              // 카테고리 키 (예: 'robot_cleaner')
}
```

**응답**:
```typescript
interface SessionStartResponse {
  session_id: string;            // 생성된 세션 ID (UUID)
  message: string;               // 환영 메시지
}
```

**에러**:
- `400 Bad Request`: 존재하지 않는 카테고리
- `500 Internal Server Error`: 세션 생성 실패

---

### 1.3 대화 메시지 (POST /api/chat/message)

**요청**:
```typescript
interface ChatRequest {
  session_id: string;            // 세션 ID
  message: string;               // 사용자 메시지
}
```

**응답**:
```typescript
interface ChatResponse {
  session_id: string;
  bot_message?: string;          // 봇 응답 메시지
  is_final: boolean;             // 대화 종료 여부
  top_factors: FactorScore[];
  
  // LLM 요약 (is_final=true일 때만)
  llm_context?: {
    top_factors_summary: Array<{
      factor_key: string;
      display_name: string;
      score: number;
      description: string;
    }>;
    overall_summary: string;
    recommendations: string[];
    evidence_stats: {
      negative: number;
      mixed: number;
      positive: number;
    };
  };
  
  // 관련 리뷰 정보
  related_reviews?: {
    [factor_key: string]: {
      count: number;
      examples: string[];        // 최대 3개
    };
  };
  
  // 질문 정보 (is_final=false일 때)
  question_id?: string;
  answer_type?: 'no_choice' | 'single_choice';
  choices?: string;              // '예|아니오|잘 모르겠음'
}

interface FactorScore {
  factor_key: string;
  factor_id?: number;
  score: number;
}
```

**에러**:
- `404 Not Found`: 세션 ID가 존재하지 않음
- `400 Bad Request`: 잘못된 요청 형식
- `500 Internal Server Error`: 처리 중 오류

---

### 1.4 메트릭 노출 (GET /metrics)

**요청**: 없음

**응답**: Prometheus text format
```text
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",endpoint="/api/chat/message",status_code="200"} 42

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="POST",endpoint="/api/chat/message",le="0.1"} 10
...
```

---

## 2. 백엔드 API ↔ Dialogue Engine

### 2.1 DialogueSession 초기화

**Python 인터페이스**:
```python
from backend.dialogue.dialogue import DialogueSession

# 생성
session = DialogueSession(
    category: str,              # 카테고리 키
    data_dir: str,              # 데이터 디렉토리 경로
    reviews_df: pd.DataFrame    # 리뷰 DataFrame
)

# reviews_df 구조
# columns: ['review_id', 'rating', 'text', 'created_at', ...]
# dtypes: review_id (int), rating (int), text (str), created_at (str)
```

**DialogueSession 속성**:
```python
session.session_id: str                    # UUID
session.category: str                      # 카테고리 키
session.turn_count: int                    # 현재 턴 수
session.factors: List[Factor]              # 로드된 Factor 리스트
session.cumulative_scores: Dict[str, float]  # 누적 점수
session.prev_top3: Set[str]                # 이전 Top 3 factor keys
session.stability_hits: int                # 수렴 카운터
```

---

### 2.2 대화 턴 처리 (step)

**함수 시그니처**:
```python
def step(user_message: str) -> BotTurn
```

**BotTurn 구조**:
```python
@dataclass
class BotTurn:
    question_text: Optional[str]           # 다음 질문
    top_factors: List[Tuple[str, float]]   # [(factor_key, score), ...]
    is_final: bool                         # 대화 완료 여부
    llm_context: Optional[Dict]            # LLM 요약 (is_final=True일 때)
    question_id: Optional[str]             # 질문 ID
    answer_type: Optional[str]             # 'no_choice' | 'single_choice'
    choices: Optional[str]                 # 선택지
```

**처리 흐름**:
1. 메시지 정규화 (`normalize(user_message)`)
2. Factor 매칭 및 점수 누적
3. Top 3 추출
4. 수렴 체크 (Jaccard similarity > 0.7, stability_hits >= 3)
5. 수렴 시: `_finalize()` 호출
6. 미수렴 시: 다음 질문 생성

---

### 2.3 최종 분석 (_finalize)

**함수 시그니처**:
```python
def _finalize(top_factors: List[Tuple[str, float]]) -> BotTurn
```

**내부 처리**:
1. `compute_review_factor_scores()` - Factor 점수 계산
2. `retrieve_evidence_reviews()` - Evidence 수집
3. `_generate_llm_summary()` - LLM 요약 생성

**llm_context 구조**:
```python
{
    "top_factors_summary": [
        {
            "factor_key": str,
            "display_name": str,
            "score": float,
            "description": str
        }
    ],
    "overall_summary": str,         # 전체 요약
    "recommendations": [str],        # 체크포인트 리스트
    "evidence_stats": {
        "negative": int,
        "mixed": int,
        "positive": int
    }
}
```

---

## 3. Dialogue Engine ↔ LLM Services

### 3.1 LLM 클라이언트 생성 (Factory Pattern)

**Python 인터페이스**:
```python
from backend.services.llm_factory import LLMFactory

client = LLMFactory.create_client(
    provider: str,                 # 'openai' | 'gemini' | 'claude'
    api_key: Optional[str] = None,
    model: Optional[str] = None
)
```

---

### 3.2 요약 생성 (generate_summary)

**함수 시그니처**:
```python
def generate_summary(
    top_factors: List[Tuple[str, float]],
    evidence_reviews: Dict[str, List[Dict]],
    product_name: str,
    category_name: str,
    total_turns: int,
    conversation_history: Optional[List[str]] = None
) -> str
```

**top_factors 구조**:
```python
[
    ("noise", 4.5),
    ("suction", 3.2),
    ("battery", 2.8)
]
```

**evidence_reviews 구조**:
```python
{
    "noise": [
        {
            "text": str,
            "rating": int,
            "label": "NEG" | "MIX" | "POS",
            "score": float
        },
        ...
    ],
    "suction": [...],
    ...
}
```

**반환값**:
```python
# 성공 시
"""
🔍 핵심 후회 요인 분석 (Top 5)

1. 소음 문제 (점수: 4.5)
   - 설명...

2. 흡입력 (점수: 3.2)
   - 설명...

✅ 구매 전 체크포인트:
- 체크포인트 1
- 체크포인트 2

💡 한 줄 조언: ...
"""

# 실패 시 (fallback)
"분석이 완료되었습니다. 상위 요인은 {factor1}, {factor2}, {factor3}입니다."
```

**에러 처리**:
- API 호출 실패 시: fallback 메시지 반환
- Timeout: 30초 후 fallback
- 메트릭 기록: `llm_calls_total{provider, status='error'}`

---

## 4. Dialogue Engine ↔ Retrieval Pipeline

### 4.1 리뷰 스코어링 (compute_review_factor_scores)

**함수 시그니처**:
```python
def compute_review_factor_scores(
    df: pd.DataFrame,
    factors: List[Factor],
    compute_top_per_review: bool = True
) -> Tuple[pd.DataFrame, Dict[str, int]]
```

**입력 DataFrame 구조**:
```python
# columns: ['review_id', 'rating', 'text', 'created_at']
# 예시 행:
{
    'review_id': 12345,
    'rating': 3,
    'text': '소음이 너무 크고 시끄러워요',
    'created_at': '2026-01-01T12:00:00'
}
```

**출력 DataFrame 구조**:
```python
# 입력 컬럼 + 추가 컬럼
columns = [
    'review_id', 'rating', 'text', 'created_at',
    'score_f1',           # Factor ID 1 점수
    'score_f2',           # Factor ID 2 점수
    'score_noise',        # Factor key 점수 (하위 호환)
    'has_neg_noise',      # negation 플래그 (bool)
    'top_factors',        # List[str] - Top 3 factor keys
    'top_factor_scores'   # List[Tuple[str, float]]
]
```

**factor_counts 구조**:
```python
{
    "noise": 45,          # 'noise' factor가 매칭된 리뷰 수
    "suction": 32,
    "battery": 28
}
```

---

### 4.2 증거 리뷰 검색 (retrieve_evidence_reviews)

**함수 시그니처**:
```python
def retrieve_evidence_reviews(
    scored_df: pd.DataFrame,
    top_factors: List[Tuple[str, float]],
    max_per_factor: int = 6
) -> Dict[str, List[Dict]]
```

**top_factors 입력**:
```python
[
    ("noise", 4.5),
    ("suction", 3.2),
    ("battery", 2.8),
    ("cleaning_quality", 1.9),
    ("design", 1.5)
]
```

**반환값 구조**:
```python
{
    "noise": [
        {
            "text": "소음이 너무 커서...",
            "rating": 2,
            "label": "NEG",      # NEG | MIX | POS
            "score": 4.2,
            "review_id": 12345,
            "created_at": "2026-01-01T12:00:00"
        },
        # NEG: 3개, MIX: 2개, POS: 1개 (Rank 0 quota)
    ],
    "suction": [
        # NEG: 2개, MIX: 2개, POS: 1개 (Rank 1 quota)
    ],
    ...
}
```

**Quota 시스템**:
- Rank 0 (Top 1): NEG 3개, MIX 2개, POS 1개
- Rank 1 (Top 2): NEG 2개, MIX 2개, POS 1개
- Rank 2+ (Top 3-5): NEG 2개, MIX 2개, POS 1개

**Label 분류 로직**:
```python
# score >= 2.0 and rating <= 3 → NEG
# score >= 1.0 and rating == 4 → MIX
# score >= 1.0 and rating == 5 → POS
```

---

## 5. 크롤러 ↔ 백엔드

### 5.1 SmartStoreCollector 인터페이스

**Python 인터페이스**:
```python
from backend.app.collector import SmartStoreCollector

collector = SmartStoreCollector(
    headless: bool = True,
    timeout: int = 30
)

result = collector.collect_reviews(
    product_url: str,
    max_reviews: int = 100,
    sort_by_low_rating: bool = True
)
```

**반환값 구조**:
```python
{
    "success": bool,
    "product_name": str,          # 페이지 제목
    "total_collected": int,
    "reviews": [
        {
            "review_id": int,     # 고유 ID (해시 기반)
            "rating": int,        # 1-5
            "text": str,
            "created_at": str,    # ISO 8601
            "reviewer": str       # 작성자 (선택사항)
        },
        ...
    ],
    "error": Optional[str]        # 에러 메시지
}
```

**에러 타입**:
- `InvalidURLError`: 잘못된 URL 형식
- `PageLoadError`: 페이지 로드 실패
- `NoReviewsFoundError`: 리뷰가 없음
- `SeleniumError`: WebDriver 오류

---

### 5.2 FactorAnalyzer 인터페이스

**Python 인터페이스**:
```python
from backend.app.collector.factor_analyzer import FactorAnalyzer

analyzer = FactorAnalyzer()

matches = analyzer.analyze_reviews(
    reviews: List[Dict],
    factors: List[Factor]
) -> List[Dict]
```

**입력 reviews**:
```python
[
    {
        "review_id": 12345,
        "text": "소음이 너무 크고...",
        "rating": 3
    },
    ...
]
```

**출력 구조**:
```python
[
    {
        "review_id": 12345,
        "factor_matches": [
            {
                "factor_id": 1,
                "factor_key": "noise",
                "display_name": "소음",
                "description": "소음이 심해서 아쉬운 요인",
                "sentences": ["소음이 너무 크고"],
                "matched_terms": ["소음", "크"]
            }
        ]
    },
    ...
]
```

---

## 6. 백엔드 ↔ Monitoring

### 6.1 Prometheus 메트릭 노출

**Endpoint**: `GET /metrics`

**메트릭 타입**:

#### Counter (누적값)
```python
http_requests_total{method, endpoint, status_code}
dialogue_sessions_total{category}
dialogue_turns_total{category}
dialogue_completions_total
llm_calls_total{provider, status}
errors_total{error_type}
```

#### Histogram (분포)
```python
http_request_duration_seconds{method, endpoint}
retrieval_duration_seconds{category}
scoring_duration_seconds{category}
llm_duration_seconds{provider}
evidence_count
```

---

### 6.2 메트릭 계측 (Instrumentation)

**HTTP 미들웨어**:
```python
from backend.core.metrics import http_requests_total, http_request_duration_seconds

# 자동 기록
http_requests_total.labels(
    method="POST",
    endpoint="/api/chat/message",
    status_code=200
).inc()

http_request_duration_seconds.labels(
    method="POST",
    endpoint="/api/chat/message"
).observe(0.123)  # 초 단위
```

**Pipeline 계측**:
```python
from backend.core.metrics import Timer, retrieval_duration_seconds

with Timer(retrieval_duration_seconds, {'category': 'robot_cleaner'}):
    evidence = retrieve_evidence_reviews(...)
```

**LLM 계측**:
```python
from backend.core.metrics import llm_calls_total, llm_duration_seconds, Timer

with Timer(llm_duration_seconds, {'provider': 'openai'}):
    summary = llm_client.generate_summary(...)

# 성공 시
llm_calls_total.labels(provider='openai', status='success').inc()

# 실패 시
llm_calls_total.labels(provider='openai', status='error').inc()
llm_calls_total.labels(provider='openai', status='fallback').inc()
```

---

### 6.3 Grafana 쿼리 (PromQL)

**HTTP Latency (p50/p95/p99)**:
```promql
# p50
histogram_quantile(0.5, rate(http_request_duration_seconds_bucket[5m]))

# p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# p99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

**에러율**:
```promql
# 5xx 에러율 (%)
sum(rate(http_requests_total{status_code=~"5.."}[5m])) 
/ 
sum(rate(http_requests_total[5m])) 
* 100
```

**LLM 성공률**:
```promql
# LLM API 성공률 (%)
sum(rate(llm_calls_total{status="success"}[5m])) 
/ 
sum(rate(llm_calls_total[5m])) 
* 100
```

---

## 부록: Factor 데이터 구조

### Factor 클래스

**Python 정의**:
```python
@dataclass
class Factor:
    factor_id: int                    # 고유 ID
    factor_key: str                   # Factor 키 (예: 'noise')
    category: str                     # 카테고리 키 (예: 'robot_cleaner')
    category_name: str                # 카테고리 표시명 (예: '로봇청소기')
    display_name: str                 # Factor 표시명 (예: '소음')
    description: str                  # Factor 설명
    anchor_terms: List[str]           # 핵심 키워드
    context_terms: List[str]          # 연관 키워드
    negation_terms: List[str]         # 반전 표현
    weight: float                     # 가중치 (1.0-3.0)
```

**CSV 형식** (`data/factor/reg_factor.csv`):
```csv
factor_id,factor_key,category,category_name,display_name,description,anchor_terms,context_terms,negation_terms,weight
1,noise,robot_cleaner,로봇청소기,소음,소음이 심해서 아쉬운 요인,소음|시끄러|떠들,조용|정숙,조용하|괜찮,1.5
2,suction,robot_cleaner,로봇청소기,흡입력,흡입력이 약해서 아쉬운 요인,흡입|빨아들,청소력|파워,약하|부족,2.0
```

**점수 계산 로직**:
```python
score = 0.0

# anchor_terms 매칭: +1.0
if any(term in normalized_text for term in factor.anchor_terms):
    score += 1.0

# context_terms 매칭: +0.3
if any(term in normalized_text for term in factor.context_terms):
    score += 0.3

# negation_terms 매칭: 점수 반영 X, has_neg 플래그만 설정
has_negation = any(term in normalized_text for term in factor.negation_terms)

# weight 곱셈
weighted_score = score * factor.weight

# rating multiplier: 1.0 + (5 - rating) * 0.2
# rating=1 → 1.8x, rating=5 → 1.0x
final_score = weighted_score * rating_multiplier
```

---

## 부록: Question 데이터 구조

### Question 클래스

**Python 정의**:
```python
@dataclass
class Question:
    question_id: int                  # 고유 ID
    factor_id: int                    # 연결된 Factor ID
    factor_key: str                   # Factor 키 (참고용)
    question_text: str                # 질문 텍스트
    answer_type: str                  # 'no_choice' | 'single_choice'
    choices: str                      # 선택지 ('|'로 구분)
    next_factor_hint: str             # 다음 Factor 힌트
```

**CSV 형식** (`data/question/reg_question.csv`):
```csv
question_id,factor_id,factor_key,question_text,answer_type,choices,next_factor_hint
1001,1,water_control,물 양을 직접 조절하고 싶으신가요?,no_choice,,
1002,1,water_control,커피 시 물 관리가 중요한가요?,single_choice,매우 중요|보통|상관없음,
1003,2,coffee_delivery,배송에 대해 걱정되시나요?,no_choice,,
```

**파싱 및 로딩**:
```python
from backend.dialogue.reg_store import load_csvs, parse_questions

# CSV 로드
_, _, questions_df = load_csvs(data_dir)

# Question 객체 리스트로 변환
questions = parse_questions(questions_df)  # List[Question]
```

**사용 예시**:
```python
# DialogueSession에서 사용
session = DialogueSession(category, data_dir, reviews_df)

# factor_id로 질문 찾기
matches = [q for q in session.questions if q.factor_id == 1]

# factor_key로 찾기
matches = [q for q in session.questions if q.factor_key == 'noise']

# 질문 정보 접근
for question in matches:
    print(f"Q{question.question_id}: {question.question_text}")
    print(f"  Type: {question.answer_type}")
    if question.choices:
        print(f"  Choices: {question.choices}")
```

**answer_type 설명**:
- `no_choice`: 자유 응답 (예: "네", "아니오", "잘 모르겠어요")
- `single_choice`: 선택지 제공 (choices 필드 사용)

**질문 선택 로직** (DialogueSession._pick_next_question):
1. Top factors에서 아직 질문하지 않은 Factor 찾기
2. factor_id로 questions 리스트에서 매칭되는 질문 검색
3. question_id가 낮은(우선순위 높은) 질문 선택
4. 질문이 없으면 기본 질문 반환
## 부록: 에러 처리 가이드

### HTTP 에러 코드

| 코드 | 상황 | 응답 예시 |
|------|------|----------|
| `200 OK` | 정상 처리 | `{"success": true, ...}` |
| `400 Bad Request` | 잘못된 요청 | `{"detail": "Invalid URL format"}` |
| `404 Not Found` | 세션 없음 | `{"detail": "Session not found"}` |
| `422 Unprocessable Entity` | Validation 실패 | Pydantic 에러 |
| `500 Internal Server Error` | 서버 오류 | `{"detail": "Internal error"}` |
| `503 Service Unavailable` | LLM API 장애 | `{"detail": "LLM service unavailable"}` |

### 재시도 전략

**크롤러**:
- 페이지 로드 실패: 3회 재시도 (5초 간격)
- Element not found: 2회 재시도 (2초 간격)
- Timeout: 재시도 없음 (즉시 실패)

**LLM API**:
- Rate limit: 지수 백오프 (1s → 2s → 4s)
- Network error: 3회 재시도
- Timeout: fallback 메시지 반환

**Prometheus Scrape**:
- 실패 시: 다음 interval까지 대기 (15초)
- 연속 실패 시: Alert 발생

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-04 | 초기 작성 |
| 1.1 | 2026-01-05 | Factor/Question 데이터 구조 업데이트 |

---

**문서 작성자**: ReviewLens Team  
**최종 업데이트**: 2026-01-05
