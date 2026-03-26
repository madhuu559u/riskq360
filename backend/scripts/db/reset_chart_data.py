#!/usr/bin/env python
"""Clear chart-derived data while preserving configuration/reference tables.

This keeps:
- system_config / llm_configs / prompt_templates
- hedis_measure_definitions / hedis_valuesets
- icd_hcc_mappings and other reference tables
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def build_url(
    db_name: str,
    db_user: str,
    db_password: str,
    db_host: str,
    db_port: str,
) -> str:
    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset chart-derived data in PostgreSQL.")
    parser.add_argument("--db-name", default=os.getenv("POSTGRES_DB", "medinsight360"))
    parser.add_argument("--db-user", default=os.getenv("POSTGRES_USER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("POSTGRES_PASSWORD", "postgres"))
    parser.add_argument("--db-host", default=os.getenv("POSTGRES_HOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("POSTGRES_PORT", "5432"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = create_engine(
        build_url(args.db_name, args.db_user, args.db_password, args.db_host, args.db_port)
    )

    with engine.begin() as conn:
        charts_before = conn.execute(text("SELECT COUNT(*) FROM charts")).scalar_one()
        conn.execute(
            text("UPDATE patients SET run_id = NULL, chart_id = NULL WHERE chart_id IS NOT NULL")
        )
        conn.execute(text("DELETE FROM charts"))
        charts_after = conn.execute(text("SELECT COUNT(*) FROM charts")).scalar_one()

    print("[reset] Chart-derived data reset complete")
    print(f"[reset] charts_before={charts_before}")
    print(f"[reset] charts_after={charts_after}")


if __name__ == "__main__":
    main()
