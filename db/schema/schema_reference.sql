-- =========================================================
-- ReviewLens - Reference Schema (FINAL)
-- Based on:
--   - reg_factor_v4_1.csv  (official, includes product_no)
--   - reg_question_v6.csv
--
-- Purpose:
--   - Fast startup (DB-backed reference data)
--   - Strong integrity guarantees
--   - Safe re-loading (idempotent)
-- =========================================================

BEGIN;

-- =========================================================
-- 1. Reference Data Versioning
-- =========================================================
CREATE TABLE IF NOT EXISTS reference_data_versions (
    version_id      SERIAL PRIMARY KEY,
    source_name     TEXT NOT NULL,          -- e.g. 'reg_factor_v4_1'
    description     TEXT,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- 2. Products (derived from reg_factor_v4_1)
-- =========================================================
CREATE TABLE IF NOT EXISTS ref_products (
    product_no      INTEGER PRIMARY KEY,    -- 1 ~ 10
    product_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    category_name   TEXT NOT NULL
);

-- =========================================================
-- 3. Regret Factors
-- =========================================================
CREATE TABLE IF NOT EXISTS ref_factors (
    factor_id           INTEGER PRIMARY KEY,     -- e.g. 101, 1001
    product_no          INTEGER NOT NULL,         -- derived, official column
    factor_seq          INTEGER NOT NULL,         -- factor_id % 100

    factor_key          TEXT NOT NULL,
    category            TEXT NOT NULL,
    category_name       TEXT NOT NULL,
    product_name        TEXT NOT NULL,

    regret_type         TEXT,
    display_name        TEXT NOT NULL,
    description         TEXT,

    anchor_terms        TEXT,     -- '|' separated
    context_terms       TEXT,     -- '|' separated
    negation_terms      TEXT,     -- '|' separated

    weight              DOUBLE PRECISION NOT NULL,
    review_mentions     INTEGER,

    CONSTRAINT uq_product_factor_seq
        UNIQUE (product_no, factor_seq),

    CONSTRAINT fk_factor_product
        FOREIGN KEY (product_no)
        REFERENCES ref_products (product_no)
        ON DELETE CASCADE
);

-- =========================================================
-- 4. Questions
-- =========================================================
CREATE TABLE IF NOT EXISTS ref_questions (
    question_id         INTEGER PRIMARY KEY,
    factor_id           INTEGER NOT NULL,

    factor_key          TEXT NOT NULL,
    question_text       TEXT NOT NULL,
    answer_type         TEXT NOT NULL,
    choices             TEXT,
    next_factor_hint    TEXT,

    CONSTRAINT fk_question_factor
        FOREIGN KEY (factor_id)
        REFERENCES ref_factors (factor_id)
        ON DELETE CASCADE
);

-- =========================================================
-- 5. Reviews (Reference Reviews)
-- =========================================================
CREATE TABLE IF NOT EXISTS ref_reviews (
    product_no      INTEGER NOT NULL,
    review_id       BIGINT NOT NULL,     -- original collected ID
    rating          INTEGER,
    text            TEXT NOT NULL,
    created_at      TIMESTAMPTZ,

    PRIMARY KEY (product_no, review_id),

    CONSTRAINT fk_review_product
        FOREIGN KEY (product_no)
        REFERENCES ref_products (product_no)
        ON DELETE CASCADE
);

-- =========================================================
-- 6. Indexes (Read-heavy optimization)
-- =========================================================
CREATE INDEX IF NOT EXISTS idx_ref_factors_product
    ON ref_factors (product_no);

CREATE INDEX IF NOT EXISTS idx_ref_questions_factor
    ON ref_questions (factor_id);

CREATE INDEX IF NOT EXISTS idx_ref_reviews_product
    ON ref_reviews (product_no);

COMMIT;
