#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Load Reference Data into PostgreSQL (ReviewLens)

Inputs:
- reg_factor_v4_1.csv: includes product_no, factor_seq
- reg_question_v6.csv
- review json files: "{product_no:02d}_reviews_smartstore_{product_name}.json"

Behavior:
- Truncate ref_* tables (safe re-load)
- Insert ref_products derived from factors
- Insert ref_factors, ref_questions
- Insert ref_reviews with ON CONFLICT DO NOTHING (dedupe)
- If --strict-filename-match: enforce product_name in filename matches ref_products mapping

Usage example (Windows PowerShell):
python db/load_reference_data.py `
  --db-url "postgresql://postgres:sqsq2601@localhost:5432/reviewlens" `
  --factors "backend/data/reference/reg_factor_v4_1.csv" `
  --questions "backend/data/reference/reg_question_v6.csv" `
  --reviews-glob "backend/data/reference/*_reviews_smartstore_*.json" `
  --strict-filename-match
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import psycopg2
import psycopg2.extras


# ----------------------------
# Helpers
# ----------------------------

def normalize_name(s: str) -> str:
    """Normalize product_name for safe comparison (strip + collapse spaces)."""
    return " ".join((s or "").strip().split())


REVIEWS_FILENAME_RE = re.compile(
    r"^(?P<product_no>\d{2})_reviews_smartstore_(?P<product_name>.+)\.json$"
)


@dataclass(frozen=True)
class ProductRow:
    product_no: int
    product_name: str
    category: str
    category_name: str


@dataclass(frozen=True)
class FactorRow:
    factor_id: int
    product_no: int
    factor_seq: int
    factor_key: str
    category: str
    category_name: str
    product_name: str
    regret_type: Optional[str]
    display_name: str
    description: Optional[str]
    anchor_terms: Optional[str]
    context_terms: Optional[str]
    negation_terms: Optional[str]
    weight: float
    review_mentions: Optional[int]


@dataclass(frozen=True)
class QuestionRow:
    question_id: int
    factor_id: int
    factor_key: str
    question_text: str
    answer_type: str
    choices: Optional[str]
    next_factor_hint: Optional[str]


@dataclass(frozen=True)
class ReviewRow:
    product_no: int
    review_id: int
    rating: Optional[int]
    text: str
    created_at: Optional[str]  # ISO8601; Postgres will parse timestamptz if valid


def parse_reviews_filename(path: str) -> Tuple[int, str]:
    base = os.path.basename(path)
    m = REVIEWS_FILENAME_RE.match(base)
    if not m:
        raise ValueError(
            f"[FILENAME ERROR] 리뷰 파일명 규칙 불일치: {base}\n"
            f"Expected: 01_reviews_smartstore_<product_name>.json"
        )
    product_no = int(m.group("product_no"))
    product_name = m.group("product_name")
    return product_no, product_name


def read_factors_csv(path: str) -> Tuple[Dict[int, ProductRow], List[FactorRow]]:
    products: Dict[int, ProductRow] = {}
    factors: List[FactorRow] = []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {
            "factor_id", "product_no", "factor_seq",
            "factor_key", "category", "category_name", "product_name",
            "regret_type", "display_name", "description",
            "anchor_terms", "context_terms", "negation_terms",
            "weight", "review_mentions"
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"[CSV ERROR] reg_factor_v4_1.csv missing columns: {sorted(missing)}")

        for row in reader:
            factor_id = int(row["factor_id"])
            product_no = int(row["product_no"])
            factor_seq = int(row["factor_seq"])

            # Optional consistency check: factor_id should match product_no/factor_seq convention
            # factor_id == product_no*100 + factor_seq (typical)
            expected_factor_id = product_no * 100 + factor_seq
            if factor_id != expected_factor_id:
                # not fatal, but strongly suspicious; fail fast to avoid silent corruption
                raise ValueError(
                    f"[CSV ERROR] factor_id convention mismatch: "
                    f"factor_id={factor_id}, product_no={product_no}, factor_seq={factor_seq} "
                    f"(expected factor_id={expected_factor_id})"
                )

            product_name = row["product_name"].strip()
            category = row["category"].strip()
            category_name = row["category_name"].strip()

            if product_no not in products:
                products[product_no] = ProductRow(
                    product_no=product_no,
                    product_name=product_name,
                    category=category,
                    category_name=category_name,
                )
            else:
                # sanity: same product_no should have stable product/category strings
                p = products[product_no]
                if normalize_name(p.product_name) != normalize_name(product_name):
                    raise ValueError(
                        f"[CSV ERROR] product_no={product_no} has inconsistent product_name: "
                        f"'{p.product_name}' vs '{product_name}'"
                    )
                if p.category != category or p.category_name != category_name:
                    raise ValueError(
                        f"[CSV ERROR] product_no={product_no} has inconsistent category fields: "
                        f"('{p.category}', '{p.category_name}') vs ('{category}', '{category_name}')"
                    )

            def _opt_int(v: str) -> Optional[int]:
                v = (v or "").strip()
                return int(v) if v != "" else None

            def _opt_text(v: str) -> Optional[str]:
                v = (v or "").strip()
                return v if v != "" else None

            factors.append(
                FactorRow(
                    factor_id=factor_id,
                    product_no=product_no,
                    factor_seq=factor_seq,
                    factor_key=row["factor_key"].strip(),
                    category=category,
                    category_name=category_name,
                    product_name=product_name,
                    regret_type=_opt_text(row.get("regret_type", "")),
                    display_name=row["display_name"].strip(),
                    description=_opt_text(row.get("description", "")),
                    anchor_terms=_opt_text(row.get("anchor_terms", "")),
                    context_terms=_opt_text(row.get("context_terms", "")),
                    negation_terms=_opt_text(row.get("negation_terms", "")),
                    weight=float(row["weight"]),
                    review_mentions=_opt_int(row.get("review_mentions", "")),
                )
            )

    return products, factors


def read_questions_csv(path: str) -> List[QuestionRow]:
    questions: List[QuestionRow] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {
            "question_id", "factor_id", "factor_key",
            "question_text", "answer_type", "choices", "next_factor_hint"
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"[CSV ERROR] reg_question_v6.csv missing columns: {sorted(missing)}")

        for row in reader:
            def _opt_text(v: str) -> Optional[str]:
                v = (v or "").strip()
                return v if v != "" else None

            questions.append(
                QuestionRow(
                    question_id=int(row["question_id"]),
                    factor_id=int(row["factor_id"]),
                    factor_key=row["factor_key"].strip(),
                    question_text=row["question_text"].strip(),
                    answer_type=row["answer_type"].strip(),
                    choices=_opt_text(row.get("choices", "")),
                    next_factor_hint=_opt_text(row.get("next_factor_hint", "")),
                )
            )
    return questions


def iter_reviews_from_json(path: str, product_no: int) -> Iterable[ReviewRow]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"[JSON ERROR] Expected list in {path}, got {type(data)}")

    for obj in data:
        if not isinstance(obj, dict):
            continue

        review_id = obj.get("review_id")
        text = (obj.get("text") or "").strip()
        if review_id is None or text == "":
            continue

        rating = obj.get("rating")
        created_at = obj.get("created_at")

        try:
            review_id_int = int(review_id)
        except Exception:
            # if somehow not int, skip rather than crash
            continue

        rating_int: Optional[int]
        try:
            rating_int = int(rating) if rating is not None and str(rating).strip() != "" else None
        except Exception:
            rating_int = None

        created_at_str: Optional[str] = None
        if created_at is not None and str(created_at).strip() != "":
            created_at_str = str(created_at).strip()

        yield ReviewRow(
            product_no=product_no,
            review_id=review_id_int,
            rating=rating_int,
            text=text,
            created_at=created_at_str,
        )


# ----------------------------
# DB Load
# ----------------------------

TRUNCATE_SQL = """
TRUNCATE TABLE
  ref_reviews,
  ref_questions,
  ref_factors,
  ref_products
RESTART IDENTITY;
"""

INSERT_PRODUCT_SQL = """
INSERT INTO ref_products (product_no, product_name, category, category_name)
VALUES %s
ON CONFLICT (product_no) DO UPDATE
SET product_name = EXCLUDED.product_name,
    category = EXCLUDED.category,
    category_name = EXCLUDED.category_name;
"""

INSERT_FACTOR_SQL = """
INSERT INTO ref_factors (
  factor_id, product_no, factor_seq,
  factor_key, category, category_name, product_name,
  regret_type, display_name, description,
  anchor_terms, context_terms, negation_terms,
  weight, review_mentions
)
VALUES %s
ON CONFLICT (factor_id) DO UPDATE
SET
  product_no = EXCLUDED.product_no,
  factor_seq = EXCLUDED.factor_seq,
  factor_key = EXCLUDED.factor_key,
  category = EXCLUDED.category,
  category_name = EXCLUDED.category_name,
  product_name = EXCLUDED.product_name,
  regret_type = EXCLUDED.regret_type,
  display_name = EXCLUDED.display_name,
  description = EXCLUDED.description,
  anchor_terms = EXCLUDED.anchor_terms,
  context_terms = EXCLUDED.context_terms,
  negation_terms = EXCLUDED.negation_terms,
  weight = EXCLUDED.weight,
  review_mentions = EXCLUDED.review_mentions;
"""

INSERT_QUESTION_SQL = """
INSERT INTO ref_questions (
  question_id, factor_id, factor_key,
  question_text, answer_type, choices, next_factor_hint
)
VALUES %s
ON CONFLICT (question_id) DO UPDATE
SET
  factor_id = EXCLUDED.factor_id,
  factor_key = EXCLUDED.factor_key,
  question_text = EXCLUDED.question_text,
  answer_type = EXCLUDED.answer_type,
  choices = EXCLUDED.choices,
  next_factor_hint = EXCLUDED.next_factor_hint;
"""

# 핵심: 중복이면 멈추지 않고 무시 (이번 에러 재발 방지)
INSERT_REVIEW_SQL = """
INSERT INTO ref_reviews (product_no, review_id, rating, text, created_at)
VALUES %s
ON CONFLICT (product_no, review_id) DO NOTHING;
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-url", required=True, help="e.g. postgresql://user:pw@localhost:5432/reviewlens")
    ap.add_argument("--factors", required=True, help="Path to reg_factor_v4_1.csv")
    ap.add_argument("--questions", required=True, help="Path to reg_question_v6.csv")
    ap.add_argument("--reviews-glob", required=True, help='Glob like "backend/data/reference/*_reviews_smartstore_*.json"')
    ap.add_argument("--strict-filename-match", action="store_true",
                    help="Fail if product_name in json filename doesn't match ref_products mapping.")
    args = ap.parse_args()

    try:
        products_map, factors = read_factors_csv(args.factors)
        questions = read_questions_csv(args.questions)
        review_files = sorted(glob.glob(args.reviews_glob))
        if not review_files:
            raise ValueError(f"[FILE ERROR] No review files matched glob: {args.reviews_glob}")

        # Connect DB
        conn = psycopg2.connect(args.db_url)
        conn.autocommit = False

        with conn.cursor() as cur:
            # 1) truncate existing reference tables
            cur.execute(TRUNCATE_SQL)

            # 2) insert products
            product_rows = [
                (p.product_no, p.product_name, p.category, p.category_name)
                for p in sorted(products_map.values(), key=lambda x: x.product_no)
            ]
            psycopg2.extras.execute_values(cur, INSERT_PRODUCT_SQL, product_rows, page_size=200)

            # 3) insert factors
            factor_rows = [
                (
                    f.factor_id, f.product_no, f.factor_seq,
                    f.factor_key, f.category, f.category_name, f.product_name,
                    f.regret_type, f.display_name, f.description,
                    f.anchor_terms, f.context_terms, f.negation_terms,
                    f.weight, f.review_mentions
                )
                for f in factors
            ]
            psycopg2.extras.execute_values(cur, INSERT_FACTOR_SQL, factor_rows, page_size=500)

            # 4) insert questions
            question_rows = [
                (
                    q.question_id, q.factor_id, q.factor_key,
                    q.question_text, q.answer_type, q.choices, q.next_factor_hint
                )
                for q in questions
            ]
            psycopg2.extras.execute_values(cur, INSERT_QUESTION_SQL, question_rows, page_size=500)

            # 5) insert reviews (dedupe via ON CONFLICT DO NOTHING)
            total_reviews = 0
            for path in review_files:
                product_no_from_fn, product_name_from_fn = parse_reviews_filename(path)

                if product_no_from_fn not in products_map:
                    raise ValueError(
                        f"[FILENAME ERROR] product_no={product_no_from_fn} not found in factors CSV. "
                        f"File: {os.path.basename(path)}"
                    )

                if args.strict_filename_match:
                    expected = normalize_name(products_map[product_no_from_fn].product_name)
                    got = normalize_name(product_name_from_fn)
                    if expected != got:
                        raise ValueError(
                            f"[FILENAME ERROR] product_name mismatch for product_no={product_no_from_fn}\n"
                            f"  expected(from factors): '{products_map[product_no_from_fn].product_name}'\n"
                            f"  got(from filename)    : '{product_name_from_fn}'\n"
                            f"  file: {os.path.basename(path)}"
                        )

                batch: List[Tuple[int, int, Optional[int], str, Optional[str]]] = []
                for r in iter_reviews_from_json(path, product_no_from_fn):
                    batch.append((r.product_no, r.review_id, r.rating, r.text, r.created_at))

                if batch:
                    psycopg2.extras.execute_values(cur, INSERT_REVIEW_SQL, batch, page_size=1000)
                    total_reviews += len(batch)

            conn.commit()

        print("[OK] Reference data load completed.")
        print(f"  products: {len(product_rows)}")
        print(f"  factors:  {len(factor_rows)}")
        print(f"  questions:{len(question_rows)}")
        print(f"  reviews(input rows): {total_reviews}")
        print("  note: reviews duplicates are ignored by ON CONFLICT DO NOTHING")
        return 0

    except Exception as e:
        print(f"[DB ERROR] {e}")
        try:
            conn.rollback()  # type: ignore
        except Exception:
            pass
        return 1
    finally:
        try:
            conn.close()  # type: ignore
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
