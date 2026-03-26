#!/usr/bin/env python
"""Bootstrap PostgreSQL database for MedInsight 360.

Creates database (if missing), creates all ORM tables, seeds:
1) ICD -> HCC mappings
2) HEDIS measure definitions (from YAML catalog)
3) HEDIS valuesets (from JSON files)
4) Active HEDIS profile (top 25 three-letter focus)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from database.models import (  # noqa: E402
    Base,
    HEDISMeasureDefinition,
    HEDISValueSet,
    ICDHCCMapping,
    SystemConfig,
)


TOP_25_HEDIS_MEASURE_IDS = [
    "AAB", "AAF", "AAP", "AMR", "APP",
    "BCS", "BPD", "CBP", "CCS", "COL",
    "DAE", "DSF", "FLU", "GSD", "KED",
    "LBP", "OED", "OMW", "POD", "PNU",
    "PSA", "SAA", "SMC", "SMD", "SPR",
]


def _checksum_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_measure_id(measure_id: str) -> str:
    return (measure_id or "").strip().upper().replace("_", "-")


def _admin_url(user: str, password: str, host: str, port: str, database: str = "postgres") -> str:
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def _db_url(user: str, password: str, host: str, port: str, database: str) -> str:
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def ensure_database_exists(admin_engine, database_name: str) -> None:
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": database_name},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{database_name}"'))
            print(f"[bootstrap] Created database: {database_name}")
        else:
            print(f"[bootstrap] Database exists: {database_name}")


def seed_icd_hcc_mappings(session: Session) -> tuple[int, int]:
    csv_path = PROJECT_ROOT / "decisioning" / "reference" / "v28_icd_hcc_mappings.csv"
    if not csv_path.exists():
        return 0, 0

    existing = session.query(ICDHCCMapping).count()
    if existing > 0:
        return existing, 0

    rows = []
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                ICDHCCMapping(
                    icd10_code=(row.get("icd10_code") or "").strip(),
                    hcc_category=(row.get("hcc_code") or "").strip(),
                    hcc_description=(row.get("hcc_description") or "").strip(),
                    raf_weight=row.get("raf_weight") or None,
                    is_payment_hcc=True,
                    model_year="V28",
                )
            )

    session.add_all(rows)
    session.flush()
    return 0, len(rows)


def seed_hedis_measure_definitions(session: Session) -> tuple[int, int]:
    catalog_dir = PROJECT_ROOT / "hedis" / "hedis_engine" / "catalog"
    if not catalog_dir.exists():
        return 0, 0

    inserted = 0
    updated = 0
    for path in sorted(catalog_dir.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict) or not payload.get("id"):
            continue
        mid = _normalize_measure_id(str(payload["id"]))
        payload["id"] = mid
        checksum = _checksum_payload(payload)

        row = session.query(HEDISMeasureDefinition).filter_by(measure_id=mid).one_or_none()
        if row is None:
            row = HEDISMeasureDefinition(
                measure_id=mid,
                version=str(payload.get("version", "2025")),
                definition_json=payload,
                source="imported",
                checksum=checksum,
                is_active=True,
                updated_by="bootstrap",
            )
            session.add(row)
            inserted += 1
        else:
            row.version = str(payload.get("version", row.version or "2025"))
            row.definition_json = payload
            row.source = "imported"
            row.checksum = checksum
            row.is_active = True
            row.updated_by = "bootstrap"
            updated += 1

    session.flush()
    return inserted, updated


def seed_hedis_valuesets(session: Session) -> tuple[int, int]:
    valuesets_dir = PROJECT_ROOT / "hedis" / "hedis_engine" / "valuesets"
    if not valuesets_dir.exists():
        return 0, 0

    inserted = 0
    updated = 0
    for path in sorted(valuesets_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        vid = str(payload.get("id") or path.stem).strip()
        if not vid:
            continue
        payload["id"] = vid
        if not isinstance(payload.get("codes"), list):
            continue

        checksum = _checksum_payload(payload)
        row = session.query(HEDISValueSet).filter_by(valueset_id=vid).one_or_none()
        if row is None:
            row = HEDISValueSet(
                valueset_id=vid,
                code_system=str(payload.get("code_system", "")) or None,
                payload_json=payload,
                source="imported",
                checksum=checksum,
                is_active=True,
                updated_by="bootstrap",
            )
            session.add(row)
            inserted += 1
        else:
            row.code_system = str(payload.get("code_system", "")) or None
            row.payload_json = payload
            row.source = "imported"
            row.checksum = checksum
            row.is_active = True
            row.updated_by = "bootstrap"
            updated += 1

    session.flush()
    return inserted, updated


def upsert_hedis_profile(session: Session) -> None:
    payload = {
        "profile_id": "top25_three_letter_focus",
        "active_measure_ids": TOP_25_HEDIS_MEASURE_IDS,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": "bootstrap",
    }
    row = session.query(SystemConfig).filter_by(config_key="hedis.measure_profile").one_or_none()
    if row is None:
        row = SystemConfig(
            config_key="hedis.measure_profile",
            config_value=payload,
            description="Active HEDIS measure profile for processing pipeline.",
            updated_by="bootstrap",
        )
        session.add(row)
    else:
        row.config_value = payload
        row.updated_by = "bootstrap"

    enrollment_row = session.query(SystemConfig).filter_by(
        config_key="hedis.assume_enrolled_if_missing"
    ).one_or_none()
    if enrollment_row is None:
        enrollment_row = SystemConfig(
            config_key="hedis.assume_enrolled_if_missing",
            config_value={"enabled": True},
            description="If enrollment evidence missing, assume member enrolled for measurement year.",
            updated_by="bootstrap",
        )
        session.add(enrollment_row)
    else:
        enrollment_row.config_value = {"enabled": True}
        enrollment_row.updated_by = "bootstrap"

    session.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap medinsight360 PostgreSQL database.")
    parser.add_argument("--db-name", default=os.getenv("POSTGRES_DB", "medinsight360"))
    parser.add_argument("--db-user", default=os.getenv("POSTGRES_USER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("POSTGRES_PASSWORD", "postgres"))
    parser.add_argument("--db-host", default=os.getenv("POSTGRES_HOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("POSTGRES_PORT", "5432"))
    parser.add_argument("--admin-user", default=os.getenv("POSTGRES_ADMIN_USER", "postgres"))
    parser.add_argument("--admin-password", default=os.getenv("POSTGRES_ADMIN_PASSWORD", "postgres"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    admin_engine = create_engine(
        _admin_url(args.admin_user, args.admin_password, args.db_host, args.db_port),
        isolation_level="AUTOCOMMIT",
    )
    ensure_database_exists(admin_engine, args.db_name)

    app_engine = create_engine(_db_url(args.db_user, args.db_password, args.db_host, args.db_port, args.db_name))
    Base.metadata.create_all(app_engine)

    with Session(app_engine) as session:
        existing_icd, inserted_icd = seed_icd_hcc_mappings(session)
        m_inserted, m_updated = seed_hedis_measure_definitions(session)
        v_inserted, v_updated = seed_hedis_valuesets(session)
        upsert_hedis_profile(session)
        session.commit()

    print("[bootstrap] Completed successfully")
    print(f"[bootstrap] ICD->HCC existing={existing_icd} inserted={inserted_icd}")
    print(f"[bootstrap] HEDIS measures inserted={m_inserted} updated={m_updated}")
    print(f"[bootstrap] HEDIS valuesets inserted={v_inserted} updated={v_updated}")
    print("[bootstrap] Active profile: top25_three_letter_focus (25 measures)")


if __name__ == "__main__":
    main()
