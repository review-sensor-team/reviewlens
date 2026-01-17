-- ReviewLens DB Schema (PostgreSQL 14+)
-- Goal: keep REG (factor/question) versioned per category, store raw reviews, and persist chat/runs/evidence.

-- Optional but recommended extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;        -- case-insensitive text (optional)

-- ----------------------------
-- 1) Reference / Catalog
-- ----------------------------

-- 쇼핑몰(데이터 소스) 단위
CREATE TABLE IF NOT EXISTS shop (
  shop_id          BIGSERIAL PRIMARY KEY,
  shop_key         TEXT NOT NULL UNIQUE,      -- e.g. "smartstore"
  shop_name        TEXT NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 카테고리(= REG가 붙는 단위). product_name은 여기로 들어오면 안 됨.
CREATE TABLE IF NOT EXISTS category (
  category_id      BIGSERIAL PRIMARY KEY,
  category_slug    TEXT NOT NULL UNIQUE,      -- e.g. "appliance_heated_humidifier"
  category_name    TEXT NOT NULL,             -- e.g. "가전/가열식 가습기"
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 상품(선택): 실제 서비스로 들어가면 product_id가 대화/리뷰/분석의 중심이 됨
CREATE TABLE IF NOT EXISTS product (
  product_id       BIGSERIAL PRIMARY KEY,
  shop_id          BIGINT REFERENCES shop(shop_id) ON DELETE SET NULL,
  category_id      BIGINT REFERENCES category(category_id) ON DELETE SET NULL,
  external_product_id TEXT,                   -- mall/product SKU or itemId
  product_name     TEXT NOT NULL,
  product_url      TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_product_category ON product(category_id);
CREATE INDEX IF NOT EXISTS idx_product_shop ON product(shop_id);

-- ----------------------------
-- 2) REG (Regret Factor / Question)
-- ----------------------------

-- REG 세트 버전(같은 카테고리에서도 v1/v2로 공존 가능)
CREATE TABLE IF NOT EXISTS reg_set (
  reg_set_id       BIGSERIAL PRIMARY KEY,
  category_id      BIGINT NOT NULL REFERENCES category(category_id) ON DELETE CASCADE,
  version_tag      TEXT NOT NULL,             -- e.g. "v4" (from file version)
  created_by       TEXT,                      -- optional (PM name/email)
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(category_id, version_tag)
);
CREATE INDEX IF NOT EXISTS idx_reg_set_category ON reg_set(category_id);

-- 요인 정의
CREATE TABLE IF NOT EXISTS reg_factor (
  reg_factor_id    BIGSERIAL PRIMARY KEY,
  reg_set_id       BIGINT NOT NULL REFERENCES reg_set(reg_set_id) ON DELETE CASCADE,
  factor_key       TEXT NOT NULL,             -- stable identifier (code)
  display_name     TEXT NOT NULL,             -- human readable
  weight           NUMERIC(6,3) NOT NULL DEFAULT 1.0,

  -- term dictionaries (token-match MVP). later can be embedding dictionary.
  anchor_terms     TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  context_terms    TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  negation_terms   TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],

  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(reg_set_id, factor_key)
);
CREATE INDEX IF NOT EXISTS idx_reg_factor_reg_set ON reg_factor(reg_set_id);

-- 대화 유도 질문(요인 수렴용)
CREATE TABLE IF NOT EXISTS reg_question (
  reg_question_id  BIGSERIAL PRIMARY KEY,
  reg_set_id       BIGINT NOT NULL REFERENCES reg_set(reg_set_id) ON DELETE CASCADE,
  factor_key       TEXT NOT NULL,             -- keep as key for simple join
  question_text    TEXT NOT NULL,
  priority         INT NOT NULL DEFAULT 999,
  is_active        BOOLEAN NOT NULL DEFAULT TRUE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reg_question_reg_set ON reg_question(reg_set_id);
CREATE INDEX IF NOT EXISTS idx_reg_question_factor_key ON reg_question(factor_key);

-- ----------------------------
-- 3) Review ingestion
-- ----------------------------

-- 한 번의 수집(파일 업로드/URL 크롤 등) 단위
CREATE TABLE IF NOT EXISTS ingestion_job (
  job_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shop_id          BIGINT REFERENCES shop(shop_id) ON DELETE SET NULL,
  product_id       BIGINT REFERENCES product(product_id) ON DELETE SET NULL,
  category_id      BIGINT REFERENCES category(category_id) ON DELETE SET NULL,

  source_type      TEXT NOT NULL,             -- "csv" | "json" | "url" | ...
  source_ref       TEXT,                      -- filepath or url
  fetched_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  status           TEXT NOT NULL DEFAULT 'done',  -- done|failed|partial
  meta             JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_ingestion_job_product ON ingestion_job(product_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_job_category ON ingestion_job(category_id);

-- 리뷰 원문 (중복 제거를 위한 norm_sha1 포함)
CREATE TABLE IF NOT EXISTS review (
  review_pk        BIGSERIAL PRIMARY KEY,
  job_id           UUID REFERENCES ingestion_job(job_id) ON DELETE SET NULL,
  product_id       BIGINT REFERENCES product(product_id) ON DELETE SET NULL,
  category_id      BIGINT REFERENCES category(category_id) ON DELETE SET NULL,

  external_review_id TEXT NOT NULL,           -- review_id from source
  rating           SMALLINT,
  text             TEXT NOT NULL,
  created_at       TIMESTAMPTZ,

  norm_text        TEXT,                      -- normalize(text)
  norm_sha1        CHAR(40),                  -- sha1(norm_text)

  meta             JSONB NOT NULL DEFAULT '{}'::jsonb,
  inserted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(job_id, external_review_id)
);
CREATE INDEX IF NOT EXISTS idx_review_product ON review(product_id);
CREATE INDEX IF NOT EXISTS idx_review_category ON review(category_id);
CREATE INDEX IF NOT EXISTS idx_review_sha1 ON review(norm_sha1);

-- 판매자 답글(있으면) - 리뷰와 분리
CREATE TABLE IF NOT EXISTS review_reply (
  reply_id         BIGSERIAL PRIMARY KEY,
  review_pk        BIGINT NOT NULL REFERENCES review(review_pk) ON DELETE CASCADE,
  reply_text       TEXT NOT NULL,
  replied_at       TIMESTAMPTZ,
  meta             JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_reply_review ON review_reply(review_pk);

-- ----------------------------
-- 4) Chat & Analysis
-- ----------------------------

-- 사용자 세션(대화 단위)
CREATE TABLE IF NOT EXISTS chat_session (
  session_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id      BIGINT REFERENCES category(category_id) ON DELETE SET NULL,
  product_id       BIGINT REFERENCES product(product_id) ON DELETE SET NULL,
  reg_set_id       BIGINT REFERENCES reg_set(reg_set_id) ON DELETE SET NULL,

  started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at         TIMESTAMPTZ,
  client_meta      JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_chat_session_product ON chat_session(product_id);
CREATE INDEX IF NOT EXISTS idx_chat_session_category ON chat_session(category_id);

-- 채팅 턴(질문/응답 모두)
CREATE TABLE IF NOT EXISTS chat_turn (
  turn_id          BIGSERIAL PRIMARY KEY,
  session_id       UUID NOT NULL REFERENCES chat_session(session_id) ON DELETE CASCADE,
  turn_index       INT NOT NULL,
  role             TEXT NOT NULL,             -- "user" | "assistant"
  message          TEXT NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- debug: turn 시점의 top_factors snapshot
  top_factors      JSONB NOT NULL DEFAULT '[]'::jsonb,

  UNIQUE(session_id, turn_index)
);
CREATE INDEX IF NOT EXISTS idx_chat_turn_session ON chat_turn(session_id);

-- 분석 실행(LLM 호출 직전까지 만들어진 컨텍스트/프롬프트 저장)
CREATE TABLE IF NOT EXISTS analysis_run (
  run_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id       UUID NOT NULL REFERENCES chat_session(session_id) ON DELETE CASCADE,
  reg_set_id       BIGINT REFERENCES reg_set(reg_set_id) ON DELETE SET NULL,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  top_factors      JSONB NOT NULL DEFAULT '[]'::jsonb,
  llm_context      JSONB NOT NULL DEFAULT '{}'::jsonb,
  llm_prompt       TEXT,

  model_name       TEXT,                      -- e.g. "gpt-4.1" etc
  model_meta       JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_analysis_run_session ON analysis_run(session_id);

-- 증거 리뷰(요인별 근거로 뽑힌 리뷰)
CREATE TABLE IF NOT EXISTS analysis_evidence (
  evidence_id      BIGSERIAL PRIMARY KEY,
  run_id           UUID NOT NULL REFERENCES analysis_run(run_id) ON DELETE CASCADE,

  factor_key       TEXT NOT NULL,
  review_pk        BIGINT REFERENCES review(review_pk) ON DELETE SET NULL,

  score            NUMERIC(10,4) NOT NULL DEFAULT 0,
  label            TEXT NOT NULL DEFAULT 'NEU', -- POS|NEG|MIX|NEU
  excerpt          TEXT,
  reason           JSONB NOT NULL DEFAULT '[]'::jsonb,
  rank_in_factor   INT,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_evidence_run ON analysis_evidence(run_id);
CREATE INDEX IF NOT EXISTS idx_evidence_factor ON analysis_evidence(factor_key);

-- ----------------------------
-- 5) Metrics / Monitoring (history)
-- ----------------------------

-- Prometheus는 time-series를 자체 TSDB에 저장하지만,
-- 서비스 분석/감사/품질 추적을 위해 "이벤트"를 별도로 남기면 유용.
CREATE TABLE IF NOT EXISTS metrics_event (
  event_id         BIGSERIAL PRIMARY KEY,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  event_name       TEXT NOT NULL,             -- e.g. "ingest_done", "chat_finalized"
  session_id       UUID REFERENCES chat_session(session_id) ON DELETE SET NULL,
  run_id           UUID REFERENCES analysis_run(run_id) ON DELETE SET NULL,
  payload          JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_metrics_event_name_time ON metrics_event(event_name, created_at DESC);
