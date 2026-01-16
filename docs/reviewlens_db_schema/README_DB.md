# DB 스키마 설계 요약 (reg_factor_v4 / reg_question_v6 / review.json 기준)

## 왜 이렇게 나눴나
- **category**: REG가 “붙는 기준 단위”입니다. `product_name`는 여기에 섞이면 안 됩니다.
- **product**: 실제 운영 쇼핑몰에 붙을 때 중심 엔티티. 데모에서는 product 없이 category만으로도 동작.
- **reg_set**: 같은 category라도 v1/v2/v4를 **동시에 보관**해서 회귀 테스트/개선 추적 가능.
- **review / ingestion_job**: 업로드/수집 단위를 job으로 묶고, 리뷰는 원문/정규화/sha1을 함께 저장해 **중복제거/재현** 가능.
- **chat_session / chat_turn / analysis_run / analysis_evidence**: “대화→수렴→근거추출→프롬프트 생성”까지를 영구 저장해 디버깅/품질검증에 유리.
- **metrics_event**: Prometheus가 실시간 TSDB를 가지더라도, 서비스 품질 이벤트는 DB에 남겨야 “나중에 원인추적/리그레션 분석”이 쉬움.

## reg_factor_v4.csv / reg_question_v6.csv → DB 매핑 가이드
### reg_factor
- `category` / `category_slug` 류 컬럼 → `category.category_slug`
- `category_name` 류 컬럼 → `category.category_name`
- `version`(v4 등) → `reg_set.version_tag`
- `factor_key` → `reg_factor.factor_key`
- `display_name` → `reg_factor.display_name`
- `weight` → `reg_factor.weight`
- `anchor_terms|context_terms|negation_terms` ("a|b|c") → `TEXT[]`

### reg_question
- `factor_key` → `reg_question.factor_key`
- `question_text`(or question) → `reg_question.question_text`
- `priority` → `reg_question.priority`

## 바로 쓰는 방법
1) Postgres에 스키마 적용

```bash
psql "$DATABASE_URL" -f schema_postgres.sql
```

2) (선택) seed 스크립트를 만들어서
- category 1개 생성
- reg_set(v4) 생성
- reg_factor / reg_question bulk insert
- review.json/csv 업로드 → ingestion_job + review insert

> seed/ingest는 지금 코드베이스(FastAPI)에서 `scripts/seed_reg.py`, `scripts/ingest_reviews.py`로 분리하는 걸 추천.
