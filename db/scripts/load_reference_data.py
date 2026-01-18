"""
load_reference_data.py
======================

[목적]
- ReviewLens 서비스에서 사용하는 Reference Data를
  PostgreSQL 데이터베이스에 "정식 테이블(ref_*)"로 적재하는 스크립트이다.

- 기존 CSV/JSON 파일을 런타임마다 직접 읽는 방식은
  ▶ 로딩 속도가 느리고
  ▶ 분석/집계(SQL) 활용이 어렵기 때문에
  ▶ Reference Data를 DB로 이전(DB화)한다.

[적재 대상]
1) ref_products
   - 상품 단위 기준 테이블 (MVP: 10개 상품 고정)
   - product_no (PK)를 기준으로 모든 데이터가 연결됨

2) ref_factors
   - 후회 요인(REG Factor)
   - factor_id 규칙:
       101~110   → product_no = 1
       201~210   → product_no = 2
       ...
       1001~1010 → product_no = 10
   - product_no + factor_seq 구조로 정규화됨

3) ref_questions
   - 대화 질문 템플릿
   - factor_id / factor_key 기반으로 factor와 연결

4) ref_reviews
   - SmartStore 등에서 수집한 리뷰 원문
   - product_no + review_id 기준으로 저장

[언제 실행하는가]
- DB 스키마(schema_reference.sql, schema_runtime.sql)를 적용한 이후
- Reference Data(CSV/JSON)를 최초 적재할 때
- 또는 Reference Data 버전(reg_factor_v2 → v3 등)이 변경되었을 때

※ 일반적인 API 요청/서비스 실행 시에는 호출하지 않는다.

[중요 설계 원칙]
- Reference Data는 "읽기 전용" 성격
- 서비스 실행 중 자동 갱신/재적재 하지 않음
- 재적재가 필요할 경우 이 스크립트를 수동 실행

[적재 실행 커맨드]
python db/scripts/load_reference_data.py `
  --db-url "postgresql://postgres:sqsq2601@localhost:5432/reviewlens" `
  --factors "backend/data/reference/reg_factor_v4_1.csv" `
  --questions "backend/data/reference/reg_question_v6.csv" `
  --reviews-glob "backend/data/reference/*_reviews_smartstore_*.json" `
  --strict-product-no `
  --source-name "reg_factor_v4_1+reg_question_v6+reviews_smartstore"

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
