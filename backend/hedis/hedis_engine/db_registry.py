"""DB registry loaders for HEDIS measure definitions and valuesets.

This module keeps the runtime evaluator resilient:
- Prefer DB-backed definitions when available.
- Fall back to file-based catalog/value sets when DB is unavailable.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


def _resolve_sync_db_url() -> Optional[str]:
    backend = (os.getenv("DB_BACKEND") or "auto").strip().lower()
    if backend == "postgres" or (backend == "auto" and os.getenv("POSTGRES_HOST")):
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "medinsight360")
        user = os.getenv("POSTGRES_USER", "postgres")
        pwd = os.getenv("POSTGRES_PASSWORD", "")
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
    if backend == "sqlite":
        sqlite_path = os.getenv("MEDINSIGHT_SQLITE_PATH", "outputs/medinsight360.db")
        path = Path(sqlite_path)
        if not path.exists():
            return None
        return f"sqlite:///{path}"
    return None


@lru_cache(maxsize=1)
def _get_engine() -> Optional[Engine]:
    url = _resolve_sync_db_url()
    if not url:
        return None
    try:
        return create_engine(url, future=True)
    except Exception:
        return None


def _table_exists(engine: Engine, table_name: str) -> bool:
    try:
        return inspect(engine).has_table(table_name)
    except Exception:
        return False


def load_measure_definition_dicts_from_db(active_only: bool = True) -> Optional[list[dict[str, Any]]]:
    engine = _get_engine()
    if engine is None or not _table_exists(engine, "hedis_measure_definitions"):
        return None

    where = "WHERE is_active = true" if active_only else ""
    sql = text(
        f"""
        SELECT definition_json
        FROM hedis_measure_definitions
        {where}
        ORDER BY measure_id
        """
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            payload = row[0]
            if isinstance(payload, dict):
                out.append(payload)
        return out
    except Exception:
        return None


def load_valueset_payload_from_db(valueset_id: str) -> Optional[dict[str, Any]]:
    engine = _get_engine()
    if engine is None or not _table_exists(engine, "hedis_valuesets"):
        return None

    sql = text(
        """
        SELECT payload_json
        FROM hedis_valuesets
        WHERE valueset_id = :valueset_id AND is_active = true
        LIMIT 1
        """
    )
    try:
        with engine.connect() as conn:
            row = conn.execute(sql, {"valueset_id": valueset_id}).fetchone()
        if not row:
            return None
        payload = row[0]
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None

