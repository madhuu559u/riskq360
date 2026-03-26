"""Create and bootstrap the `medinsight_codex` Postgres database.

This mirrors the current SQLAlchemy schema into a new database on the same
Postgres instance, then applies the Codex audit extensions and seeds the
ICD→HCC reference table from the checked-in CSV.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

from database.models import Base, ICDHCCMapping


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_USER = os.getenv("POSTGRES_USER", "medinsight")
DEFAULT_PASSWORD = os.getenv("POSTGRES_PASSWORD", "change_me_in_production")
DEFAULT_HOST = os.getenv("POSTGRES_HOST", "localhost")
DEFAULT_PORT = os.getenv("POSTGRES_PORT", "5432")
TARGET_DB = os.getenv("POSTGRES_CODEX_DB", "medinsight_codex")
ADMIN_USER = os.getenv("POSTGRES_ADMIN_USER", "postgres")
ADMIN_PASSWORD = os.getenv("POSTGRES_ADMIN_PASSWORD", "postgres")
MAPPING_CSV = PROJECT_ROOT / "decisioning" / "reference" / "v28_icd_hcc_mappings.csv"


def _url(database: str) -> str:
    return f"postgresql+psycopg2://{DEFAULT_USER}:{DEFAULT_PASSWORD}@{DEFAULT_HOST}:{DEFAULT_PORT}/{database}"


def _admin_url(database: str) -> str:
    return f"postgresql+psycopg2://{ADMIN_USER}:{ADMIN_PASSWORD}@{DEFAULT_HOST}:{DEFAULT_PORT}/{database}"


def ensure_database(database: str) -> None:
    engine = create_engine(_admin_url("postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{database}"'))


def seed_icd_hcc_mappings(engine) -> int:
    if not MAPPING_CSV.exists():
        return 0

    inserted = 0
    with engine.begin() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM icd_hcc_mappings")).scalar() or 0
        if existing:
            return existing

        with MAPPING_CSV.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = []
            for row in reader:
                rows.append(
                    {
                        "icd10_code": row.get("icd10_code"),
                        "hcc_category": row.get("hcc_code"),
                        "hcc_description": row.get("hcc_description"),
                        "measurement_year": 2026,
                    }
                )
            if rows:
                conn.execute(ICDHCCMapping.__table__.insert(), rows)
                inserted = len(rows)
    return inserted


def main() -> None:
    ensure_database(TARGET_DB)
    admin_engine = create_engine(_admin_url(TARGET_DB))
    Base.metadata.create_all(admin_engine)
    with admin_engine.begin() as conn:
        conn.execute(text(f'ALTER DATABASE "{TARGET_DB}" OWNER TO {DEFAULT_USER}'))
        conn.execute(text(f'GRANT ALL PRIVILEGES ON DATABASE "{TARGET_DB}" TO {DEFAULT_USER}'))
        conn.execute(text(f'GRANT ALL ON SCHEMA public TO {DEFAULT_USER}'))
        conn.execute(text(f'ALTER SCHEMA public OWNER TO {DEFAULT_USER}'))
    inserted = seed_icd_hcc_mappings(admin_engine)
    with admin_engine.begin() as conn:
        conn.execute(text(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {DEFAULT_USER}'))
        conn.execute(text(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {DEFAULT_USER}'))
        conn.execute(text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {DEFAULT_USER}'))
        conn.execute(text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {DEFAULT_USER}'))
    print(f"Bootstrapped {TARGET_DB}")
    print(f"Reference ICD-to-HCC rows present: {inserted}")


if __name__ == "__main__":
    main()
