-- =========================================================
-- ReviewLens (AI Bootcamp) - Runtime / Analytics Schema (MVP)
--
-- IMPORTANT:
--   Apply schema_reference.sql BEFORE this file.
--   This runtime schema references:
--     - ref_products(category)
--     - ref_questions(question_id)
-- =========================================================

-- ---------------------------------------------------------
-- 1) Dialogue Sessions
-- category_key is the same stable key as ref_products.category
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS dialogue_sessions (
  session_id         UUID PRIMARY KEY,

  category_key       TEXT NOT NULL REFERENCES ref_products(category) ON DELETE RESTRICT,

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

CREATE INDEX IF NOT EXISTS idx_sessions_category_started_at
  ON dialogue_sessions(category_key, started_at DESC);

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

-- =========================================================
-- End of Runtime schema
-- =========================================================
