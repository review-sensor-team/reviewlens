"""
Initialize ReviewLens DB for local/dev.

Steps
- Apply reference/runtime schemas via dockerized psql
- Load reference datasets into ref_* tables
- Print basic verification outputs
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

import psycopg
from dotenv import load_dotenv


# ----------------------------
# Paths / env
# ----------------------------

def project_root() -> Path:
    # db/scripts/init_db.py -> repo root
    return Path(__file__).resolve().parents[2]


def env_required(key: str, default: str | None = None) -> str:
    v = os.getenv(key, default)
    if v is None or v == "":
        raise RuntimeError(f"{key} is empty. Set it in .env.")
    return v


def pg_dsn_from_env() -> str:
    host = env_required("POSTGRES_HOST", "localhost")
    port = env_required("POSTGRES_PORT", "5432")
    dbname = env_required("POSTGRES_DB", "reviewlens")
    user = env_required("POSTGRES_USER", "postgres")
    password = env_required("POSTGRES_PASSWORD")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


# ----------------------------
# Subprocess helpers
# ----------------------------

def _run(cmd: List[str]) -> subprocess.CompletedProcess:
    # Intentionally not check=True to keep full stdout/stderr in our errors.
    return subprocess.run(cmd, capture_output=True, text=True)


def _fmt_cmd(cmd: List[str]) -> str:
    return " ".join(cmd)


# ----------------------------
# Docker helpers
# ----------------------------

def postgres_container_id(compose_file: str) -> str:
    """
    Return container id for docker compose service 'postgres'.
    Works regardless of auto-generated container names.
    """
    cmd = ["docker", "compose", "-f", compose_file, "ps", "-q", "postgres"]
    r = _run(cmd)
    if r.returncode != 0:
        raise RuntimeError(
            "Cannot get postgres container id.\n"
            f"CMD: {_fmt_cmd(cmd)}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        )
    cid = r.stdout.strip()
    if not cid:
        raise RuntimeError(
            "Postgres container is not running or not found.\n"
            f"Run: docker compose -f {compose_file} up -d"
        )
    return cid


def wait_for_postgres(compose_file: str, retries: int = 20, sleep_sec: float = 1.0) -> None:
    """
    Best-effort readiness check (avoids race right after 'up -d').
    Uses psql inside container so host does not need psql installed.
    """
    user = os.getenv("POSTGRES_USER", "postgres")
    db = os.getenv("POSTGRES_DB", "reviewlens")

    cmd = [
        "docker", "compose", "-f", compose_file,
        "exec", "-T", "postgres",
        "psql", "-U", user, "-d", db,
        "-v", "ON_ERROR_STOP=1",
        "-c", "select 1;"
    ]

    last = None
    for _ in range(retries):
        r = _run(cmd)
        if r.returncode == 0:
            return
        last = r
        time.sleep(sleep_sec)

    assert last is not None
    raise RuntimeError(
        "Postgres is not ready.\n"
        f"CMD: {_fmt_cmd(cmd)}\nSTDOUT:\n{last.stdout}\nSTDERR:\n{last.stderr}"
    )


def run_psql_file_via_docker(sql_path: Path, compose_file: str) -> None:
    """
    Apply a .sql file using psql inside the postgres container.

    Approach:
    - docker cp <host_sql> <container>:/tmp/<name>.sql
    - docker compose exec postgres psql -f /tmp/<name>.sql
    """
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    cid = postgres_container_id(compose_file)

    src = str(sql_path.resolve())
    dst = f"/tmp/{sql_path.name}"

    # 1) Copy SQL into container
    cmd_cp = ["docker", "cp", src, f"{cid}:{dst}"]
    r1 = _run(cmd_cp)
    if r1.returncode != 0:
        raise RuntimeError(
            f"docker cp failed for {sql_path.name}\n"
            f"CMD: {_fmt_cmd(cmd_cp)}\nSTDOUT:\n{r1.stdout}\nSTDERR:\n{r1.stderr}"
        )

    # 2) Execute SQL inside container
    user = os.getenv("POSTGRES_USER", "postgres")
    db = os.getenv("POSTGRES_DB", "reviewlens")
    cmd_psql = [
        "docker", "compose", "-f", compose_file,
        "exec", "-T", "postgres",
        "psql", "-v", "ON_ERROR_STOP=1",
        "-U", user, "-d", db, "-f", dst
    ]
    r2 = _run(cmd_psql)
    if r2.returncode != 0:
        raise RuntimeError(
            f"psql failed for {sql_path.name}\n"
            f"CMD: {_fmt_cmd(cmd_psql)}\nSTDOUT:\n{r2.stdout}\nSTDERR:\n{r2.stderr}"
        )


# ----------------------------
# Verification (no GUI)
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
        for product_no, cnt in cur.fetchall():
            print(f"- product_no={int(product_no):02d}: {cnt}")


# ----------------------------
# Main
# ----------------------------

def main() -> None:
    load_dotenv()

    root = project_root()

    # Use absolute compose path so script can be run from any cwd.
    compose_file = str(root / "docker-compose.db.yml")

    schema_reference = root / "db" / "schema" / "schema_reference.sql"
    schema_runtime = root / "db" / "schema" / "schema_runtime.sql"
    reference_dir = root / "backend" / "data" / "reference"

    # Allow importing "db.scripts.*" when running as a script (Windows-friendly)
    sys.path.insert(0, str(root))

    # Fail fast on missing env vars.
    _ = pg_dsn_from_env()

    try:
        print("[INIT] Wait for postgres")
        wait_for_postgres(compose_file)

        print("[INIT] Apply schema_reference.sql (via docker psql)")
        run_psql_file_via_docker(schema_reference, compose_file)

        print("[INIT] Apply schema_runtime.sql (via docker psql)")
        run_psql_file_via_docker(schema_runtime, compose_file)

        print("[INIT] Load reference data (via psycopg)")
        dsn = pg_dsn_from_env()
        with psycopg.connect(dsn) as conn:
            conn.execute("SET TIME ZONE 'UTC';")

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
