from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path
from typing import Iterable, List, Tuple

import psycopg
from dotenv import load_dotenv


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def env_required(key: str, default: str | None = None) -> str:
    v = os.getenv(key, default)
    if v is None or v == "":
        raise RuntimeError(f"{key} is empty. Set it in .env (do NOT commit .env).")
    return v


def pg_dsn_from_env() -> str:
    host = env_required("POSTGRES_HOST", "localhost")
    port = env_required("POSTGRES_PORT", "5432")
    dbname = env_required("POSTGRES_DB", "reviewlens")
    user = env_required("POSTGRES_USER", "postgres")
    password = env_required("POSTGRES_PASSWORD")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def export_query_to_csv(conn: psycopg.Connection, query: str, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with conn.cursor() as cur:
        cur.execute(query)
        cols = [d.name for d in cur.description]
        rows = cur.fetchall()

    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)

    return len(rows)


def verify_counts(conn: psycopg.Connection) -> None:
    checks: List[Tuple[str, str]] = [
        ("ref_products", "select count(*) from ref_products;"),
        ("ref_factors", "select count(*) from ref_factors;"),
        ("ref_questions", "select count(*) from ref_questions;"),
        ("ref_reviews", "select count(*) from ref_reviews;"),
        ("dialogue_sessions", "select count(*) from dialogue_sessions;"),
        ("dialogue_turns", "select count(*) from dialogue_turns;"),
        ("llm_runs", "select count(*) from llm_runs;"),
        ("reference_data_versions", "select count(*) from reference_data_versions;"),
    ]
    with conn.cursor() as cur:
        print("\n[VERIFY] Row counts")
        for name, q in checks:
            cur.execute(q)
            n = cur.fetchone()[0]
            print(f"- {name}: {n}")


def docker_pg_dump(out_path: Path) -> None:
    """
    Optional: full SQL backup using pg_dump inside docker container.
    Requires docker compose service name 'postgres' and compose file 'docker-compose.db.yml'.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    db = os.getenv("POSTGRES_DB", "reviewlens")
    user = os.getenv("POSTGRES_USER", "postgres")

    cmd = [
        "docker", "compose", "-f", "docker-compose.db.yml",
        "exec", "-T", "postgres",
        "pg_dump", "-U", user, "-d", db
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"pg_dump failed\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")

    out_path.write_text(r.stdout, encoding="utf-8")


def main() -> None:
    load_dotenv()
    root = project_root()

    out_dir = root / "out" / "db_exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    dsn = pg_dsn_from_env()
    with psycopg.connect(dsn) as conn:
        conn.execute("SET TIME ZONE 'UTC';")

        verify_counts(conn)

        exports: List[Tuple[str, str, Path]] = [
            ("ref_products", "select * from ref_products order by product_no;", out_dir / "ref_products.csv"),
            ("ref_factors", "select * from ref_factors order by product_no, factor_seq;", out_dir / "ref_factors.csv"),
            ("ref_questions", "select * from ref_questions order by question_id;", out_dir / "ref_questions.csv"),
            ("ref_reviews", "select * from ref_reviews order by product_no, review_id;", out_dir / "ref_reviews.csv"),
        ]

        print("\n[EXPORT] CSV")
        for name, q, path in exports:
            n = export_query_to_csv(conn, q, path)
            print(f"- {name}: {n} rows -> {path.relative_to(root)}")

    # Optional: full dump
    dump_path = root / "out" / "db_backups" / "reviewlens_dump.sql"
    print("\n[BACKUP] pg_dump (docker)")
    docker_pg_dump(dump_path)
    print(f"- dump -> {dump_path.relative_to(root)}")

    print("\n[DONE]")


if __name__ == "__main__":
    main()
