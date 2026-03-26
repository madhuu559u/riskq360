#!/usr/bin/env python
"""MedInsight 360 - Batch Chart Processing via 5-Pipeline Parallel Extraction.

Processes medical chart PDFs through:
  1. Smart PDF extraction (text + quality scoring + vision OCR fallback)
  2. 5 parallel LLM extraction pipelines (demographics, sentences, risk dx, HEDIS, encounters)
  3. HCC mapping (ICD-10 -> HCC V28 + hierarchy suppression + RAF)
  4. HEDIS measure evaluation
  5. JSON output file generation
  6. Database persistence

Usage:
  python scripts/process_charts.py                          # Process all PDFs in uploads/
  python scripts/process_charts.py --input-dir ./my_charts  # Custom folder
  python scripts/process_charts.py --pdf chart.pdf           # Single PDF
  python scripts/process_charts.py --api-key sk-...          # Override API key
  python scripts/process_charts.py --no-vision               # Skip vision OCR
  python scripts/process_charts.py --no-db                   # Skip DB persistence
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from openai import OpenAI

from extraction.smart_pdf import smart_extract_pdf, basic_extract_pdf, score_text_quality
from extraction.parallel_extractor import run_all_extractions, safe_parse_json, chunk_text
from extraction.prompts import PIPELINE_PROMPTS
from extraction.hedis_fallback import extract_hedis_fallback_artifacts

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("medinsight360")


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_UPLOADS_DIR = PROJECT_ROOT / "uploads"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_VISION_MODEL = "gpt-4o"
DEFAULT_QUALITY_THRESHOLD = 50
DEFAULT_CHUNK_SIZE = 10000
MAX_PIPELINE_WORKERS = 5
MAX_CHUNK_WORKERS = 4
MAX_PARALLEL_PDFS = 3
DEFAULT_MEASUREMENT_YEAR = 2026

# Top-25 focused profile (mostly 3-letter HEDIS measures).
TOP_25_HEDIS_MEASURE_IDS = [
    "AAB", "AAF", "AAP", "AMR", "APP",
    "BCS", "BPD", "CBP", "CCS", "COL",
    "DAE", "DSF", "FLU", "GSD", "KED",
    "LBP", "OED", "OMW", "POD", "PNU",
    "PSA", "SAA", "SMC", "SMD", "SPR",
]


def _load_active_hedis_measure_ids(db_url: Optional[str]) -> Optional[List[str]]:
    """Resolve active HEDIS measure IDs from env override or DB config."""
    env_ids = os.getenv("HEDIS_ACTIVE_MEASURE_IDS", "").strip()
    if env_ids:
        parsed = [m.strip().upper().replace("_", "-") for m in env_ids.split(",") if m.strip()]
        if parsed:
            return parsed

    if not db_url:
        return None

    try:
        from sqlalchemy import create_engine, text
    except Exception:
        return None

    try:
        if db_url == "postgres":
            from database.connection import sync_engine

            engine = sync_engine
        else:
            engine = create_engine(db_url, future=True)
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT config_value FROM system_config WHERE config_key = :key"),
                {"key": "hedis.measure_profile"},
            ).fetchone()
        if not row:
            return None
        raw = row[0]
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                return None
        if not isinstance(raw, dict):
            return None
        ids = raw.get("active_measure_ids", [])
        parsed = [str(m).strip().upper().replace("_", "-") for m in ids if str(m).strip()]
        return parsed or None
    except Exception as e:
        log.warning("Unable to load HEDIS measure profile from DB URL %s: %s", db_url, e)
        return None


# ---------------------------------------------------------------------------
# HCC Post-Processing (from risk pipeline output)
# ---------------------------------------------------------------------------

def process_hcc_from_risk(
    risk_data: Dict[str, Any],
    clinical_text: str = "",
    client: Optional[Any] = None,
    model: str = "gpt-4o-mini",
    enable_ensemble: bool = True,
) -> Dict[str, Any]:
    """Map ICD-10 codes from risk extraction to HCC categories and compute RAF.

    When enable_ensemble=True (default), runs the 4-track ensemble:
      Track 1: LLM extraction (ICD→HCC from Pipeline 3 diagnoses)
      Track 2: TF-IDF classifier (multi-label HCC from clinical text)
      Track 3: BioClinicalBERT (deep learning HCC prediction)
      Track 4: LLM verification gate (confirms each HCC with evidence)

    Falls back to LLM-only mapping if ensemble components aren't available.
    """
    try:
        from decisioning.hcc_mapper import HCCMapper

        ref_dir = PROJECT_ROOT / "decisioning" / "reference"
        mapper = HCCMapper(ref_dir)
    except Exception as e:
        log.warning("HCC mapper not available, using basic mapping: %s", e)
        return _basic_hcc_mapping(risk_data)

    # Try ensemble first
    if enable_ensemble and clinical_text:
        try:
            from core.hcc_ensemble import run_ensemble_hcc, EnsembleConfig

            cfg = EnsembleConfig()
            result = run_ensemble_hcc(
                risk_data=risk_data,
                clinical_text=clinical_text,
                hcc_mapper=mapper,
                client=client,
                model=model,
                config=cfg,
            )
            return result
        except Exception as e:
            log.warning("Ensemble failed, falling back to LLM-only: %s", e)

    # Fallback: LLM-only mapping (original logic)
    return _llm_only_hcc_mapping(risk_data, mapper)


def _llm_only_hcc_mapping(risk_data: Dict[str, Any], mapper: Any) -> Dict[str, Any]:
    """LLM-only HCC mapping fallback (no TF-IDF/BERT/verification)."""
    diagnoses = risk_data.get("diagnoses", [])
    mapper._load()

    hcc_to_icds: Dict[str, List[Dict]] = {}
    unmapped: List[Dict] = []
    active_count = 0
    negated_count = 0

    for dx in diagnoses:
        icd10 = (dx.get("icd10_code") or "").strip().upper()
        neg_status = (dx.get("negation_status") or "active").lower()

        if neg_status != "active":
            if neg_status == "negated":
                negated_count += 1
            continue

        active_count += 1
        if not icd10:
            continue

        mapping = mapper._icd_to_hcc.get(icd10)
        if not mapping:
            mapping = mapper._icd_to_hcc.get(icd10.replace(".", ""))
        if not mapping and len(icd10) > 3 and "." not in icd10:
            mapping = mapper._icd_to_hcc.get(icd10[:3] + "." + icd10[3:])

        if not mapping:
            unmapped.append(dx)
            continue

        hcc_code = mapping.get("hcc_code", "")
        if not hcc_code:
            unmapped.append(dx)
            continue

        if hcc_code not in hcc_to_icds:
            hcc_to_icds[hcc_code] = []
        hcc_to_icds[hcc_code].append({
            "icd10_code": icd10,
            "description": dx.get("description", ""),
            "hcc_code": hcc_code,
            "hcc_description": mapping.get("hcc_description", ""),
            "raf_weight": mapping.get("raf_weight", 0),
            "supporting_text": dx.get("supporting_text", ""),
            "date_of_service": dx.get("date_of_service"),
            "provider": dx.get("provider"),
            "source_section": dx.get("source_section"),
        })

    active_hccs = set(hcc_to_icds.keys())
    suppressed: Dict[str, str] = {}

    for group in mapper._hierarchy_groups:
        ordered = group.get("ordered_hccs", [])
        present = [h for h in ordered if h in active_hccs]
        if len(present) <= 1:
            continue
        winner = present[0]
        for loser in present[1:]:
            if loser not in suppressed:
                suppressed[loser] = winner

    payable_hccs = []
    suppressed_hccs = []
    total_raf = 0.0

    for hcc_code, icd_list in hcc_to_icds.items():
        entry = {
            "hcc_code": hcc_code,
            "hcc_description": icd_list[0].get("hcc_description", ""),
            "raf_weight": icd_list[0].get("raf_weight", 0),
            "confidence": 0.9,
            "source": "llm",
            "llm_verified": None,
            "llm_confidence": None,
            "supported_icds": icd_list,
            "icd_count": len(icd_list),
        }
        if hcc_code in suppressed:
            entry["suppressed_by"] = suppressed[hcc_code]
            suppressed_hccs.append(entry)
        else:
            payable_hccs.append(entry)
            total_raf += entry["raf_weight"]

    return {
        "payable_hccs": payable_hccs,
        "suppressed_hccs": suppressed_hccs,
        "unmapped_icds": unmapped,
        "unsupported_candidates": [],
        "raf_summary": {
            "total_raf_score": round(total_raf, 3),
            "hcc_raf": round(total_raf, 3),
            "demographic_raf": 0.0,
            "hcc_count": len(hcc_to_icds),
            "payable_hcc_count": len(payable_hccs),
            "suppressed_hcc_count": len(suppressed_hccs),
            "unmapped_icd_count": len(unmapped),
        },
        "diagnosis_summary": {
            "total_diagnoses": len(diagnoses),
            "active_diagnoses": active_count,
            "negated_diagnoses": negated_count,
        },
        "ensemble_metadata": {
            "ensemble_version": "llm_only",
            "tracks_enabled": {"llm": True, "tfidf": False, "bert": False, "llm_verification": False},
            "track_predictions": {"llm": len(hcc_to_icds), "tfidf": 0, "bert": 0},
        },
    }


def _basic_hcc_mapping(risk_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback HCC mapping when the full mapper isn't available."""
    diagnoses = risk_data.get("diagnoses", [])
    active = [d for d in diagnoses if (d.get("negation_status") or "active") == "active"]
    return {
        "payable_hccs": [],
        "suppressed_hccs": [],
        "unmapped_icds": active,
        "raf_summary": {
            "total_raf_score": 0.0,
            "hcc_count": 0,
            "payable_hcc_count": 0,
            "total_diagnoses": len(diagnoses),
            "active_diagnoses": len(active),
        },
    }


# ---------------------------------------------------------------------------
# Extraction hardening helpers
# ---------------------------------------------------------------------------

_DATE_TOKEN_RE = re.compile(r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}/\d{1,2}/(?:19|20)?\d{2})\b")


def _try_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        if isinstance(val, str):
            cleaned = val.strip().replace("%", "")
            if not cleaned:
                return None
            return float(cleaned)
        return float(val)
    except Exception:
        return None


def _is_plausible_bp(sys_val: Any, dia_val: Any) -> bool:
    s = _try_float(sys_val)
    d = _try_float(dia_val)
    if s is None or d is None:
        return False
    if not (70 <= s <= 260 and 40 <= d <= 160):
        return False
    if s <= d:
        return False
    return True


def _parse_flexible_date(raw: Any) -> Optional[date]:
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except Exception:
        return None


def _extract_best_event_date_from_text(text: str, measurement_year: int) -> Optional[str]:
    if not text:
        return None
    lower = text.lower()
    if "dob" in lower or "date of birth" in lower:
        # Still allow service-date lines that also include DOB by picking the newest date.
        pass
    candidates: List[date] = []
    for m in _DATE_TOKEN_RE.finditer(text):
        dt = _parse_flexible_date(m.group(1))
        if dt is None:
            continue
        if dt.year < 1990 or dt.year > measurement_year + 1:
            continue
        candidates.append(dt)
    if not candidates:
        return None
    return max(candidates).isoformat()


def _normalize_event_date(raw_date: Any, *, evidence: str, measurement_year: int) -> Optional[str]:
    dt = _parse_flexible_date(raw_date)
    if dt and 1990 <= dt.year <= measurement_year + 1:
        return dt.isoformat()
    inferred = _extract_best_event_date_from_text(evidence, measurement_year)
    return inferred


def _normalize_hedis_bp_readings(
    readings: Any,
    *,
    measurement_year: int,
) -> List[Dict[str, Any]]:
    if not isinstance(readings, list):
        return []

    normalized: List[Dict[str, Any]] = []
    seen: set[Tuple[Any, ...]] = set()
    for item in readings:
        if not isinstance(item, dict):
            continue
        sys_val = item.get("systolic")
        dia_val = item.get("diastolic")
        evidence = str(item.get("evidence") or item.get("exact_quote") or "").strip()

        if not _is_plausible_bp(sys_val, dia_val):
            continue

        # Evidence context guard: avoid date fragments turning into fake BP.
        ev_lower = evidence.lower()
        has_bp_context = any(t in ev_lower for t in ("bp", "blood pressure", "b/p", "mmhg", "systolic", "diastolic"))
        if evidence and not has_bp_context:
            short_pair = bool(re.fullmatch(r"\s*\d{2,3}\s*/\s*\d{2,3}\s*", evidence))
            if not short_pair:
                continue

        normalized_date = _normalize_event_date(
            item.get("date"),
            evidence=evidence,
            measurement_year=measurement_year,
        )
        record = {
            "systolic": int(round(_try_float(sys_val) or 0)),
            "diastolic": int(round(_try_float(dia_val) or 0)),
            "date": normalized_date,
            "evidence": evidence or None,
            "page_number": item.get("page_number"),
        }
        key = (
            record["systolic"],
            record["diastolic"],
            record.get("page_number"),
            record.get("date"),
            (record.get("evidence") or "")[:160],
        )
        if key in seen:
            continue
        seen.add(key)
        normalized.append(record)
    return normalized


def _sanitize_hedis_extraction_payload(
    hedis_data: Dict[str, Any],
    *,
    measurement_year: int,
) -> Dict[str, Any]:
    """Harden extracted HEDIS payload to remove low-quality vitals/noise."""
    if not isinstance(hedis_data, dict):
        return {}
    sanitized = dict(hedis_data)
    sanitized["blood_pressure_readings"] = _normalize_hedis_bp_readings(
        hedis_data.get("blood_pressure_readings", []),
        measurement_year=measurement_year,
    )
    return sanitized


# ---------------------------------------------------------------------------
# Convert 5-pipeline output to assertions for DB persistence
# ---------------------------------------------------------------------------

def convert_to_assertions(
    extraction_results: Dict[str, Dict],
    hcc_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Convert 5-pipeline extraction results into assertion format for DB.

    Maps each pipeline's output items into the unified assertion schema
    so they can be persisted via the existing database/persist.py module.
    """
    assertions: List[Dict[str, Any]] = []
    assertion_id = 0

    # Demographics -> assertions
    demo = extraction_results.get("demographics", {})
    if demo and "_error" not in demo:
        for field in ["patient_name", "date_of_birth", "gender", "age", "insurance", "language", "race_ethnicity"]:
            val = demo.get(field)
            if val:
                assertion_id += 1
                assertions.append({
                    "assertion_id": f"demo_{assertion_id}",
                    "category": "demographics" if field != "insurance" else "administrative_code",
                    "concept": field.replace("_", " ").title(),
                    "text": f"{field}: {val}",
                    "status": "active",
                    "subject": "patient",
                    "evidence_rank": 2,
                })
        # Vitals from demographics
        for vital in demo.get("vitals", []):
            assertion_id += 1
            parts = []
            if vital.get("bp_systolic"):
                parts.append(f"BP {vital['bp_systolic']}/{vital.get('bp_diastolic', '?')}")
            if vital.get("weight"):
                parts.append(f"Weight {vital['weight']}")
            if vital.get("bmi"):
                parts.append(f"BMI {vital['bmi']}")
            assertions.append({
                "assertion_id": f"vital_{assertion_id}",
                "category": "vital_sign",
                "concept": "Vitals",
                "text": ", ".join(parts) if parts else str(vital),
                "status": "active",
                "subject": "patient",
                "evidence_rank": 2,
                "effective_date": vital.get("date"),
                "structured": {
                    "bp_systolic": vital.get("bp_systolic"),
                    "bp_diastolic": vital.get("bp_diastolic"),
                },
            })

    # Sentences -> assertions
    sentences = extraction_results.get("sentences", {})
    for s in sentences.get("sentences", []):
        assertion_id += 1
        status = "negated" if s.get("is_negated") else "active"
        assertions.append({
            "assertion_id": f"sent_{assertion_id}",
            "category": s.get("category", "unknown"),
            "concept": (s.get("negated_item") or s.get("text", ""))[:100],
            "text": s.get("text", ""),
            "status": status,
            "subject": "patient",
            "evidence_rank": 2,
            "negation_trigger": s.get("negation_trigger"),
        })

    # Risk diagnoses -> assertions
    risk = extraction_results.get("risk", {})
    for dx in risk.get("diagnoses", []):
        assertion_id += 1
        neg = (dx.get("negation_status") or "active").lower()
        icd_codes = []
        if dx.get("icd10_code"):
            icd_codes.append({"code": dx["icd10_code"], "type": "ICD-10-CM", "description": dx.get("description", "")})

        is_payable = neg == "active" and bool(dx.get("icd10_code"))
        assertions.append({
            "assertion_id": f"dx_{assertion_id}",
            "category": "diagnosis",
            "concept": dx.get("description", ""),
            "text": dx.get("supporting_text") or dx.get("description", ""),
            "exact_quote": dx.get("supporting_text") or dx.get("description", ""),
            "status": neg,
            "subject": "family_member" if neg == "family_history" else "patient",
            "evidence_rank": 1,
            "icd_codes": icd_codes,
            "icd_codes_primary": icd_codes[:1] if icd_codes else None,
            "negation_trigger": dx.get("negation_trigger"),
            "effective_date": dx.get("date_of_service"),
            "page_number": dx.get("page_number"),
            "is_payable_ra_candidate": is_payable,
            "is_hcc_candidate": is_payable,
            "is_payable_hcc_candidate": is_payable,
        })

    # HEDIS evidence -> assertions
    hedis = extraction_results.get("hedis", {})
    for bp in _normalize_hedis_bp_readings(
        hedis.get("blood_pressure_readings", []),
        measurement_year=DEFAULT_MEASUREMENT_YEAR,
    ):
        assertion_id += 1
        systolic = bp.get("systolic")
        diastolic = bp.get("diastolic")
        assertions.append({
            "assertion_id": f"hedis_bp_{assertion_id}",
            "category": "vital_sign",
            "concept": f"BP {systolic}/{diastolic}",
            "text": (
                f"BP {systolic}/{diastolic} on {bp.get('date')}"
                if bp.get("date")
                else f"BP {systolic}/{diastolic}"
            ),
            "exact_quote": bp.get("evidence") or f"BP {systolic}/{diastolic}",
            "status": "active",
            "subject": "patient",
            "evidence_rank": 1,
            "effective_date": bp.get("date"),
            "page_number": bp.get("page_number"),
            "is_hedis_evidence": True,
            "structured": {"bp_systolic": systolic, "bp_diastolic": diastolic},
        })
    for lab in hedis.get("lab_results", []):
        assertion_id += 1
        assertions.append({
            "assertion_id": f"hedis_lab_{assertion_id}",
            "category": "lab_result",
            "concept": lab.get("test_name", "Lab"),
            "text": f"{lab.get('test_name', '')}: {lab.get('result_value', '')} on {lab.get('result_date', '')}",
            "exact_quote": lab.get("evidence") or f"{lab.get('test_name', '')}: {lab.get('result_value', '')}",
            "status": "active",
            "subject": "patient",
            "evidence_rank": 1,
            "effective_date": lab.get("result_date"),
            "page_number": lab.get("page_number"),
            "is_hedis_evidence": True,
        })
    for scr in hedis.get("screenings", []):
        assertion_id += 1
        assertions.append({
            "assertion_id": f"hedis_scr_{assertion_id}",
            "category": "screening",
            "concept": scr.get("screening_type", "Screening"),
            "text": f"{scr.get('screening_type', '')}: {scr.get('result', 'no result')} on {scr.get('date', '')}",
            "exact_quote": scr.get("evidence") or f"{scr.get('screening_type', '')}: {scr.get('result', '')}",
            "status": "active",
            "subject": "patient",
            "evidence_rank": 1,
            "effective_date": scr.get("date"),
            "page_number": scr.get("page_number"),
            "is_hedis_evidence": True,
        })

    # Encounters -> assertions
    enc_data = extraction_results.get("encounters", {})
    for enc in enc_data.get("encounters", []):
        assertion_id += 1
        assertions.append({
            "assertion_id": f"enc_{assertion_id}",
            "category": "encounter",
            "concept": f"Encounter: {enc.get('type', 'office')}",
            "text": f"{enc.get('type', 'Office')} visit on {enc.get('date', '')} with {enc.get('provider', 'unknown')}",
            "exact_quote": enc.get("evidence") or f"{enc.get('type', 'Office')} visit",
            "status": "active",
            "subject": "patient",
            "evidence_rank": 1,
            "effective_date": enc.get("date"),
            "page_number": enc.get("page_number"),
            "structured": {
                "provider": enc.get("provider"),
                "facility": enc.get("facility"),
                "encounter_type": enc.get("type") or enc.get("encounter_type"),
                "chief_complaint": enc.get("chief_complaint"),
            },
        })
        # Medications from encounters
        for med in enc.get("medications", []):
            assertion_id += 1
            assertions.append({
                "assertion_id": f"med_{assertion_id}",
                "category": "medication",
                "concept": med.get("name", "Medication"),
                "text": f"{med.get('name', '')} - {med.get('instructions', '')}",
                "exact_quote": med.get("evidence") or f"{med.get('name', '')} - {med.get('instructions', '')}",
                "status": "active",
                "subject": "patient",
                "evidence_rank": 2,
                "effective_date": enc.get("date"),
                "page_number": med.get("page_number") or enc.get("page_number"),
            })

    return assertions


# ---------------------------------------------------------------------------
# DB Persistence
# ---------------------------------------------------------------------------

def persist_to_db(
    chart_name: str,
    pdf_path: str,
    assertions: List[Dict],
    hcc_data: Dict,
    hedis_data: Dict,
    page_count: int,
    elapsed: float,
    extraction_results: Optional[Dict[str, Dict]] = None,
    pages_meta: Optional[List[Dict]] = None,
    model: str = DEFAULT_MODEL,
    db_url: Optional[str] = None,
    existing_chart_id: Optional[int] = None,
    upload_source: str = "batch",
) -> Optional[Dict[str, Any]]:
    """Persist all results to the database (assertions + normalized tables)."""
    try:
        from database.persist import persist_chart_results, init_db
        engine = init_db(db_url)
        result = persist_chart_results(
            engine=engine,
            chart_name=chart_name,
            source_file=pdf_path,
            assertions=assertions,
            hcc_pack=hcc_data,
            hedis_result=hedis_data,
            measurement_year=2026,
            page_count=page_count,
            elapsed_seconds=elapsed,
            extraction_results=extraction_results,
            pages_meta=pages_meta,
            model_used=model,
            existing_chart_id=existing_chart_id,
            upload_source=upload_source,
        )
        return result
    except Exception as e:
        log.warning("DB persistence failed (non-fatal): %s", e)
        import traceback
        log.debug(traceback.format_exc())
        return None


# ---------------------------------------------------------------------------
# Single PDF Processing
# ---------------------------------------------------------------------------

def process_single_pdf(
    pdf_path: str,
    client: Any,
    model: str = DEFAULT_MODEL,
    vision_model: str = DEFAULT_VISION_MODEL,
    quality_threshold: int = DEFAULT_QUALITY_THRESHOLD,
    use_vision: bool = True,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    output_dir: Optional[str] = None,
    persist_db: bool = True,
    db_url: Optional[str] = None,
    chart_id_override: Optional[int] = None,
    upload_source: str = "batch",
) -> Dict[str, Any]:
    """Process a single PDF through the full 5-pipeline extraction."""
    start_time = time.time()
    pdf_name = Path(pdf_path).stem

    if not output_dir:
        output_dir = str(DEFAULT_OUTPUT_DIR / pdf_name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"  Processing: {Path(pdf_path).name}")
    print(f"  Model: {model} | Vision: {use_vision} | Threshold: {quality_threshold}")
    print(f"  Output: {output_dir}")
    print(f"{'='*70}")

    # --- Step 1: PDF Extraction ---
    print("\n  Step 1: Extracting text from PDF...")
    vision_results = {}
    if use_vision:
        full_text, pages_meta, vision_results, pdf_stats = smart_extract_pdf(
            pdf_path, client, vision_model=vision_model, quality_threshold=quality_threshold,
        )
        print(f"    Pages: {pdf_stats['total_pages']} | Text: {pdf_stats['text_pages']} | "
              f"Vision: {pdf_stats['vision_pages']} | Chars: {pdf_stats['total_chars']}")
    else:
        full_text, pages_meta, pdf_stats = basic_extract_pdf(pdf_path)
        print(f"    Pages: {pdf_stats['total_pages']} | Chars: {pdf_stats['total_chars']}")

    if not full_text or not full_text.strip():
        print("  ERROR: No text extracted from PDF!")
        return {"file": Path(pdf_path).name, "status": "error", "error": "No text extracted"}

    # Save raw extraction artifacts for chart-level audit traceability.
    raw_text_path = os.path.join(output_dir, "_raw_text.txt")
    with open(raw_text_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"    Saved: {Path(raw_text_path).name}")
    _save_json(os.path.join(output_dir, "_pages_meta.json"), pages_meta)
    _save_json(os.path.join(output_dir, "_chunk_map.json"), _build_chunk_map(full_text, chunk_size))

    # --- Step 2: Run 5 Extraction Pipelines in Parallel ---
    print(f"\n  Step 2: Running 5 extraction pipelines in parallel...")
    extraction_results = run_all_extractions(
        client=client,
        text=full_text,
        prompts_dict=PIPELINE_PROMPTS,
        model=model,
        max_pipeline_workers=MAX_PIPELINE_WORKERS,
        max_chunk_workers=MAX_CHUNK_WORKERS,
        chunk_size=chunk_size,
    )

    # Count results per pipeline
    for name, data in extraction_results.items():
        if "_error" in data:
            print(f"    [{name}] ERROR: {data.get('_error', 'unknown')}")
        else:
            count = _count_items(data)
            print(f"    [{name}] {count} items extracted")

    # Deterministic fallback for evidence-grounded HEDIS/risk/demographics/encounters when LLM outputs are empty.
    fallback_bundle = extract_hedis_fallback_artifacts(full_text=full_text, pdf_name=Path(pdf_path).name)
    fallback_assertions = fallback_bundle.get("assertions", [])
    fallback_encounters = (fallback_bundle.get("encounters_patch", {}) or {}).get("encounters", [])
    fallback_applied = False
    if fallback_assertions or fallback_encounters:
        hedis_current = extraction_results.get("hedis", {})
        risk_current = extraction_results.get("risk", {})
        demo_current = extraction_results.get("demographics", {})
        enc_current = extraction_results.get("encounters", {})

        hedis_is_sparse = bool(hedis_current.get("_error")) or _count_items(hedis_current) == 0
        risk_is_sparse = bool(risk_current.get("_error")) or len(risk_current.get("diagnoses", [])) == 0
        demo_is_sparse = bool(demo_current.get("_error")) or _count_items(demo_current) == 0
        enc_is_sparse = bool(enc_current.get("_error")) or len(enc_current.get("encounters", [])) == 0

        if hedis_is_sparse or risk_is_sparse or demo_is_sparse or (enc_is_sparse and fallback_encounters):
            fallback_applied = True
            print(
                f"    [fallback] Applying deterministic extractor "
                f"({len(fallback_assertions)} assertions, {len(fallback_encounters)} encounters)"
            )

            if demo_is_sparse:
                extraction_results["demographics"] = {
                    **{k: v for k, v in demo_current.items() if k != "_error"},
                    **fallback_bundle.get("demographics", {}),
                }

            if risk_is_sparse:
                extraction_results["risk"] = {
                    **{k: v for k, v in risk_current.items() if k != "_error"},
                    **fallback_bundle.get("risk_patch", {}),
                }

            if hedis_is_sparse:
                hedis_patch = fallback_bundle.get("hedis_patch", {})
                extraction_results["hedis"] = {
                    **{k: v for k, v in hedis_current.items() if k != "_error"},
                    **hedis_patch,
                }

            if enc_is_sparse and fallback_encounters:
                extraction_results["encounters"] = {
                    **{k: v for k, v in enc_current.items() if k != "_error"},
                    "encounters": fallback_encounters,
                }

    # Quality hardening for noisy HEDIS extraction fields (especially BP).
    extraction_results["hedis"] = _sanitize_hedis_extraction_payload(
        extraction_results.get("hedis", {}),
        measurement_year=DEFAULT_MEASUREMENT_YEAR,
    )

    # --- Step 3: Save Pipeline JSONs ---
    print(f"\n  Step 3: Saving extraction results...")
    file_map = {
        "demographics": "0_demographics.json",
        "sentences": "1_clinical_sentences.json",
        "risk": "2_risk_diagnoses.json",
        "hedis": "3_hedis_evidence.json",
        "encounters": "4_encounters.json",
    }
    for name, filename in file_map.items():
        _save_json(os.path.join(output_dir, filename), extraction_results.get(name, {}))
    if fallback_applied:
        _save_json(os.path.join(output_dir, "3b_hedis_fallback_evidence.json"), fallback_bundle)

    if vision_results:
        _save_json(os.path.join(output_dir, "vision_ocr.json"), vision_results)

    # --- Step 4: HCC Mapping (Ensemble V4) ---
    print(f"\n  Step 4: HCC ensemble (LLM + TF-IDF + BERT + Verification)...")
    risk_data = extraction_results.get("risk", {})
    hcc_data = process_hcc_from_risk(
        risk_data=risk_data,
        clinical_text=full_text,
        client=client,
        model=model,
    )
    _save_json(os.path.join(output_dir, "5_hcc_pack.json"), hcc_data)

    raf_score = hcc_data.get("raf_summary", {}).get("total_raf_score", 0)
    hcc_count = hcc_data.get("raf_summary", {}).get("payable_hcc_count", 0)
    dx_count = hcc_data.get("diagnosis_summary", {}).get("total_diagnoses", 0) or len(risk_data.get("diagnoses", []))
    active_dx = hcc_data.get("diagnosis_summary", {}).get("active_diagnoses", 0)
    ensemble_meta = hcc_data.get("ensemble_metadata", {})
    tracks = ensemble_meta.get("track_predictions", {})
    print(f"    Diagnoses: {dx_count} total, {active_dx} active")
    print(f"    Ensemble tracks: LLM={tracks.get('llm', 0)} TF-IDF={tracks.get('tfidf', 0)} BERT={tracks.get('bert', 0)}")
    print(f"    Verified: {ensemble_meta.get('verified_count', '?')}/{ensemble_meta.get('total_candidates', '?')} candidates")
    print(f"    HCC Categories: {hcc_count} | RAF Score: {raf_score}")

    # --- Step 5: Convert to assertions ---
    assertions = convert_to_assertions(extraction_results, hcc_data)
    if fallback_applied and fallback_assertions:
        assertions.extend(fallback_assertions)
    print(f"\n  Step 5: Converted to {len(assertions)} assertions")

    # Augment HCC pack with deterministic candidate lifecycle trace for reviewer-grade lineage.
    try:
        from core.hcc_bridge import build_hcc_pack as build_bridge_hcc_pack
        from decisioning.hcc_mapper import HCCMapper

        bridge_mapper = HCCMapper(PROJECT_ROOT / "decisioning" / "reference")
        bridge_hcc = build_bridge_hcc_pack(
            assertions=assertions,
            hcc_mapper=bridge_mapper,
            chart_id=pdf_name,
            measurement_year=2026,
        )
        hcc_data["decision_trace"] = bridge_hcc.get("decision_trace", [])
        hcc_data["candidate_summary"] = bridge_hcc.get("candidate_summary", {})
        hcc_data["bridge_hcc_pack"] = bridge_hcc
        _save_json(os.path.join(output_dir, "5_hcc_pack.json"), hcc_data)
        print(
            f"    HCC lineage: {len(hcc_data.get('decision_trace', []))} decision-trace events, "
            f"{hcc_data.get('candidate_summary', {}).get('supported_candidate_count', 0)} supported candidates"
        )
    except Exception as e:
        log.warning("HCC bridge lineage augmentation failed: %s", e)

    # --- Step 6: HEDIS Engine Evaluation (122 measures) ---
    print(f"\n  Step 6: HEDIS engine evaluation...")
    active_hedis_ids = _load_active_hedis_measure_ids(db_url)
    hedis_data = _run_hedis_engine(
        extraction_results=extraction_results,
        assertions=assertions,
        pdf_name=Path(pdf_path).name,
        measurement_year=DEFAULT_MEASUREMENT_YEAR,
        active_measure_ids_override=active_hedis_ids,
        client=client,
        model=model,
    )
    _save_json(os.path.join(output_dir, "6_hedis_quality.json"), hedis_data)
    hedis_summary = hedis_data.get("summary", {})
    print(f"    Measures evaluated: {hedis_summary.get('total_measures', 0)} | "
          f"Applicable: {hedis_summary.get('applicable', 0)} | "
          f"Met: {hedis_summary.get('met', 0)} | Gaps: {hedis_summary.get('gap', 0)}")

    # --- Step 7: Save Summary ---
    elapsed = round(time.time() - start_time, 2)
    summary = {
        "pdf_file": Path(pdf_path).name,
        "model": model,
        "vision_enabled": use_vision,
        "processing_time_seconds": elapsed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pdf_stats": pdf_stats,
        "extraction_counts": {
            "demographics_fields": _count_items(extraction_results.get("demographics", {})),
            "clinical_sentences": len(extraction_results.get("sentences", {}).get("sentences", [])),
            "diagnoses_total": dx_count,
            "diagnoses_active": active_dx,
            "hedis_bp_readings": len(extraction_results.get("hedis", {}).get("blood_pressure_readings", [])),
            "encounters": len(extraction_results.get("encounters", {}).get("encounters", [])),
        },
        "hcc_summary": hcc_data.get("raf_summary", {}),
        "hedis_summary": hedis_summary,
        "assertions_count": len(assertions),
    }
    _save_json(os.path.join(output_dir, "7_summary.json"), summary)

    # --- Step 8: DB Persistence ---
    db_result = None
    if persist_db:
        print(f"\n  Step 8: Persisting to database...")
        db_result = persist_to_db(
            chart_name=Path(pdf_path).name,
            pdf_path=str(pdf_path),
            assertions=assertions,
            hcc_data=hcc_data,
            hedis_data=hedis_data,
            page_count=pdf_stats.get("total_pages", 0),
            elapsed=elapsed,
            extraction_results=extraction_results,
            pages_meta=pages_meta,
            model=model,
            db_url=db_url,
            existing_chart_id=chart_id_override,
            upload_source=upload_source,
        )
        if db_result:
            pid = db_result.get("patient_id")
            patient_info = f", patient_id={pid}" if pid else ""
            print(f"    DB: chart_id={db_result.get('chart_id')}{patient_info}")
            print(f"    Tables: {db_result.get('tables', {})}")
        else:
            print(f"    DB: skipped or failed")

    print(f"\n  Completed in {elapsed}s -> {output_dir}")

    return {
        "file": Path(pdf_path).name,
        "status": "success" if (not persist_db or db_result is not None) else "error",
        "time": elapsed,
        "raf_score": raf_score,
        "diagnoses": dx_count,
        "active_diagnoses": active_dx,
        "hcc_count": hcc_count,
        "assertions": len(assertions),
        "sentences": len(extraction_results.get("sentences", {}).get("sentences", [])),
        "encounters": len(extraction_results.get("encounters", {}).get("encounters", [])),
        "db_result": db_result,
    }


# ---------------------------------------------------------------------------
# HEDIS Evaluation from 5-pipeline output
# ---------------------------------------------------------------------------

def _evaluate_hedis_from_extraction(results: Dict[str, Dict]) -> Dict[str, Any]:
    """Evaluate HEDIS measures from the extraction results."""
    hedis = results.get("hedis", {})
    risk = results.get("risk", {})

    # Check eligibility conditions
    conditions: Dict[str, bool] = {}
    for ec in hedis.get("eligibility_conditions", []):
        cond = (ec.get("condition") or "").lower()
        conditions[cond] = ec.get("is_present", False)

    # Also check from risk diagnoses
    for dx in risk.get("diagnoses", []):
        desc = (dx.get("description") or "").lower()
        neg = (dx.get("negation_status") or "active").lower()
        if neg == "active":
            if "diabetes" in desc or "dm" in desc:
                conditions["diabetes"] = True
            if "hypertension" in desc or "htn" in desc:
                conditions["hypertension"] = True
            if "depression" in desc:
                conditions["depression"] = True

    measures: List[Dict] = []

    # CBP - Controlling Blood Pressure
    bp_readings = hedis.get("blood_pressure_readings", [])
    has_htn = conditions.get("hypertension", False)
    bp_at_goal = any(
        (bp.get("systolic") or 999) < 140 and (bp.get("diastolic") or 999) < 90
        for bp in bp_readings
    ) if bp_readings else False
    measures.append({
        "measure_id": "CBP",
        "measure_name": "Controlling Blood Pressure",
        "applicable": has_htn,
        "compliant": bp_at_goal and has_htn,
        "status": "met" if (bp_at_goal and has_htn) else ("gap" if has_htn else "not_applicable"),
        "evidence_used": [f"BP {bp.get('systolic')}/{bp.get('diastolic')} on {bp.get('date')}" for bp in bp_readings],
    })

    # GSD - Glycemic Status
    has_dm = conditions.get("diabetes", False)
    a1c_results = [l for l in hedis.get("lab_results", []) if "a1c" in (l.get("test_name") or "").lower()]
    a1c_controlled = False
    for a1c in a1c_results:
        try:
            val = float(str(a1c.get("result_value", "")).replace("%", "").strip())
            if val < 9.0:
                a1c_controlled = True
        except (ValueError, TypeError):
            pass
    measures.append({
        "measure_id": "GSD",
        "measure_name": "Glycemic Status Assessment",
        "applicable": has_dm,
        "compliant": a1c_controlled and has_dm,
        "status": "met" if (a1c_controlled and has_dm) else ("gap" if has_dm else "not_applicable"),
        "evidence_used": [f"{l.get('test_name')}: {l.get('result_value')} on {l.get('result_date')}" for l in a1c_results],
    })

    # Screening measures
    screenings = hedis.get("screenings", [])
    screening_measures = [
        ("BCS", "Breast Cancer Screening", "mammogram"),
        ("COL", "Colorectal Cancer Screening", "colonoscopy"),
        ("CCS", "Cervical Cancer Screening", "pap_smear"),
    ]
    for mid, mname, stype in screening_measures:
        found = [s for s in screenings if stype in (s.get("screening_type") or "").lower()]
        completed = any(s.get("status") == "completed" for s in found)
        measures.append({
            "measure_id": mid,
            "measure_name": mname,
            "applicable": True,
            "compliant": completed,
            "status": "met" if completed else "gap",
            "evidence_used": [f"{s.get('screening_type')} on {s.get('date')}: {s.get('result')}" for s in found],
        })

    # DSF - Depression Screening
    dep = hedis.get("depression_screening", {})
    phq_done = bool(dep.get("phq2_score") is not None or dep.get("phq9_score") is not None)
    measures.append({
        "measure_id": "DSF",
        "measure_name": "Depression Screening and Follow-Up",
        "applicable": True,
        "compliant": phq_done,
        "status": "met" if phq_done else "gap",
        "evidence_used": [
            f"PHQ-2: {dep.get('phq2_score')}" if dep.get("phq2_score") is not None else None,
            f"PHQ-9: {dep.get('phq9_score')}" if dep.get("phq9_score") is not None else None,
        ],
    })

    # Clean up evidence lists
    for m in measures:
        m["evidence_used"] = [e for e in m.get("evidence_used", []) if e]

    met = sum(1 for m in measures if m["status"] == "met")
    gap = sum(1 for m in measures if m["status"] == "gap")
    na = sum(1 for m in measures if m["status"] == "not_applicable")

    return {
        "measures": measures,
        "eligibility_conditions": conditions,
        "summary": {
            "total_measures": len(measures),
            "met": met,
            "gap": gap,
            "not_applicable": na,
        },
    }


# ---------------------------------------------------------------------------
# Real HEDIS Engine Integration
# ---------------------------------------------------------------------------

def _run_hedis_engine(
    extraction_results: Dict[str, Dict],
    assertions: List[Dict[str, Any]],
    pdf_name: str = "",
    measurement_year: int = DEFAULT_MEASUREMENT_YEAR,
    active_measure_ids_override: Optional[List[str]] = None,
    client: Optional[Any] = None,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """Run HEDIS with a top-25 profile and strict evidence-grounded outcomes."""

    def _truthy(raw: Optional[str], default: bool = False) -> bool:
        if raw is None:
            return default
        val = str(raw).strip().lower()
        if val in {"1", "true", "yes", "y", "on"}:
            return True
        if val in {"0", "false", "no", "n", "off"}:
            return False
        return default

    extraction_results = dict(extraction_results or {})
    extraction_results["hedis"] = _sanitize_hedis_extraction_payload(
        extraction_results.get("hedis", {}),
        measurement_year=measurement_year,
    )
    assume_enrollment_if_missing = _truthy(
        os.getenv("HEDIS_ASSUME_ENROLLED_IF_MISSING"),
        default=False,
    )

    measure_defs_by_id: Dict[str, Any] = {}
    valueset_payload_cache: Dict[str, Dict[str, Any]] = {}

    def _normalize_measure_id(measure_id: str) -> str:
        return (measure_id or "").strip().upper().replace("_", "-")

    def _load_valueset_payload(valueset_id: str) -> Dict[str, Any]:
        vid = (valueset_id or "").strip()
        if not vid:
            return {}
        if vid in valueset_payload_cache:
            return valueset_payload_cache[vid]

        payload: Dict[str, Any] = {}

        # DB-first valueset resolution (matches runtime engine behavior).
        try:
            from hedis_engine.db_registry import load_valueset_payload_from_db

            db_payload = load_valueset_payload_from_db(vid)
            if isinstance(db_payload, dict):
                payload = db_payload
        except Exception:
            payload = {}

        # File fallback.
        if not payload:
            valueset_dir = PROJECT_ROOT / "hedis" / "hedis_engine" / "valuesets"
            candidates = [valueset_dir / f"{vid}.json", valueset_dir / f"{vid.lower()}.json"]
            for path in candidates:
                if path.exists():
                    try:
                        payload = json.loads(path.read_text(encoding="utf-8"))
                        break
                    except Exception:
                        payload = {}
            if not payload and valueset_dir.exists():
                for path in valueset_dir.glob("*.json"):
                    try:
                        candidate = json.loads(path.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    if str(candidate.get("id") or path.stem) == vid:
                        payload = candidate
                        break

        valueset_payload_cache[vid] = payload if isinstance(payload, dict) else {}
        return valueset_payload_cache[vid]

    def _valueset_display_name(valueset_id: str) -> str:
        payload = _load_valueset_payload(valueset_id)
        return str(payload.get("name") or valueset_id)

    def _criterion_summary(criterion: Any) -> str:
        ctype = str(getattr(criterion, "criterion_type", "") or "")
        if ctype == "procedure" and getattr(criterion, "procedure", None):
            proc = criterion.procedure
            label = _valueset_display_name(proc.valueset) if proc.valueset else "procedure criteria"
            if proc.lookback_years:
                return f"Procedure in {label} within {proc.lookback_years} year(s)"
            return f"Procedure in {label} within {proc.window_months} month(s)"
        if ctype == "diagnosis" and getattr(criterion, "diagnosis", None):
            diag = criterion.diagnosis
            label = _valueset_display_name(diag.valueset) if diag.valueset else "diagnosis criteria"
            return f"Diagnosis in {label} within {diag.lookback_months} month(s)"
        if ctype in {"lab_exists", "lab_value"} and getattr(criterion, "lab", None):
            lab = criterion.lab
            if ctype == "lab_exists":
                return f"Lab {lab.lab} documented within {lab.window_months} month(s)"
            comp = f" {lab.comparator} {lab.threshold}" if lab.comparator and lab.threshold is not None else ""
            return f"Lab {lab.lab}{comp} within {lab.window_months} month(s)"
        if ctype == "bp_controlled" and getattr(criterion, "bp", None):
            bp = criterion.bp
            return (
                f"BP below {int(bp.systolic_threshold)}/{int(bp.diastolic_threshold)} "
                f"within {bp.window_months} month(s)"
            )
        if ctype == "medication" and getattr(criterion, "medication", None):
            med = criterion.medication
            med_label = med.medication_class or _valueset_display_name(med.valueset) or "medication criteria"
            return f"Medication in {med_label} within {med.window_months} month(s)"
        if ctype == "immunization" and getattr(criterion, "immunization", None):
            imm = criterion.immunization
            label = imm.vaccine_type or _valueset_display_name(imm.valueset) or "immunization"
            if imm.window_months is None:
                return f"{label} immunization with minimum count {imm.min_count}"
            return f"{label} immunization count >= {imm.min_count} within {imm.window_months} month(s)"
        if ctype == "vital" and getattr(criterion, "vital", None):
            vital = criterion.vital
            return f"{vital.vital_type} vital documented within {vital.window_months} month(s)"
        if ctype == "encounter" and getattr(criterion, "encounter", None):
            enc = criterion.encounter
            if enc.encounter_types:
                return (
                    f"Encounter type in [{', '.join(enc.encounter_types)}] "
                    f"within {enc.window_months} month(s)"
                )
            return f"Encounter documented within {enc.window_months} month(s)"
        return criterion.description or ctype or "criteria"

    def _measure_definition_snapshot(measure_def: Any) -> Dict[str, Any]:
        denominator_rules: List[str] = []
        if getattr(measure_def, "denominator_age_only", False):
            denominator_rules.append("Age/gender eligible population")
        if getattr(measure_def, "denominator_diagnosis", None):
            diag = measure_def.denominator_diagnosis
            label = _valueset_display_name(diag.valueset) if diag.valueset else "diagnosis criteria"
            denominator_rules.append(f"Diagnosis in {label} within {diag.lookback_months} month(s)")
        if getattr(measure_def, "denominator_diagnosis_secondary", None):
            diag2 = measure_def.denominator_diagnosis_secondary
            label = _valueset_display_name(diag2.valueset) if diag2.valueset else "secondary diagnosis criteria"
            denominator_rules.append(f"Secondary diagnosis in {label} within {diag2.lookback_months} month(s)")
        if getattr(measure_def, "denominator_procedure", None):
            proc = measure_def.denominator_procedure
            label = _valueset_display_name(proc.valueset) if proc.valueset else "procedure criteria"
            denominator_rules.append(f"Procedure in {label}")
        if getattr(measure_def, "denominator_encounter", None):
            enc = measure_def.denominator_encounter
            enc_label = ", ".join(enc.encounter_types) if enc.encounter_types else "qualifying encounter"
            denominator_rules.append(f"{enc_label} within {enc.window_months} month(s)")
        if getattr(measure_def, "denominator_medication", None):
            med = measure_def.denominator_medication
            med_label = med.medication_class or _valueset_display_name(med.valueset) or "medication"
            denominator_rules.append(f"Medication in {med_label} within {med.window_months} month(s)")

        exclusion_rules: List[str] = []
        for ex in getattr(measure_def, "exclusions", []) or []:
            if getattr(ex, "description", ""):
                exclusion_rules.append(str(ex.description))
                continue
            if getattr(ex, "valueset", ""):
                exclusion_rules.append(f"{ex.exclusion_type} in {_valueset_display_name(ex.valueset)}")
            elif getattr(ex, "codes", []):
                exclusion_rules.append(f"{ex.exclusion_type} code-based exclusion")

        numerator_any = [
            _criterion_summary(c) for c in (getattr(getattr(measure_def, "numerator", None), "any_of", []) or [])
        ]
        numerator_all = [
            _criterion_summary(c) for c in (getattr(getattr(measure_def, "numerator", None), "all_of", []) or [])
        ]

        age_rule = getattr(measure_def, "age", None)
        if age_rule:
            age_text = f"{age_rule.min_age}-{age_rule.max_age} years"
        else:
            age_text = "Any age"

        gender = getattr(measure_def, "gender", None) or []
        gender_text = "all" if not gender else ", ".join(gender)

        return {
            "measure_id": getattr(measure_def, "id", ""),
            "measure_name": getattr(measure_def, "name", ""),
            "description": getattr(measure_def, "description", ""),
            "domain": getattr(measure_def, "domain", ""),
            "eligibility": {
                "age": age_text,
                "gender": gender_text,
                "continuous_enrollment_required": bool(getattr(measure_def, "continuous_enrollment", False)),
            },
            "denominator_rules": denominator_rules,
            "numerator_logic": {
                "any_of": numerator_any,
                "all_of": numerator_all,
            },
            "exclusion_rules": exclusion_rules,
            "valuesets_needed": list(getattr(measure_def, "valuesets_needed", []) or []),
            "data_sources": list(getattr(measure_def, "data_sources", []) or []),
        }

    def _humanize_gap(gap: Dict[str, Any], measure_name: str) -> Dict[str, Any]:
        enriched_gap = dict(gap)
        gap_type = str(enriched_gap.get("type") or "")
        required_event = str(enriched_gap.get("required_event") or "")
        window = str(enriched_gap.get("window") or "").strip()
        description = str(enriched_gap.get("description") or "")
        action_text = ""

        if required_event.startswith("VS_"):
            vs_payload = _load_valueset_payload(required_event)
            required_name = str(vs_payload.get("name") or required_event)
            enriched_gap["required_event_name"] = required_name
            if vs_payload.get("description"):
                enriched_gap["required_event_description"] = str(vs_payload["description"])
            if gap_type == "missing_procedure":
                action_text = f"No qualifying procedure found in {required_name}"
            elif gap_type == "missing_diagnosis":
                action_text = f"No qualifying diagnosis found in {required_name}"
            elif gap_type == "missing_medication":
                action_text = f"No qualifying medication found in {required_name}"
            else:
                action_text = f"Missing required event from {required_name}"
        elif gap_type == "missing_encounter":
            action_text = "No qualifying encounter found in required window"
        elif gap_type == "missing_lab":
            action_text = f"Required lab evidence missing for {measure_name}"
        elif gap_type == "missing_vital":
            action_text = f"Required vital evidence missing for {measure_name}"
        elif gap_type == "missing_immunization":
            action_text = f"Required immunization evidence missing for {measure_name}"

        if window and action_text:
            action_text = f"{action_text} ({window})"

        if action_text:
            enriched_gap["actionable_reason"] = action_text
            raw_is_technical = (
                not description
                or description.startswith("Missing ")
                or "VS_" in description
            )
            if raw_is_technical:
                enriched_gap["description"] = action_text
        return enriched_gap

    def _has_grounded_evidence(measure: Dict[str, Any]) -> bool:
        evidence_used = measure.get("evidence_used", []) or []
        for ev in evidence_used:
            if not isinstance(ev, dict):
                continue
            if ev.get("page_number") is not None:
                return True
            if ev.get("exact_quote"):
                return True
            src = ev.get("source")
            if isinstance(src, dict) and (src.get("page") is not None or src.get("exact_quote")):
                return True

        trace = measure.get("trace", []) or []
        for trace_entry in trace:
            for tev in trace_entry.get("evidence", []) or []:
                if tev.get("page") is not None:
                    return True
                if tev.get("exact_quote"):
                    return True
                src = tev.get("source")
                if isinstance(src, dict) and (src.get("page") is not None or src.get("exact_quote")):
                    return True
        return False

    def _enrich_measure(measure: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(measure)
        measure_id = enriched.get("measure_id") or enriched.get("id")
        measure_name = enriched.get("measure_name") or enriched.get("name")
        if measure_id:
            enriched["measure_id"] = measure_id
            enriched["id"] = measure_id
        if measure_name:
            enriched["measure_name"] = measure_name
            enriched["name"] = measure_name
        evidence_used = enriched.get("evidence_used", []) or []
        trace = enriched.get("trace", []) or []

        pages: List[int] = []
        for ev in evidence_used:
            if not isinstance(ev, dict):
                continue
            if ev.get("page_number") is not None:
                pages.append(int(ev["page_number"]))
            src = ev.get("source")
            if isinstance(src, dict) and src.get("page") is not None:
                pages.append(int(src["page"]))

        enriched["decision_reasoning"] = {
            "status": enriched.get("status"),
            "applicable": bool(enriched.get("applicable")),
            "eligibility_reason": enriched.get("eligibility_reason", []),
            "compliance_reason": enriched.get("compliance_reason", []),
            "exclusion_reason": enriched.get("exclusion_reason", ""),
            "rule_trace_count": len(trace),
            "evidence_count": len(evidence_used),
            "evidence_pages": sorted(set(pages)),
        }

        if (
            enriched.get("applicable")
            and enriched.get("status") in {"met", "gap"}
            and not _has_grounded_evidence(enriched)
        ):
            enriched["status"] = "indeterminate"
            enriched["compliant"] = None
            missing_data = list(enriched.get("missing_data", []))
            if "grounded_evidence" not in missing_data:
                missing_data.append("grounded_evidence")
            enriched["missing_data"] = missing_data
            compliance_reason = list(enriched.get("compliance_reason", []))
            compliance_reason.append(
                "Decision downgraded to indeterminate because no page-linked evidence was found."
            )
            enriched["compliance_reason"] = compliance_reason
            enriched["decision_reasoning"]["status"] = "indeterminate"

        measure_def = measure_defs_by_id.get(_normalize_measure_id(str(measure_id or "")))
        if measure_def:
            enriched["measure_definition"] = _measure_definition_snapshot(measure_def)
        if isinstance(enriched.get("gaps"), list):
            enriched["gaps"] = [
                _humanize_gap(g, str(measure_name or measure_id or "measure"))
                for g in enriched.get("gaps", [])
                if isinstance(g, dict)
            ]
        return enriched

    def _summarize(measures: List[Dict[str, Any]]) -> Dict[str, int]:
        summary = {
            "total_measures": len(measures),
            "applicable": 0,
            "met": 0,
            "gap": 0,
            "excluded": 0,
            "not_applicable": 0,
            "indeterminate": 0,
            "inactive": 0,
        }
        for measure in measures:
            if measure.get("applicable"):
                summary["applicable"] += 1
            status = measure.get("status")
            if status in summary:
                summary[status] += 1
        return summary

    def _extract_bp(assertion: Dict[str, Any]) -> Optional[tuple[float, float]]:
        structured = assertion.get("structured") or {}
        sys_val = structured.get("bp_systolic")
        dia_val = structured.get("bp_diastolic")
        if _is_plausible_bp(sys_val, dia_val):
            return float(sys_val), float(dia_val)
        text = " ".join(
            [
                str(assertion.get("exact_quote") or ""),
                str(assertion.get("text") or ""),
                str(assertion.get("concept") or ""),
            ]
        )
        m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", text)
        if m and _is_plausible_bp(m.group(1), m.group(2)):
            return float(m.group(1)), float(m.group(2))
        return None

    def _detect_hypertension_signal(assertions_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        high_bp = []
        all_bp = []
        htn_code_present = False
        anti_htn_med = []
        anti_htn_keywords = (
            "lisinopril", "losartan", "valsartan", "amlodipine", "metoprolol",
            "atenolol", "carvedilol", "hydrochlorothiazide", "chlorthalidone",
            "spironolactone", "benazepril", "enalapril", "irbesartan", "olmesartan",
            "nifedipine", "diltiazem", "verapamil", "nebivolol", "propranolol",
            "clonidine", "hydralazine",
        )
        for a in assertions_list:
            for icd in (a.get("icd_codes") or []):
                code = str(icd.get("code") or "").upper().replace(".", "")
                if code.startswith("I10") or code.startswith("I11") or code.startswith("I12") or code.startswith("I13") or code.startswith("I15"):
                    htn_code_present = True
            if (a.get("category") or "").lower() in {"vital_sign", "vitals"}:
                bp = _extract_bp(a)
                if bp:
                    entry = {
                        "systolic": bp[0],
                        "diastolic": bp[1],
                        "page_number": a.get("page_number"),
                        "exact_quote": a.get("exact_quote") or a.get("text"),
                        "effective_date": a.get("effective_date"),
                    }
                    all_bp.append(entry)
                    if bp[0] >= 140 or bp[1] >= 90:
                        high_bp.append(entry)
            if (a.get("category") or "").lower() == "medication":
                blob = " ".join(
                    [
                        str(a.get("concept") or ""),
                        str(a.get("text") or ""),
                        str(a.get("exact_quote") or ""),
                    ]
                ).lower()
                if any(k in blob for k in anti_htn_keywords):
                    anti_htn_med.append(
                        {
                            "page_number": a.get("page_number"),
                            "exact_quote": a.get("exact_quote") or a.get("text"),
                            "effective_date": a.get("effective_date"),
                        }
                    )

        return {
            "htn_code_present": htn_code_present,
            "bp_readings": all_bp,
            "high_bp_readings": high_bp,
            "antihypertensive_med_mentions": anti_htn_med,
        }

    def _evidence_from_signal(signal: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for bp in signal.get("high_bp_readings", [])[:5]:
            out.append(
                {
                    "type": "vital",
                    "code": "BP",
                    "value": f"{int(bp['systolic'])}/{int(bp['diastolic'])}",
                    "date": bp.get("effective_date"),
                    "page_number": bp.get("page_number"),
                    "exact_quote": bp.get("exact_quote"),
                }
            )
        for med in signal.get("antihypertensive_med_mentions", [])[:5]:
            out.append(
                {
                    "type": "medication",
                    "date": med.get("effective_date"),
                    "page_number": med.get("page_number"),
                    "exact_quote": med.get("exact_quote"),
                }
            )
        return out

    def _apply_clinical_denominator_hints(measures: List[Dict[str, Any]]) -> None:
        signal = _detect_hypertension_signal(assertions)
        for m in measures:
            mid = (m.get("measure_id") or m.get("id") or "").upper()
            if mid not in {"CBP", "BPD"}:
                continue
            if m.get("status") != "not_applicable":
                continue
            if signal.get("htn_code_present"):
                continue

            high_bp_count = len(signal.get("high_bp_readings", []))
            med_count = len(signal.get("antihypertensive_med_mentions", []))
            suspected = high_bp_count >= 2 or (high_bp_count >= 1 and med_count >= 1)
            if not suspected:
                continue

            preview = dict(m.get("clinical_only_preview") or {})
            preview.update(
                {
                    "status": "indeterminate",
                    "applicable": True,
                    "compliant": None,
                    "eligibility_reason": [
                        "Clinical denominator signal suggests probable hypertension despite missing coded diagnosis."
                    ],
                    "compliance_reason": [
                        f"Detected {high_bp_count} elevated BP reading(s) and {med_count} antihypertensive medication mention(s).",
                        "Strict mode keeps measure not_applicable because denominator diagnosis code set is unmet.",
                    ],
                    "gaps": [
                        {
                            "type": "missing_diagnosis",
                            "description": "Missing hypertension denominator code despite elevated BP signal.",
                            "required_event": "VS_HYPERTENSION_ICD10",
                        }
                    ],
                    "evidence_used": _evidence_from_signal(signal),
                    "trace": list(preview.get("trace") or []),
                }
            )
            m["clinical_only_preview"] = preview
            m["denominator_signal"] = {
                "suspected_denominator": True,
                "reason_code": "probable_hypertension_without_coded_denominator",
                "high_bp_count": high_bp_count,
                "antihypertensive_medication_mentions": med_count,
            }
            m["coding_opportunity"] = {
                "suggestion": "Review chart for hypertension diagnosis capture/coding specificity.",
                "valueset": "VS_HYPERTENSION_ICD10",
            }

    def _build_llm_review_prompt(measure: Dict[str, Any]) -> str:
        evidence_lines = []
        for ev in (measure.get("evidence_used") or [])[:10]:
            if not isinstance(ev, dict):
                continue
            evidence_lines.append(
                f"- page={ev.get('page_number') or (ev.get('source') or {}).get('page')}, "
                f"code={ev.get('code')}, value={ev.get('value')}, quote={str(ev.get('exact_quote') or (ev.get('source') or {}).get('exact_quote') or '')[:180]}"
            )
        if not evidence_lines:
            evidence_lines.append("- No direct evidence attached by deterministic engine.")
        return (
            "You are adjudicating a HEDIS measure outcome.\n"
            "Return strict JSON only with keys: recommended_status, confidence, rationale, missing_evidence, contradiction_found.\n"
            "recommended_status must be one of: met, gap, not_applicable, indeterminate.\n"
            f"Measure ID: {measure.get('measure_id')}\n"
            f"Measure Name: {measure.get('measure_name')}\n"
            f"Current deterministic status: {measure.get('status')}\n"
            f"Eligibility reason: {measure.get('eligibility_reason')}\n"
            f"Compliance reason: {measure.get('compliance_reason')}\n"
            f"Gaps: {measure.get('gaps')}\n"
            "Evidence:\n"
            + "\n".join(evidence_lines)
        )

    def _apply_llm_adjudication(measures: List[Dict[str, Any]]) -> None:
        llm_enabled = (os.getenv("ENABLE_HEDIS_LLM_REVIEW", "1") or "1").strip().lower() not in {"0", "false", "no"}
        if not llm_enabled or client is None:
            return
        review_targets = [
            m for m in measures
            if m.get("status") in {"gap", "indeterminate", "not_applicable"}
            and m.get("status") != "inactive"
        ][:12]
        for m in review_targets:
            try:
                prompt = _build_llm_review_prompt(m)
                resp = client.chat.completions.create(
                    model=model,
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a strict clinical quality auditor. "
                                "Never fabricate evidence. "
                                "If evidence is insufficient, choose indeterminate."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                raw = resp.choices[0].message.content or "{}"
                parsed = safe_parse_json(raw, "hedis_llm_adjudication")
                if not isinstance(parsed, dict):
                    parsed = {"raw": raw}
                m["llm_adjudication"] = {
                    "model": model,
                    "recommended_status": parsed.get("recommended_status"),
                    "confidence": parsed.get("confidence"),
                    "rationale": parsed.get("rationale"),
                    "missing_evidence": parsed.get("missing_evidence"),
                    "contradiction_found": parsed.get("contradiction_found"),
                    "raw": parsed,
                }
            except Exception as e:
                m["llm_adjudication"] = {
                    "model": model,
                    "error": str(e),
                }

    try:
        import sys as _sys
        hedis_path = str(PROJECT_ROOT / "hedis")
        if hedis_path not in _sys.path:
            _sys.path.insert(0, hedis_path)

        from hedis_engine.engine import HedisEngine
        from core.hedis_bridge import evaluate_hedis_measures

        requested_ids = active_measure_ids_override or TOP_25_HEDIS_MEASURE_IDS
        top25_ids = [_normalize_measure_id(mid) for mid in requested_ids]
        engine = HedisEngine(measurement_year=measurement_year, require_enrollment_data=True)
        measure_defs_by_id = {
            _normalize_measure_id(m.id): m for m in getattr(engine, "measures", []) if getattr(m, "id", None)
        }
        all_measure_ids = [_normalize_measure_id(m.id) for m in engine.measures]
        all_measure_set = set(all_measure_ids)
        active_measure_ids = [mid for mid in top25_ids if mid in all_measure_set]
        active_measure_set = set(active_measure_ids)
        inactive_measure_ids = sorted([mid for mid in all_measure_ids if mid not in active_measure_set])

        demo = extraction_results.get("demographics", {})
        raw_enrollment_periods = demo.get("enrollment_periods", [])
        if not isinstance(raw_enrollment_periods, list):
            raw_enrollment_periods = []
        effective_enrollment_periods = list(raw_enrollment_periods)
        enrollment_assumed = False
        if not effective_enrollment_periods and assume_enrollment_if_missing:
            enrollment_assumed = True
            effective_enrollment_periods = [
                {
                    "start_date": f"{measurement_year}-01-01",
                    "end_date": f"{measurement_year}-12-31",
                    "source": "assumed_member_enrollment",
                }
            ]
        bridge_results = evaluate_hedis_measures(
            assertions=assertions,
            measurement_year=measurement_year,
            pdf_name=pdf_name,
            dob=demo.get("dob") or demo.get("date_of_birth"),
            gender=demo.get("gender") or demo.get("sex"),
            measure_ids=active_measure_ids,
            enrollment_periods=effective_enrollment_periods,
            require_enrollment_data=True,
        )

        clinical_preview_by_id: Dict[str, Dict[str, Any]] = {}
        if not raw_enrollment_periods:
            preview_results = evaluate_hedis_measures(
                assertions=assertions,
                measurement_year=measurement_year,
                pdf_name=pdf_name,
                dob=demo.get("dob") or demo.get("date_of_birth"),
                gender=demo.get("gender") or demo.get("sex"),
                measure_ids=active_measure_ids,
                enrollment_periods=[],
                require_enrollment_data=False,
            )
            for pm in preview_results.get("measures", []):
                pm_id = pm.get("measure_id") or pm.get("id")
                if pm_id:
                    clinical_preview_by_id[pm_id] = pm

        active_results = [_enrich_measure(m) for m in bridge_results.get("measures", [])]
        if clinical_preview_by_id:
            for m in active_results:
                mid = m.get("measure_id") or m.get("id")
                preview = clinical_preview_by_id.get(mid)
                if not preview:
                    continue
                m["enrollment_dependency"] = "missing_enrollment_data_strict_mode"
                preview_payload = {
                    "status": preview.get("status"),
                    "applicable": preview.get("applicable"),
                    "compliant": preview.get("compliant"),
                    "eligibility_reason": preview.get("eligibility_reason", []),
                    "compliance_reason": preview.get("compliance_reason", []),
                    "gaps": preview.get("gaps", []),
                    "evidence_used": preview.get("evidence_used", []),
                    "trace": preview.get("trace", []),
                }
                if isinstance(preview_payload.get("gaps"), list):
                    preview_payload["gaps"] = [
                        _humanize_gap(g, str(m.get("measure_name") or m.get("measure_id") or "measure"))
                        for g in preview_payload.get("gaps", [])
                        if isinstance(g, dict)
                    ]
                m["clinical_only_preview"] = preview_payload
        if enrollment_assumed:
            for m in active_results:
                m["enrollment_dependency"] = "assumed_enrollment_if_missing"
                m["enrollment_assumption"] = {
                    "assumed": True,
                    "source": "assumed_member_enrollment",
                    "window_start": f"{measurement_year}-01-01",
                    "window_end": f"{measurement_year}-12-31",
                }
        _apply_clinical_denominator_hints(active_results)
        _apply_llm_adjudication(active_results)
        inactive_results = [
            {
                "measure_id": mid,
                "id": mid,
                "measure_name": (
                    measure_defs_by_id.get(mid).name
                    if measure_defs_by_id.get(mid) and getattr(measure_defs_by_id.get(mid), "name", "")
                    else mid
                ),
                "name": (
                    measure_defs_by_id.get(mid).name
                    if measure_defs_by_id.get(mid) and getattr(measure_defs_by_id.get(mid), "name", "")
                    else mid
                ),
                "status": "inactive",
                "applicable": False,
                "compliant": None,
                "eligibility_reason": ["Inactive by top-25 profile"],
                "compliance_reason": [],
                "gaps": [],
                "evidence_used": [],
                "trace": [],
                "decision_reasoning": {
                    "status": "inactive",
                    "applicable": False,
                    "eligibility_reason": ["Inactive by top-25 profile"],
                    "compliance_reason": [],
                    "exclusion_reason": "",
                    "rule_trace_count": 0,
                    "evidence_count": 0,
                    "evidence_pages": [],
                },
                "measure_definition": (
                    _measure_definition_snapshot(measure_defs_by_id[mid])
                    if mid in measure_defs_by_id
                    else None
                ),
            }
            for mid in inactive_measure_ids
        ]
        measures_out = active_results + inactive_results

        gaps_list: List[Dict[str, Any]] = []
        for m in active_results:
            if m.get("status") == "gap":
                for gap in m.get("gaps", []):
                    gaps_list.append(
                        {
                            "measure_id": m.get("measure_id", m.get("id")),
                            "measure_name": m.get("measure_name", m.get("name")),
                            **gap,
                        }
                    )

        return {
            "engine": "hedis_engine_v2_profiled",
            "measurement_year": measurement_year,
            "measure_profile": {
                "profile_id": "db_or_env_profile" if active_measure_ids_override else "top25_three_letter_focus",
                "active_measure_ids": active_measure_ids,
                "inactive_measure_ids": inactive_measure_ids,
            },
            "measures": measures_out,
            "gaps": gaps_list,
            "summary": _summarize(measures_out),
            "store_stats": bridge_results.get("store_stats", {}),
            "enrollment_mode": {
                "assume_if_missing": assume_enrollment_if_missing,
                "assumed_for_run": enrollment_assumed,
                "provided_periods": len(raw_enrollment_periods),
            },
        }

    except Exception as e:
        log.warning("HEDIS engine failed, falling back to simple evaluator: %s", e)
        import traceback
        log.debug(traceback.format_exc())
        return _evaluate_hedis_from_extraction(extraction_results)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_items(data: Any, depth: int = 0) -> int:
    """Count non-empty fields in a nested dict."""
    if depth > 5:
        return 0
    if isinstance(data, dict):
        count = 0
        for v in data.values():
            if isinstance(v, (dict, list)):
                count += _count_items(v, depth + 1)
            elif v is not None and v != "" and v != []:
                count += 1
        return count
    if isinstance(data, list):
        return len(data)
    return 0


def _save_json(filepath: str, data: Any) -> None:
    """Save data as formatted JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"    Saved: {Path(filepath).name}")


def _build_chunk_map(full_text: str, chunk_size: int) -> List[Dict[str, Any]]:
    """Build deterministic chunk offsets for audit traceability."""
    chunks = chunk_text(full_text, chunk_size=chunk_size)
    chunk_map: List[Dict[str, Any]] = []
    offset = 0
    for idx, chunk in enumerate(chunks, 1):
        start = full_text.find(chunk, offset)
        if start < 0:
            start = offset
        end = start + len(chunk)
        chunk_map.append({
            "chunk_index": idx,
            "start_char": start,
            "end_char": end,
            "length": len(chunk),
            "preview": chunk[:220],
        })
        offset = end
    return chunk_map


# ---------------------------------------------------------------------------
# Batch Processing
# ---------------------------------------------------------------------------

def run_batch(
    input_dir: str,
    client: Any,
    model: str = DEFAULT_MODEL,
    vision_model: str = DEFAULT_VISION_MODEL,
    quality_threshold: int = DEFAULT_QUALITY_THRESHOLD,
    use_vision: bool = True,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    output_dir: Optional[str] = None,
    max_parallel: int = MAX_PARALLEL_PDFS,
    persist_db: bool = True,
    max_files: Optional[int] = None,
    db_url: Optional[str] = None,
) -> None:
    """Process all PDFs in a directory."""
    import glob as glob_mod

    pdf_files = sorted(set(
        glob_mod.glob(os.path.join(input_dir, "*.pdf"))
        + glob_mod.glob(os.path.join(input_dir, "*.PDF"))
    ))

    if not pdf_files:
        print(f"\nNo PDF files found in: {input_dir}")
        return

    if max_files:
        pdf_files = pdf_files[:max_files]

    if not output_dir:
        output_dir = str(DEFAULT_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"  BATCH MODE: {len(pdf_files)} PDF(s)")
    print(f"  Input:    {input_dir}")
    print(f"  Output:   {output_dir}")
    print(f"  Model:    {model}")
    print(f"  Vision:   {use_vision}")
    print(f"  Parallel: {min(max_parallel, len(pdf_files))} PDFs at a time")
    print(f"{'='*70}")

    batch_start = time.time()
    batch_results: List[Dict] = []

    # Process sequentially (each PDF already uses parallel pipelines internally)
    for idx, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{idx}/{len(pdf_files)}] {Path(pdf_path).name}")
        chart_output = os.path.join(output_dir, Path(pdf_path).stem)
        try:
            result = process_single_pdf(
                pdf_path, client, model, vision_model,
                quality_threshold, use_vision, chunk_size,
                chart_output, persist_db, db_url,
            )
            batch_results.append(result)
        except Exception as e:
            print(f"\n  ERROR: {e}")
            batch_results.append({
                "file": Path(pdf_path).name,
                "status": "error",
                "error": str(e),
                "time": 0, "raf_score": 0, "diagnoses": 0, "hcc_count": 0,
            })

    # Batch Summary
    batch_elapsed = round(time.time() - batch_start, 2)
    total_raf = sum(r.get("raf_score", 0) for r in batch_results)
    total_dx = sum(r.get("diagnoses", 0) for r in batch_results)
    total_hcc = sum(r.get("hcc_count", 0) for r in batch_results)
    success_count = sum(1 for r in batch_results if r.get("status") == "success")

    batch_summary = {
        "total_charts": len(pdf_files),
        "successful": success_count,
        "failed": len(pdf_files) - success_count,
        "total_time_seconds": batch_elapsed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_context": {
            "input_dir": input_dir,
            "output_dir": output_dir,
            "model": model,
            "vision_model": vision_model,
            "quality_threshold": quality_threshold,
            "chunk_size": chunk_size,
            "persist_db": persist_db,
            "db_url": db_url or "sqlite:///outputs/medinsight360.db (default)",
            "prompt_source": "extraction/prompts.py::PIPELINE_PROMPTS",
        },
        "aggregate": {
            "total_raf_score": round(total_raf, 3),
            "avg_raf_score": round(total_raf / max(success_count, 1), 3),
            "total_diagnoses": total_dx,
            "total_hcc_categories": total_hcc,
        },
        "per_chart": batch_results,
    }
    _save_json(os.path.join(output_dir, "batch_summary.json"), batch_summary)

    # Print results table
    print(f"\n{'='*90}")
    print("  BATCH RESULTS")
    print(f"{'='*90}")
    print(f"  {'File':<35} {'Status':<10} {'Time(s)':<10} {'RAF':<10} {'Dx':<8} {'HCCs':<6} {'Assertions':<12}")
    print(f"  {'-'*85}")
    for r in batch_results:
        print(
            f"  {r.get('file','?'):<35} {r.get('status','?'):<10} "
            f"{r.get('time',0):<10.1f} {r.get('raf_score',0):<10.3f} "
            f"{r.get('diagnoses',0):<8} {r.get('hcc_count',0):<6} "
            f"{r.get('assertions',0):<12}"
        )
    print(f"  {'-'*85}")
    print(
        f"  {'TOTALS':<35} {f'{success_count}/{len(pdf_files)}':<10} "
        f"{batch_elapsed:<10.1f} {total_raf:<10.3f} {total_dx:<8} {total_hcc:<6}"
    )
    print(f"\n  Batch completed in {batch_elapsed}s")
    print(f"  Results saved to: {output_dir}")

    # DB stats + member summary
    if persist_db:
        try:
            from database.persist import get_db_stats, init_db, list_patients
            engine = init_db(db_url)
            stats = get_db_stats(engine)
            print(f"\n  Database stats: {stats}")

            # Show patient/member summary
            patients = list_patients(engine)
            if patients:
                print(f"\n  Members ({len(patients)} unique patients):")
                for p in patients:
                    print(f"    patient_id={p['patient_id']}: {p['patient_name']} "
                          f"(DOB: {p['date_of_birth']}) — {p['chart_count']} chart(s)")
        except Exception as e:
            log.debug("Could not get DB stats: %s", e)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="MedInsight 360 - Process medical chart PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python scripts/process_charts.py                           # All PDFs in uploads/
  python scripts/process_charts.py --pdf uploads/chart.pdf   # Single PDF
  python scripts/process_charts.py --max-files 3             # First 3 PDFs only
  python scripts/process_charts.py --no-vision --no-db       # Text only, skip DB
  python scripts/process_charts.py --api-key sk-proj-...     # Custom API key
  python scripts/process_charts.py --base-url https://...    # Custom API endpoint
        """,
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--pdf", help="Single PDF file to process")
    input_group.add_argument("--input-dir", default=None, help=f"Directory of PDFs (default: {DEFAULT_UPLOADS_DIR})")

    parser.add_argument("--api-key", default=None, help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--base-url", default=None, help="API base URL (for non-OpenAI providers)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Text model (default: {DEFAULT_MODEL})")
    parser.add_argument("--vision-model", default=DEFAULT_VISION_MODEL, help=f"Vision model (default: {DEFAULT_VISION_MODEL})")
    parser.add_argument("--quality-threshold", type=int, default=DEFAULT_QUALITY_THRESHOLD, help=f"Vision quality threshold (default: {DEFAULT_QUALITY_THRESHOLD})")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help=f"Chunk size (default: {DEFAULT_CHUNK_SIZE})")
    parser.add_argument("--no-vision", action="store_true", help="Disable vision OCR")
    parser.add_argument("--no-db", action="store_true", help="Skip database persistence")
    parser.add_argument(
        "--db-url",
        default=None,
        help="Database URL for persistence (example: sqlite:///run_outputs/batch10/run.db or 'postgres')",
    )
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--max-files", type=int, default=None, help="Max PDFs to process")
    parser.add_argument("--parallel", type=int, default=MAX_PARALLEL_PDFS, help=f"Max parallel PDFs (default: {MAX_PARALLEL_PDFS})")

    args = parser.parse_args()

    # Resolve API key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("\nERROR: No API key found.")
        print("Set OPENAI_API_KEY environment variable or use --api-key argument.")
        print("Example: python scripts/process_charts.py --api-key sk-proj-...")
        sys.exit(1)

    # Create client
    client_kwargs = {"api_key": api_key, "timeout": 120.0}
    base_url = args.base_url or os.getenv("OPENAI_BASE_URL", "")
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    print(f"\nAPI client configured (model: {args.model})")
    if base_url:
        print(f"  Base URL: {base_url}")

    use_vision = not args.no_vision
    persist_db = not args.no_db

    if args.pdf:
        if not os.path.isfile(args.pdf):
            print(f"ERROR: File not found: {args.pdf}")
            sys.exit(1)
        process_single_pdf(
            args.pdf, client, args.model, args.vision_model,
            args.quality_threshold, use_vision, args.chunk_size,
            args.output, persist_db, args.db_url,
        )
    else:
        input_dir = args.input_dir or str(DEFAULT_UPLOADS_DIR)
        if not os.path.isdir(input_dir):
            print(f"ERROR: Directory not found: {input_dir}")
            sys.exit(1)
        run_batch(
            input_dir, client, args.model, args.vision_model,
            args.quality_threshold, use_vision, args.chunk_size,
            args.output, args.parallel, persist_db, args.max_files, args.db_url,
        )


if __name__ == "__main__":
    main()
