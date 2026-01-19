"""
Load ReviewLens reference datasets into PostgreSQL.

What it does
- Loads reference datasets from backend/data/reference/ into ref_* tables:
  - reg_factor_v4_1.csv  -> ref_products, ref_factors
  - reg_question_v6.csv  -> ref_questions
  - {product_no:02d}_reviews_smartstore_*.json -> ref_reviews

When to run
- During local/dev DB bootstrap (after schema_reference.sql applied).
- When reference files change and need re-loading.

Notes
- Reference data is treated as read-only and loaded via upsert (idempotent).
- product_no for reviews is derived from the filename prefix (e.g. "02_...json" -> 2).
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import psycopg


@dataclass(frozen=True)
class PgConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    @staticmethod
    def from_env() -> "PgConfig":
        # 팀 공통: .env(.example)로 주입
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        dbname = os.getenv("POSTGRES_DB", "reviewlens")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")
        if not password:
            raise RuntimeError("POSTGRES_PASSWORD is empty. Set it in .env (NOT .env.example).")
        return PgConfig(host, port, dbname, user, password)

    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.user} password={self.password}"
        )


def parse_timestamptz(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except Exception:
        return None


def upsert_reference_version(cur, source_name: str, description: str) -> None:
    cur.execute(
        """
        INSERT INTO reference_data_versions(source_name, description)
        VALUES (%s, %s)
        """,
        (source_name, description),
    )


def load_reg_factors(conn: psycopg.Connection, reg_factor_csv: str) -> None:
    """
    CSV header (confirmed):
    product_no,factor_seq,factor_id,factor_key,category,category_name,product_name,regret_type,display_name,
    description,anchor_terms,context_terms,negation_terms,weight,review_mentions
    """
    with open(reg_factor_csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        # 헤더 정규화 (BOM/공백 제거)
        reader.fieldnames = [
            (h or "").strip().lstrip("\ufeff")
            for h in (reader.fieldnames or [])
        ]

        rows = []
        for row in reader:
            # 각 행의 key도 정규화 (간헐적으로 헤더/키가 깨지는 케이스 방어)
            norm = {}
            for k, v in row.items():
                if k is None:
                    continue
                nk = k.strip().lstrip("\ufeff")
                norm[nk] = v
            rows.append(norm)


    products: Dict[int, Tuple[int, str, str, str]] = {}
    factors: List[Tuple[Any, ...]] = []

    required = {"product_no", "factor_seq", "factor_id", "factor_key", "category", "category_name", "product_name", "display_name", "weight"}
    missing = required - set(rows[0].keys()) if rows else required
    if missing:
        raise RuntimeError(f"reg_factor_v4_1.csv missing columns: {sorted(missing)}; got={list(rows[0].keys()) if rows else 'NO ROWS'}")

    for r in rows:
        product_no = int(r["product_no"])
        product_name = r["product_name"].strip()
        category = r["category"].strip()
        category_name = r["category_name"].strip()

        products[product_no] = (product_no, product_name, category, category_name)

        factor_id = int(r["factor_id"])
        factor_seq = int(r["factor_seq"])

        review_mentions_raw = (r.get("review_mentions") or "").strip()
        review_mentions = int(review_mentions_raw) if review_mentions_raw else None

        factors.append(
            (
                factor_id,
                product_no,
                factor_seq,
                r["factor_key"].strip(),
                category,
                category_name,
                product_name,
                (r.get("regret_type") or None),
                r["display_name"].strip(),
                (r.get("description") or None),
                (r.get("anchor_terms") or None),
                (r.get("context_terms") or None),
                (r.get("negation_terms") or None),
                float(r["weight"]),
                review_mentions,
            )
        )

    with conn.cursor() as cur:
        upsert_reference_version(cur, "reg_factor_v4_1", f"Loaded from {os.path.basename(reg_factor_csv)}")

        # ref_products upsert
        cur.executemany(
            """
            INSERT INTO ref_products(product_no, product_name, category, category_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (product_no) DO UPDATE SET
              product_name = EXCLUDED.product_name,
              category = EXCLUDED.category,
              category_name = EXCLUDED.category_name
            """,
            list(products.values()),
        )

        # ref_factors upsert (PK: factor_id)
        # NOTE: uq_product_factor_seq(product_no, factor_seq)가 존재하므로,
        # 데이터 자체가 그 제약을 만족해야 합니다(정상 데이터면 OK).
        cur.executemany(
            """
            INSERT INTO ref_factors(
              factor_id, product_no, factor_seq,
              factor_key, category, category_name, product_name,
              regret_type, display_name, description,
              anchor_terms, context_terms, negation_terms,
              weight, review_mentions
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (factor_id) DO UPDATE SET
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
              review_mentions = EXCLUDED.review_mentions
            """,
            factors,
        )

    conn.commit()


def load_reg_questions(conn: psycopg.Connection, reg_question_csv: str) -> None:
    # header: question_id,factor_id,factor_key,question_text,answer_type,choices,next_factor_hint
    with open(reg_question_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    questions: List[Tuple[Any, ...]] = []
    for r in rows:
        questions.append(
            (
                int(r["question_id"]),
                int(r["factor_id"]),
                r["factor_key"].strip(),
                r["question_text"].strip(),
                r["answer_type"].strip(),
                (r.get("choices") or None),
                (r.get("next_factor_hint") or None),
            )
        )

    with conn.cursor() as cur:
        upsert_reference_version(cur, "reg_question_v6", f"Loaded from {os.path.basename(reg_question_csv)}")

        cur.executemany(
            """
            INSERT INTO ref_questions(
              question_id, factor_id, factor_key, question_text, answer_type, choices, next_factor_hint
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (question_id) DO UPDATE SET
              factor_id = EXCLUDED.factor_id,
              factor_key = EXCLUDED.factor_key,
              question_text = EXCLUDED.question_text,
              answer_type = EXCLUDED.answer_type,
              choices = EXCLUDED.choices,
              next_factor_hint = EXCLUDED.next_factor_hint
            """,
            questions,
        )

    conn.commit()


def load_reviews(conn: psycopg.Connection, reference_dir: str) -> None:
    # 파일명: 01_reviews_smartstore_*.json ~ 10_reviews_smartstore_*.json
    pattern = os.path.join(reference_dir, "[0-9][0-9]_reviews_smartstore_*.json")
    paths = sorted(glob.glob(pattern))

    to_insert: List[Tuple[Any, ...]] = []

    for path in paths:
        base = os.path.basename(path)
        try:
            product_no = int(base.split("_", 1)[0])
        except Exception:
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            continue

        for item in data:
            if not isinstance(item, dict):
                continue
            review_id = int(item["review_id"])
            rating = item.get("rating")
            rating = int(rating) if rating is not None else None
            text = (item.get("text") or "").strip()
            created_at = parse_timestamptz(item.get("created_at"))

            to_insert.append((product_no, review_id, rating, text, created_at))

    with conn.cursor() as cur:
        upsert_reference_version(cur, "smartstore_reviews", f"Loaded {len(paths)} files from {reference_dir}")

        cur.executemany(
            """
            INSERT INTO ref_reviews(product_no, review_id, rating, text, created_at)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (product_no, review_id) DO UPDATE SET
              rating = EXCLUDED.rating,
              text = EXCLUDED.text,
              created_at = EXCLUDED.created_at
            """,
            to_insert,
        )

    conn.commit()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", default="backend/data/reference")
    ap.add_argument("--reg-factor", default="reg_factor_v4_1.csv")
    ap.add_argument("--reg-question", default="reg_question_v6.csv")
    args = ap.parse_args()

    cfg = PgConfig.from_env()
    ref_dir = args.reference_dir
    reg_factor_path = os.path.join(ref_dir, args.reg_factor)
    reg_question_path = os.path.join(ref_dir, args.reg_question)

    with psycopg.connect(cfg.dsn()) as conn:
        conn.execute("SET TIME ZONE 'UTC';")
        load_reg_factors(conn, reg_factor_path)
        load_reg_questions(conn, reg_question_path)
        load_reviews(conn, ref_dir)


if __name__ == "__main__":
    main()
