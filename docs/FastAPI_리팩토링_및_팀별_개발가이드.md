# ReviewLens — FastAPI 리팩토링 가이드 & 팀 역할별 개발 가이드

> 목표: **(1) 기능은 유지**하면서 **(2) 코드 경계를 명확히** 하고, **(3) 팀이 병렬로 개발**할 수 있게 만드는 것.

---

## 0) 현재 상태 요약(업로드 소스 기준)

- `backend/app/api/routes_chat.py` 한 파일에
  - 세션 시작/대화(`/start`, `/message`)
  - 리뷰 수집(`/collect-reviews`)
  - 캐시/카테고리 감지/메시지 포맷/리뷰 관련 로직
  - LLM 설정(session_configs) 등
  가 **혼재**되어 있습니다.
- 이 구조는 MVP에선 빠르지만, **역할 분리(API/ML/인프라/FE)** 와 **테스트/관측/배포**가 어려워집니다.

리팩토링의 핵심은
1) **라우터는 얇게(HTTP만)**
2) **유스케이스/서비스로 로직 이동**
3) **도메인(대화/스코어링/리트리벌)을 독립 패키지화**
4) **계약(입출력 스키마, 이벤트, 메트릭) 먼저 고정**
입니다.

---

## 1) FastAPI 리팩토링 가이드

### 1.1 권장 폴더 구조

```text
backend/app/
  main.py
  core/
    settings.py
    logging.py
  api/
    routers/
      chat.py
      ingest.py           # CSV/URL 업로드/수집
      health.py
    schemas/
      requests.py
      responses.py
  domain/
    dialogue/
      session.py          # DialogueSession (수렴 로직 포함)
      types.py
    reg/
      store.py            # reg_factor/reg_question 로드/파싱
      matching.py         # 질문->factor 매칭
    review/
      scoring.py          # factor scoring
      retrieval.py        # evidence 추출 + label/quote
      normalize.py
  services/
    chat_service.py       # “세션/대화” 유스케이스
    review_service.py     # “리뷰 수집/분석” 유스케이스
    prompt_service.py     # LLM context/prompt 생성
  infra/
    persistence/
      session_repo.py     # SessionStore 추상화
      db.py               # DB 연결
    collectors/
      smartstore.py
    cache/
      review_cache.py
    observability/
      metrics.py
      tracing.py
  tests/
    ...
```

> 포인트: `domain/*` 는 “순수 로직”만. HTTP(FastAPI), DB, 외부수집(SmartStoreCollector), 캐시는 `infra/*`.

### 1.2 “라우터 얇게” 원칙(필수)

라우터(컨트롤러)는 아래만 합니다.
- request validation (Pydantic)
- auth/권한(있다면)
- service 호출
- response mapping
- error mapping(HTTPException)

즉, 아래는 **절대 라우터에 두지 않기**
- 리뷰 수집 크롤링 상세
- factor 점수 계산
- evidence quota/라벨링
- 대화 수렴 알고리즘
- 캐시 eviction 정책

### 1.3 세션/대화 로직 경계

#### 현재 문제
- `SessionStore` + `DialogueSession` + 라우터에서 상태를 섞어 다루는 부분이 있어, 테스트/확장이 어렵습니다.

#### 정리된 경계(추천)
- `domain.dialogue.session.DialogueSession`: **순수 대화 엔진**
  - `step(user_message, selected_factor=None) -> BotTurn`
  - `finalize_now() -> BotTurn`
  - 수렴 로직(top3 Jaccard) 등
- `services.chat_service.ChatService`: **유스케이스**
  - 세션 생성/조회/삭제
  - step 호출
  - 최종 시점에 scoring/retrieval/prompt_service 호출
- `infra.persistence.session_repo.SessionRepo`: **저장소**
  - 메모리 저장(MVP)
  - DB 저장(운영)

### 1.4 리뷰 수집/업로드 파이프라인 경계

입력은 두 가지:
1) **CSV 업로드**
2) **상품 URL 입력(리뷰 수집)**

이를 `services.review_service.ReviewService`로 고정:
- `collect_from_url(product_url, max_reviews, sort_by_low_rating) -> CollectResult`
- `ingest_from_csv(file) -> CollectResult`

CollectResult는 **표준 리뷰 포맷**으로 반환:
```json
{
  "product": {"name": "...", "url": "...", "category": "..."},
  "reviews": [ {"review_id": "...", "rating": 1, "text": "...", "created_at": "..."} ],
  "total_count": 123
}
```

### 1.5 ML(스코어링/리트리벌/라벨링) 모듈 경계

ML팀이 건드려야 할 코드는 HTTP나 DB에 의존하면 안 됩니다.
- `domain/review/scoring.py`
- `domain/review/retrieval.py`
- `domain/review/normalize.py`
- `domain/reg/*`

이 모듈은 아래 “계약”만 맞추면 됩니다.

**입력:**
- `reviews_df`(표준 컬럼)
- `factors: List[Factor]`
- `top_factors: List[(factor_key, score)]`

**출력:**
- `scored_df`
- `evidence_reviews: List[Evidence]`

Evidence 표준(권장):
```python
Evidence = {
  "review_id": str,
  "rating": int,
  "excerpt": str,
  "reason": list[str],
  "factor": str,
  "score": float,
  "label": "POS"|"NEG"|"MIX"|"NEU"
}
```

### 1.6 프롬프트/컨텍스트 생성 경계

- `services.prompt_service.PromptService`
  - `build_llm_context(session, top_factors, evidence, safety_rules, ...)`
  - `build_prompt(llm_context) -> str`

> 라우터에서는 prompt 문자열을 **직접 조립하지 말고**, 서비스만 호출.

### 1.7 설정/환경변수 정리

- `core/settings.py`에 다음을 고정:
  - `DATA_DIR`
  - `MAX_CACHE_SIZE`
  - `API_CATEGORY_PREVIEW_REVIEWS`
  - `MIN_FINALIZE_TURNS`, `MIN_STABILITY_HITS`, `TOP_FACTORS_LIMIT`
  - `PROM_METRICS_ENABLED`, `PROM_METRICS_PATH`(`/metrics`)

환경별 설정은 `.env` / Render 환경변수 / GitHub Actions secrets로만.

### 1.8 테스트 전략(최소 필수)

- **도메인 유닛 테스트(ML팀 중심)**
  - scoring: 특정 텍스트에서 anchor/context hit
  - retrieval: quota/중복/라벨/발췌
  - convergence: top3 jaccard 수렴

- **API 통합 테스트(API팀 중심)**
  - `/start` → `/message` 3~5턴 → 최종 응답
  - `/collect-reviews`는 실제 크롤러 대신 mock

- **계약 테스트(FE팀)**
  - 응답 JSON schema snapshot

---

## 2) 팀 역할별 개발 가이드

### A. API팀(백엔드 서비스/유스케이스)

#### 책임(Owner)
- FastAPI 라우팅/스키마
- 세션 관리(SessionRepo/SessionStore)
- CSV 업로드/URL 수집을 “서비스 API”로 제공
- LLM 호출 직전 컨텍스트(JSON) 생성까지
- 에러/리트라이/타임아웃 정책

#### 주요 산출물
- `api/routers/chat.py`, `api/routers/ingest.py`
- `services/chat_service.py`, `services/review_service.py`, `services/prompt_service.py`
- OpenAPI 문서(기본 자동)

#### FE와의 인터페이스(고정)

1) **세션 시작**
- `POST /api/chat/start`
- req: `{ category, provider, model_name }`
- res: `{ session_id, message }`

2) **메시지 전송**
- `POST /api/chat/message`
- req: `{ session_id, message, selected_factor?, request_finalize? }`
- res: 
  - `is_final=false`: `{ bot_message, top_factors, related_reviews?, can_finalize, turn_count, stability_info }`
  - `is_final=true`: 위 + `llm_context`

3) **리뷰 수집/업로드**
- `POST /api/chat/collect-reviews` (URL)
- `POST /api/chat/upload-csv` (파일)

#### 구현 팁
- 라우터는 `ChatService`만 호출하도록
- `collect-reviews`는 시간이 길어질 수 있으니
  - 요청 제한(max_reviews 상한)
  - 타임아웃/취소
  - 캐시(키: url|max|sort)

---

### B. ML팀(룰/스코어링/리트리벌/라벨링)

#### 책임(Owner)
- reg_factor/reg_question 포맷 해석
- factor scoring(가중치/평점 multiplier/negation 처리)
- evidence 추출(중복 제거, excerpt, quota)
- label(POS/NEG/MIX/NEU) 규칙
- (선택) 벡터 기반 유사 리뷰 검색의 도입 판단과 PoC

#### “지금 단계에서” 벡터 검색이 필요할까?
- **필수는 아님**: 지금은 anchor/context 기반으로도 “근거 리뷰”를 뽑아낼 수 있고, 데모 품질을 만들 수 있습니다.
- **필요해지는 조건**
  1) 리뷰가 수만~수십만으로 커져서 keyword scan이 병목
  2) 표현 다양성 때문에 anchor/context가 놓치는 비율이 커짐
  3) 사용자 질문이 추상적(“아이에게 괜찮을까요?”)이라 keyword 매칭이 빈약
- **추천 전략(현실적)**
  - v1: 현재 룰 기반(빠르게 완성)
  - v1.1: **후처리로만** 임베딩 검색(“키워드로 못 뽑았을 때만”) 하이브리드
  - v2: 전면 임베딩/ANN 도입

#### 주요 산출물
- `domain/review/scoring.py`
- `domain/review/retrieval.py` (quota/label 포함)
- `domain/review/normalize.py`
- `domain/reg/store.py`
- `tests/domain_review_*.py`

#### 성능/품질 체크리스트
- **정확도**: top_factors가 3~5턴 내 안정적으로 수렴하는가
- **근거 다양성**: NEG만 쏠리지 않고 POS/MIX/NEU를 의도대로 포함하는가(quota)
- **중복 제거**: SHA1/SimHash(선택)로 유사 중복 제거
- **길이 제어**: excerpt clip, evidence 상한

---

### C. FE팀(Vue: 챗봇 UI/UX)

#### 책임(Owner)
- Figma 기반 UI 구현(02_챗봇_메인)
- API 연동(`/start`, `/message`, `/collect-reviews`)
- 상태 관리(session_id, turn_count, can_finalize, final result)
- 근거 리뷰/요인/계산 로직 표시

#### 주요 산출물
- `ChatBot.vue` (현재 파일을 기준으로 고도화)
- `api.js` (endpoint/timeout/retry)
- `config.js` (API base url)

#### API팀과 합의해야 할 “UI에 필요한 응답 필드”
- `turn_count`, `stability_info`, `can_finalize`
- `top_factors[{factor_key, score}]`
- `llm_context.calculation_info`
  - `scoring_formula`: `base_score × factor_weight × rating_multiplier`
  - `rating_multiplier_formula`: `1.0 + (5 - rating) × 0.2`
  - `total_turns`
- `evidence_reviews[{excerpt, rating, label, reason}]`

#### 프론트 팁
- “사용자가 finalize 버튼을 누를 수 있는 조건”을 UI에 명확히
  - `can_finalize==true` 일 때만 활성
- evidence는 길어서 UI가 무거워질 수 있으니
  - 기본은 상위 5개만 펼침
  - 더보기 토글

---

### D. 인프라팀(CI/CD, 배포, 관측)

#### 책임(Owner)
- 배포 플랫폼 선택(Render 또는 AWS)
- GitHub Actions 자동배포
- 로깅/메트릭(프로메테우스) 노출
- 장애/성능 관측 대시보드

#### 가장 쉽고 저렴한 운영(추천 순서)

1) **Render(가장 쉬움)**
- FastAPI Web Service 1개
- (선택) Worker(리뷰 수집이 무거우면 분리)
- DB는 처음엔 SQLite/파일로 시작 → 운영은 Postgres Add-on

2) **모니터링 최소 세트**
- FastAPI에 `prometheus_client`로 `/metrics` 노출(앱 내부)
- 로그는 stdout(JSON 로그 권장)

> 질문: “Prom/Grafana를 어디 SaaS에 띄워야?”
- Prometheus/Grafana는 **앱이 아니라 별도 런타임**이 필요합니다.
  - self-host: 같은 서버(또는 별도 VM/컨테이너)에서 Prometheus+Grafana 실행
  - SaaS: Grafana Cloud(추천), Datadog, New Relic 등

Render의 free tier만으로 **Prom+Grafana를 안정적으로 같이 돌리긴 어렵고**, 가장 현실적인 선택은
- **Grafana Cloud(무료 티어)** + 앱의 `/metrics`를 scrape
또는
- **Render + 외부 Uptime/Log 서비스(무료 티어)**
입니다.

#### GitHub Actions 배포(최소)
- Render deploy hook(웹훅) 호출 방식이 제일 단순
- 또는 Render가 GitHub 연결로 자동 배포

#### 메트릭 설계(팀 경계)
- **인프라팀/Observability 담당**이 `infra/observability/metrics.py`에
  - Counter/Histogram/Gauge를 정의
- **API팀**은 라우터/서비스에서 “증분 호출”만
  - 예: `metrics.chat_turn_total.inc()`
  - 예: `metrics.latency_seconds.labels(route="/message").observe(x)`

---

## 3) 팀 간 인터페이스 문서(최소 합의안)

### 3.1 공통 데이터 모델(표준)

- Review
  - `review_id: str`
  - `rating: int`
  - `text: str`
  - `created_at: str`(없으면 "")

- Factor
  - `factor_key: str`
  - `display_name: str`
  - `anchor_terms/context_terms/negation_terms: list[str]`
  - `weight: float`
  - `category: str`

- Evidence
  - 위 1.5 참조

### 3.2 성능 목표(가이드)

- `/message`: p95 < 1s(리뷰 리트리벌 포함)
- `/collect-reviews`: 시간 오래 걸릴 수 있음(비동기/워커 분리 고려)

---

## 4) 다음 액션(현실적인 1주 스프린트)

1) **API팀**: `routes_chat.py`를 `chat_service` 중심으로 “라우터 얇게” 리팩토링
2) **ML팀**: scoring/retrieval/label 모듈을 `domain/`로 분리 + 유닛 테스트
3) **FE팀**: Figma UI 반영 + `can_finalize`/`stability_info` UX
4) **인프라팀**: `/metrics` 노출 + Render 배포 파이프라인(GitHub 연동)

---

## 부록) Done 정의(간단)

- API팀 Done
  - 라우터에서 비즈니스 로직 제거
  - swagger에서 3개 API(`/start`, `/message`, `/collect...`) 확인
  - e2e 테스트 1개 통과

- ML팀 Done
  - 샘플 데이터로 evidence 15개 이내 추출
  - label 분포가 quota 의도대로 나오는지 테스트

- FE팀 Done
  - 3~5턴 대화 흐름 + 최종 결과 화면
  - 계산 로직/총 턴 표시

- 인프라팀 Done
  - /metrics 동작
  - 배포 후 health check + 로그 확인
