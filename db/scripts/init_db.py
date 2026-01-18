"""
db/scripts/init_db.py
=====================

Goal (MVP):
- No GUI (no DBeaver/psql install on host)
- Docker-based PostgreSQL (no local Postgres install)
- One command to:
  1) Apply schemas (reference + runtime)
  2) Load reference data (CSV/JSON)
  3) Print verification outputs

Usage (Windows PowerShell):
  .\.venv\Scripts\python.exe db\scripts\init_db.py

Prerequisites:
- Docker Desktop running
- docker-compose.db.yml up -d (postgres/redis)
- .env exists (copied from .env.example) and includes POSTGRES_PASSWORD
- pip install: psycopg[binary], python-dotenv
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import psycopg
from dotenv import load_dotenv


# ----------------------------
# Environment / Path utilities
# ----------------------------

def project_root() -> Path:
    # db/scripts/init_db.py -> repo root
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


# ----------------------------
# Docker helpers
# ----------------------------

def _run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def postgres_container_id(compose_file: str = "docker-compose.db.yml") -> str:
    """
    Return container id for docker compose service 'postgres'.
    Works regardless of auto-generated container names (e.g., reviewlens-postgres-1).
    """
    cmd = ["docker", "compose", "-f", compose_file, "ps", "-q", "postgres"]
    r = _run(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"Cannot get postgres container id.\nCMD: {' '.join(cmd)}\nSTDERR:\n{r.stderr}")
    cid = r.stdout.strip()
    if not cid:
        raise RuntimeError(
            "Postgres container is not running or not found. "
            "Run: docker compose -f docker-compose.db.yml up -d"
        )
    return cid


def run_psql_file_via_docker(sql_path: Path, compose_file: str = "docker-compose.db.yml") -> None:
    """
    Apply a .sql file using psql inside the postgres container.

    Why:
    - Avoid fragile SQL splitting/parsing in Python
    - Avoid Windows path visibility issue in container
    Approach:
    - docker cp <host_sql> <container>:/tmp/<name>.sql
    - docker compose exec postgres psql -f /tmp/<name>.sql
    """
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    cid = postgres_container_id(compose_file=compose_file)

    src = str(sql_path.resolve())
    dst = f"/tmp/{sql_path.name}"

    # 1) Copy SQL into container
    r1 = _run(["docker", "cp", src, f"{cid}:{dst}"])
    if r1.returncode != 0:
        raise RuntimeError(f"docker cp failed for {sql_path.name}\nSTDERR:\n{r1.stderr}")

    # 2) Execute SQL inside container
    user = os.getenv("POSTGRES_USER", "postgres")
    db = os.getenv("POSTGRES_DB", "reviewlens")

    r2 = _run([
        "docker", "compose", "-f", compose_file,
        "exec", "-T", "postgres",
        "psql", "-v", "ON_ERROR_STOP=1",  # stop on first error, propagate non-zero
        "-U", user, "-d", db, "-f", dst
    ])
    if r2.returncode != 0:
        raise RuntimeError(
            f"psql failed for {sql_path.name}\nSTDOUT:\n{r2.stdout}\nSTDERR:\n{r2.stderr}"
        )


# ----------------------------
# Verification helpers (no GUI)
# ----------------------------

def verify_counts(conn: psycopg.Connection) -> None:
    checks: List[Tuple[str, str]] = [
        ("ref_products", "select count(*) from ref_products;"),
        ("ref_factors", "select count(*) from ref_factors;"),
        ("ref_questions", "select count(*) from ref_questions;"),
        ("ref_reviews", "select count(*) from ref_reviews;"),
    ]
    with conn.cursor() as cur:
        print("\n[VERIFY] Row counts")
        for name, q in checks:
            cur.execute(q)
            n = cur.fetchone()[0]
            print(f"- {name}: {n}")

        print("\n[VERIFY] Reviews per product_no")
        cur.execute(
            "select product_no, count(*) "
            "from ref_reviews "
            "group by product_no "
            "order by product_no;"
        )
        rows = cur.fetchall()
        for product_no, cnt in rows:
            print(f"- product_no={int(product_no):02d}: {cnt}")


# ----------------------------
# Main
# ----------------------------

def main() -> None:
    # Load .env into process environment
    load_dotenv()

    root = project_root()

    compose_file = "docker-compose.db.yml"

    schema_reference = root / "db" / "schema" / "schema_reference.sql"
    schema_runtime = root / "db" / "schema" / "schema_runtime.sql"
    reference_dir = root / "backend" / "data" / "reference"

    # Ensure repo root importable (for db.scripts.load_reference_data)
    sys.path.insert(0, str(root))

    # Validate env early (clear error message)
    _ = pg_dsn_from_env()

    try:
        print("[INIT] Apply schema_reference.sql (via docker psql)")
        run_psql_file_via_docker(schema_reference, compose_file=compose_file)

        print("[INIT] Apply schema_runtime.sql (via docker psql)")
        run_psql_file_via_docker(schema_runtime, compose_file=compose_file)

        print("[INIT] Load reference data (via psycopg)")
        dsn = pg_dsn_from_env()
        with psycopg.connect(dsn) as conn:
            conn.execute("SET TIME ZONE 'UTC';")

            # Import existing loader functions
            from db.scripts.load_reference_data import (  # type: ignore
                load_reg_factors,
                load_reg_questions,
                load_reviews,
            )

            load_reg_factors(conn, str(reference_dir / "reg_factor_v4_1.csv"))
            load_reg_questions(conn, str(reference_dir / "reg_question_v6.csv"))
            load_reviews(conn, str(reference_dir))

            print("[INIT] Verify")
            verify_counts(conn)

        print("\n[INIT] Done.")

    except Exception as e:
        print(f"\n[ERROR] init_db failed: {e}")
        raise


if __name__ == "__main__":
    main()
