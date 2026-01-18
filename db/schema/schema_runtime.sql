-- =========================================================
-- ReviewLens (AI Bootcamp) - Runtime / Analytics Schema (MVP)
--
-- IMPORTANT:
--   Apply schema_reference.sql BEFORE this file.
--   This runtime schema references:
--     - ref_products(product_no)
--     - ref_questions(question_id)
-- =========================================================

-- ---------------------------------------------------------
-- 1) Dialogue Sessions
-- product_no is the stable FK to ref_products(product_no)
-- category_key is optional (snapshot/compat); NOT used as FK.
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS dialogue_sessions (
  session_id         UUID PRIMARY KEY,

  product_no         INT NOT NULL REFERENCES ref_products(product_no) ON DELETE RESTRICT,

  -- Optional snapshot/compat field (do NOT FK this)
  category_key       TEXT,

  provider           TEXT,
  model_name         TEXT,

  started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at           TIMESTAMPTZ,

  total_turns        INT NOT NULL DEFAULT 0,
  completed          BOOLEAN NOT NULL DEFAULT FALSE,
  exit_reason        TEXT CHECK (exit_reason IN ('converged', 'turn_limit', 'user_drop', 'error')),

  final_top_factors  JSONB,
  llm_context_final  JSONB
);

-- Query patterns:
-- - recent sessions per product
-- - funnels/metrics per product
CREATE INDEX IF NOT EXISTS idx_sessions_product_started_at
  ON dialogue_sessions(product_no, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_started_at
  ON dialogue_sessions(started_at DESC);

-- ---------------------------------------------------------
-- 2) Dialogue Turns
-- question_id references ref_questions(question_id)
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS dialogue_turns (
  session_id     UUID NOT NULL REFERENCES dialogue_sessions(session_id) ON DELETE CASCADE,
  turn_index     INT  NOT NULL,

  question_id    INT  NOT NULL REFERENCES ref_questions(question_id) ON DELETE RESTRICT,

  user_message   TEXT NOT NULL,
  bot_message    TEXT,

  top_factors    JSONB,
  is_final       BOOLEAN NOT NULL DEFAULT FALSE,
  llm_context    JSONB,

  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

  PRIMARY KEY (session_id, turn_index)
);

CREATE INDEX IF NOT EXISTS idx_turns_created_at
  ON dialogue_turns(created_at DESC);

-- Useful for "which questions cause drop-off"
CREATE INDEX IF NOT EXISTS idx_turns_question_id
  ON dialogue_turns(question_id);

-- Ensure only one final turn per session.
CREATE UNIQUE INDEX IF NOT EXISTS uq_one_final_turn_per_session
  ON dialogue_turns(session_id)
  WHERE (is_final = TRUE);

-- ---------------------------------------------------------
-- 3) LLM Runs (final only: 1 per session)
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS llm_runs (
  session_id     UUID PRIMARY KEY REFERENCES dialogue_sessions(session_id) ON DELETE CASCADE,

  status         TEXT NOT NULL CHECK (status IN ('success', 'fallback', 'error')),
  provider       TEXT,
  model_name     TEXT,

  llm_context    JSONB,
  output_text    TEXT,
  error_message  TEXT,

  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_llm_status_created_at
  ON llm_runs(status, created_at DESC);