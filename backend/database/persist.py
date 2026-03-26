"""Persist pipeline results to the database.

Stores all processed chart data into SQLAlchemy ORM tables using
synchronous sessions. Populates both the assertion-centric tables
AND the normalized tables (patients, diagnoses, encounters, clinical
sentences, HEDIS evidence, extraction results).

Supports both PostgreSQL (from config) and SQLite (zero-config fallback).

Usage from scripts:
    from database.persist import persist_chart_results, init_db
    engine = init_db("sqlite:///outputs/medinsight360.db")
    persist_chart_results(engine, chart_name, ...)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import (
    Assertion,
    Base,
    Chart,
    ChartPage,
    ClinicalSentence,
    ConditionGroup,
    DecisionTraceEvent,
    Diagnosis,
    DiagnosisCandidate,
    DiagnosisCandidateEvidence,
    DiagnosisHCCMapping,
    Encounter,
    EncounterDiagnosis,
    EncounterLabOrder,
    EncounterMedication,
    EncounterProcedure,
    EncounterReferral,
    ExtractionResult,
    HEDISBPReading,
    HEDISDepressionScreening,
    HEDISEligibility,
    HEDISFallsRisk,
    HEDISLabResult,
    HEDISMedication,
    HEDISResult,
    HEDISScreening,
    HEDISSummary,
    Patient,
    PatientFamilyHistory,
    PatientMemberID,
    PatientPhone,
    PatientProvider,
    PatientVital,
    PayableHCC,
    PipelineLog,
    PipelineRun,
    ProcessingStats,
    RAFSummary,
    SuppressedHCC,
)

log = logging.getLogger(__name__)

DEFAULT_SQLITE_PATH = os.getenv("MEDINSIGHT_SQLITE_PATH", "outputs/medinsight360.db")


def init_db(db_url: Optional[str] = None) -> Engine:
    """Initialize DB engine and create all tables."""
    if db_url == "postgres":
        from database.connection import sync_engine
        engine = sync_engine
    elif db_url:
        engine = create_engine(db_url, echo=False)
    else:
        Path(DEFAULT_SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{DEFAULT_SQLITE_PATH}", echo=False)

    Base.metadata.create_all(bind=engine)
    return engine


def _make_session(engine: Engine) -> Session:
    return sessionmaker(bind=engine)()


def _clear_chart_data(session: Session, chart_id: int) -> None:
    """Delete all existing data for a chart (for re-processing)."""
    for model in [
        Assertion, ConditionGroup, PayableHCC, SuppressedHCC,
        RAFSummary, HEDISResult, HEDISSummary, ProcessingStats,
        PipelineLog, PipelineRun,
        DiagnosisCandidate, DiagnosisCandidateEvidence, DecisionTraceEvent,
        # Normalized tables
        ClinicalSentence, Diagnosis, Encounter,
        HEDISBPReading, HEDISLabResult, HEDISScreening,
        HEDISDepressionScreening, HEDISFallsRisk, HEDISEligibility,
        HEDISMedication, Patient, ChartPage,
    ]:
        try:
            session.execute(delete(model).where(model.chart_id == chart_id))
        except Exception:
            pass


def _safe_json(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, (list, dict)):
        return json.loads(json.dumps(val, default=str))
    return str(val)


def _safe_date(val: Any) -> Optional[date]:
    if val is None or val == "":
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        text = val.strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            return None
    return None


def _safe_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        text = val.strip()
        if text.isdigit():
            return int(text)
    return None


def _fit_text(val: Any, max_len: int) -> Optional[str]:
    if val is None:
        return None
    text = str(val)
    if max_len <= 0:
        return text
    return text[:max_len]


# -----------------------------------------------------------------------
# Assertion persistence (existing)
# -----------------------------------------------------------------------

def _persist_assertions(
    session: Session, chart_id: int, run_id: int, assertions: List[Dict[str, Any]],
) -> int:
    objects = []
    for a in assertions:
        obj = Assertion(
            chart_id=chart_id, run_id=run_id,
            assertion_id=a.get("assertion_id"),
            category=a.get("category", "unknown"),
            concept=a.get("concept"),
            canonical_concept=a.get("canonical_concept"),
            text=a.get("text"),
            clean_text=a.get("clean_text"),
            status=a.get("status", "active"),
            subject=a.get("subject", "patient"),
            evidence_rank=a.get("evidence_rank", 3),
            page_number=a.get("page_number"),
            exact_quote=(a.get("exact_quote") or "")[:4000] if a.get("exact_quote") else None,
            char_start=a.get("char_start"),
            char_end=a.get("char_end"),
            quote_repaired=a.get("quote_repaired", False),
            quote_similarity=a.get("quote_similarity"),
            quote_match_method=a.get("quote_match_method"),
            icd_codes=_safe_json(a.get("icd_codes")),
            icd_codes_primary=_safe_json(a.get("icd_codes_primary")),
            icd9_codes=_safe_json(a.get("icd9_codes")),
            cpt2_codes=_safe_json(a.get("cpt2_codes")),
            hcpcs_codes=_safe_json(a.get("hcpcs_codes")),
            codes=_safe_json(a.get("codes")),
            effective_date=a.get("effective_date"),
            effective_date_source=a.get("effective_date_source"),
            inferred_date=a.get("inferred_date"),
            inferred_date_confidence=a.get("inferred_date_confidence"),
            inferred_date_source=a.get("inferred_date_source"),
            page_best_dos=a.get("page_best_dos"),
            doc_best_guess_dos=a.get("doc_best_guess_dos"),
            negation_trigger=a.get("negation_trigger"),
            allergy_none=a.get("allergy_none", False),
            structured=_safe_json(a.get("structured")),
            structured_page_vitals=_safe_json(a.get("structured_page_vitals")),
            medication_normalized=_safe_json(a.get("medication_normalized")),
            condition_group_id_v3=a.get("condition_group_id_v3"),
            condition_group_key_v3=a.get("condition_group_key_v3"),
            is_condition_best_evidence_v3=a.get("is_condition_best_evidence_v3", False),
            is_hcc_candidate=a.get("is_hcc_candidate", False),
            is_payable_hcc_candidate=a.get("is_payable_hcc_candidate", False),
            is_payable_ra_candidate=a.get("is_payable_ra_candidate", False),
            payable_hcc_exclusion_reason=a.get("payable_hcc_exclusion_reason"),
            is_hedis_evidence=a.get("is_hedis_evidence", False),
            is_hedis_evidence_effective=a.get("is_hedis_evidence_effective", False),
            review_status="pending",
            contradicted=a.get("contradicted", False),
        )
        objects.append(obj)
    session.add_all(objects)
    session.flush()
    return len(objects)


# -----------------------------------------------------------------------
# HCC / RAF persistence (existing)
# -----------------------------------------------------------------------

def _persist_hcc_pack(
    session: Session, chart_id: int, run_id: int,
    hcc_pack: Dict[str, Any], measurement_year: int,
) -> Dict[str, int]:
    counts = {"payable_hccs": 0, "suppressed_hccs": 0}

    for h in hcc_pack.get("payable_hccs", []):
        session.add(PayableHCC(
            chart_id=chart_id, run_id=run_id,
            hcc_code=h.get("hcc_code", ""),
            hcc_description=h.get("hcc_description", ""),
            raf_weight=h.get("raf_weight", 0),
            confidence=h.get("confidence"),
            source=h.get("source"),
            llm_verified=h.get("llm_verified"),
            llm_confidence=h.get("llm_confidence"),
            hierarchy_applied=h.get("hierarchy_applied", False),
            supported_icds=_safe_json(h.get("supported_icds", [])),
            icd_count=h.get("icd_count", len(h.get("supported_icds", []))),
            measurement_year=measurement_year,
        ))
        counts["payable_hccs"] += 1

    for s in hcc_pack.get("suppressed_hccs", []):
        session.add(SuppressedHCC(
            chart_id=chart_id, run_id=run_id,
            hcc_code=s.get("hcc_code", ""),
            hcc_description=s.get("hcc_description", ""),
            suppressed_by=s.get("suppressed_by", ""),
            hierarchy_group=s.get("group", ""),
            supported_icds=_safe_json(s.get("supported_icds", [])),
        ))
        counts["suppressed_hccs"] += 1

    raf = hcc_pack.get("raf_summary", {})
    ensemble_meta = hcc_pack.get("ensemble_metadata", {})
    session.add(RAFSummary(
        chart_id=chart_id, run_id=run_id,
        total_raf_score=raf.get("total_raf_score", 0),
        demographic_raf=raf.get("demographic_raf", 0),
        hcc_raf=raf.get("hcc_raf", 0),
        hcc_count=raf.get("hcc_count", 0),
        payable_hcc_count=raf.get("payable_hcc_count", 0),
        suppressed_hcc_count=raf.get("suppressed_hcc_count", 0),
        unmapped_icd_count=raf.get("unmapped_icd_count", 0),
        total_payable_icds=hcc_pack.get("payable_icd_count", 0),
        ensemble_version=ensemble_meta.get("ensemble_version"),
        ensemble_metadata=_safe_json(ensemble_meta) if ensemble_meta else None,
        measurement_year=measurement_year,
    ))

    session.flush()
    return counts


# -----------------------------------------------------------------------
# HEDIS result persistence (existing)
# -----------------------------------------------------------------------

def _persist_hedis(
    session: Session, chart_id: int, run_id: int,
    hedis_result: Dict[str, Any], measurement_year: int,
) -> Dict[str, int]:
    counts = {"hedis_results": 0}

    for m in hedis_result.get("measures", []):
        # Handle both engine format (id/name) and legacy format (measure_id/measure_name)
        measure_id = m.get("measure_id") or m.get("id", "")
        measure_name = m.get("measure_name") or m.get("name", "")
        compliant_val = m.get("compliant")
        if compliant_val is None:
            compliant_val = False
        trace_payload = m.get("trace", [])
        if not isinstance(trace_payload, list):
            trace_payload = []
        evidence_payload = m.get("evidence_used", [])
        if not isinstance(evidence_payload, list):
            evidence_payload = []
        gap_payload = m.get("gaps", [])
        if not isinstance(gap_payload, list):
            gap_payload = []

        # Preserve richer measure context inside trace JSON for backward-compatible storage.
        rich_payload = {
            "measure_definition": m.get("measure_definition"),
            "decision_reasoning": m.get("decision_reasoning"),
            "eligibility_reason": m.get("eligibility_reason", []),
            "compliance_reason": m.get("compliance_reason", []),
            "exclusion_reason": m.get("exclusion_reason"),
            "missing_data": m.get("missing_data", []),
            "confidence": m.get("confidence"),
            "clinical_only_preview": m.get("clinical_only_preview"),
            "enrollment_dependency": m.get("enrollment_dependency"),
            "denominator_signal": m.get("denominator_signal"),
            "coding_opportunity": m.get("coding_opportunity"),
            "llm_adjudication": m.get("llm_adjudication"),
        }
        trace_payload.append(
            {
                "rule": "__measure_payload__",
                "result": True,
                "detail": "Persisted enriched measure payload for API/UI rendering.",
                "meta": _safe_json(rich_payload),
            }
        )
        session.add(HEDISResult(
            chart_id=chart_id, run_id=run_id,
            measure_id=measure_id,
            measure_name=measure_name,
            status=m.get("status", ""),
            applicable=m.get("applicable", False),
            compliant=bool(compliant_val),
            evidence_used=_safe_json(evidence_payload),
            gaps=_safe_json(gap_payload),
            trace=_safe_json(trace_payload),
            measurement_year=measurement_year,
        ))
        counts["hedis_results"] += 1

    hs = hedis_result.get("summary", {})
    session.add(HEDISSummary(
        chart_id=chart_id, run_id=run_id,
        total_measures=hs.get("total_measures", 0),
        applicable_count=hs.get("applicable", 0),
        met_count=hs.get("met", 0),
        gap_count=hs.get("gap", 0),
        excluded_count=hs.get("excluded", 0),
        indeterminate_count=hs.get("indeterminate", 0),
        not_applicable_count=hs.get("not_applicable", 0),
        measurement_year=measurement_year,
        engine_version=hedis_result.get("engine", "simple"),
    ))

    session.flush()
    return counts


def _candidate_key(item: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(item.get("icd10_code") or ""),
            str(item.get("assertion_id") or ""),
            str(item.get("page_number") or ""),
            str(item.get("condition_group_id_v3") or ""),
            str(item.get("candidate_state") or ""),
        ]
    )


def _persist_codex_lineage(
    session: Session,
    chart_id: int,
    run_id: int,
    patient_id: Optional[int],
    hcc_pack: Dict[str, Any],
    hedis_result: Dict[str, Any],
) -> Dict[str, int]:
    counts = {"diagnosis_candidates": 0, "candidate_evidence": 0, "decision_trace_events": 0}

    for item in hcc_pack.get("decision_trace", []):
        key = _candidate_key(item)
        cand = DiagnosisCandidate(
            chart_id=chart_id,
            patient_id=patient_id,
            run_id=run_id,
            assertion_id=_safe_int(item.get("assertion_id")),
            candidate_key=key,
            icd10_code=item.get("icd10_code"),
            hcc_code=item.get("hcc_code"),
            source_type=item.get("source_type", "assertion"),
            lifecycle_state=item.get("candidate_state", "unknown"),
            reason_code=item.get("reason_code"),
            reason_text=item.get("reason"),
            confidence=item.get("confidence"),
            effective_date=_safe_date(item.get("effective_date")),
            provider_name=item.get("provider"),
            page_number=item.get("page_number"),
            exact_quote=(item.get("exact_quote") or "")[:4000] if item.get("exact_quote") else None,
            payload=_safe_json(item),
            review_status="pending",
        )
        session.add(cand)
        session.flush()
        counts["diagnosis_candidates"] += 1

        if item.get("exact_quote") or item.get("page_number") is not None:
            session.add(DiagnosisCandidateEvidence(
                candidate_id=cand.id,
                chart_id=chart_id,
                page_number=item.get("page_number"),
                char_start=item.get("char_start"),
                char_end=item.get("char_end"),
                exact_quote=(item.get("exact_quote") or "")[:4000] if item.get("exact_quote") else None,
                section_name=item.get("category"),
                is_primary=True,
                confidence=item.get("confidence"),
            ))
            counts["candidate_evidence"] += 1

        session.add(DecisionTraceEvent(
            chart_id=chart_id,
            patient_id=patient_id,
            run_id=run_id,
            entity_type="diagnosis_candidate",
            entity_key=key,
            lifecycle_state=item.get("candidate_state", "unknown"),
            reason_code=item.get("reason_code"),
            reason_text=item.get("reason"),
            icd10_code=item.get("icd10_code"),
            hcc_code=item.get("hcc_code"),
            event_date=_safe_date(item.get("effective_date")),
            payload=_safe_json(item),
        ))
        counts["decision_trace_events"] += 1

    for measure in hedis_result.get("measures", []):
        measure_id = measure.get("measure_id") or measure.get("id") or ""
        summary_reason = "; ".join(measure.get("eligibility_reason", []) + measure.get("compliance_reason", []))
        session.add(DecisionTraceEvent(
            chart_id=chart_id,
            patient_id=patient_id,
            run_id=run_id,
            entity_type="hedis_measure",
            entity_key=measure_id,
            lifecycle_state=measure.get("status", "unknown"),
            reason_code="measure_evaluation",
            reason_text=summary_reason[:4000] if summary_reason else None,
            measure_id=measure_id,
            payload=_safe_json({
                "status": measure.get("status"),
                "applicable": measure.get("applicable"),
                "missing_data": measure.get("missing_data", []),
                "trace": measure.get("trace", []),
                "gaps": measure.get("gaps", []),
            }),
        ))
        counts["decision_trace_events"] += 1

    session.flush()
    return counts


# -----------------------------------------------------------------------
# Patient matching + demographics persistence (multi-chart aware)
# -----------------------------------------------------------------------

def _normalize_name(name: Optional[str]) -> str:
    """Normalize a patient name for comparison.

    Strips whitespace, lowercases, removes common prefixes/suffixes,
    collapses multiple spaces, and sorts name parts for order-independent matching.
    """
    if not name:
        return ""
    import re
    n = name.lower().strip()
    # Remove titles and suffixes
    for prefix in ["mr.", "mrs.", "ms.", "dr.", "mr ", "mrs ", "ms ", "dr "]:
        if n.startswith(prefix):
            n = n[len(prefix):]
    for suffix in [" jr", " sr", " jr.", " sr.", " ii", " iii", " iv"]:
        if n.endswith(suffix):
            n = n[:-len(suffix)]
    # Remove non-alpha characters except spaces
    n = re.sub(r"[^a-z\s]", "", n)
    # Collapse whitespace and sort parts (handles "Last, First" vs "First Last")
    parts = sorted(n.split())
    return " ".join(parts)


def _normalize_dob(dob: Optional[str]) -> str:
    """Normalize DOB string for comparison."""
    if not dob:
        return ""
    import re
    # Strip to digits only, then try to reconstruct YYYY-MM-DD
    digits = re.sub(r"[^0-9]", "", dob)
    if len(digits) == 8:
        # Could be YYYYMMDD or MMDDYYYY
        if digits[:2] in ("19", "20"):
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        else:
            return f"{digits[4:8]}-{digits[:2]}-{digits[2:4]}"
    # Return cleaned original
    return dob.strip()


def _find_matching_patient(
    session: Session, name: str, dob: str, member_ids: List[str],
) -> Optional[Patient]:
    """Find an existing patient by member_id or (name + DOB).

    Priority: 1) exact member_id match, 2) normalized name + DOB match.
    """
    from sqlalchemy import select

    # 1. Try member ID match (most reliable)
    for mid in member_ids:
        if mid:
            existing_mid = session.execute(
                select(PatientMemberID).where(PatientMemberID.member_id == mid)
            ).scalar_one_or_none()
            if existing_mid:
                patient = session.get(Patient, existing_mid.patient_id)
                if patient:
                    log.info("Patient matched by member_id=%s -> patient_id=%d", mid, patient.id)
                    return patient

    # 2. Try name + DOB match
    norm_name = _normalize_name(name)
    norm_dob = _normalize_dob(dob)
    if not norm_name or not norm_dob:
        return None

    # Query all patients with matching DOB (small result set)
    candidates = session.execute(
        select(Patient).where(Patient.date_of_birth.isnot(None))
    ).scalars().all()

    for candidate in candidates:
        if _normalize_dob(candidate.date_of_birth) == norm_dob:
            if _normalize_name(candidate.patient_name) == norm_name:
                log.info(
                    "Patient matched by name+DOB: '%s' + '%s' -> patient_id=%d",
                    name, dob, candidate.id,
                )
                return candidate

    return None


def _update_patient_demographics(patient: Patient, demo: Dict[str, Any]) -> None:
    """Merge new demographics into existing patient — fill blanks, don't overwrite existing."""
    address = demo.get("address", {}) if isinstance(demo.get("address"), dict) else {}
    social = demo.get("social_history", {}) if isinstance(demo.get("social_history"), dict) else {}
    mental = demo.get("mental_health", {}) if isinstance(demo.get("mental_health"), dict) else {}

    # Only fill in fields that are currently empty
    field_map = {
        "gender": demo.get("gender"),
        "age": _try_int(demo.get("age")),
        "language": demo.get("language"),
        "race_ethnicity": demo.get("race_ethnicity"),
        "insurance": demo.get("insurance"),
        "allergies": _safe_json(demo.get("allergies")),
        "advance_directives": demo.get("advance_directives"),
        "address_street": address.get("street"),
        "address_city": address.get("city"),
        "address_state": address.get("state"),
        "address_zip": address.get("zip"),
        "social_smoking": social.get("smoking_status") or social.get("smoking") or demo.get("smoking"),
        "social_alcohol": social.get("alcohol_use") or social.get("alcohol") or demo.get("alcohol"),
        "social_drugs": social.get("drug_use") or social.get("drugs") or demo.get("drug_use"),
        "social_marital": social.get("marital_status") or demo.get("marital_status"),
        "social_employment": social.get("employment") or demo.get("employment"),
        "social_living": social.get("living_situation") or demo.get("living_situation"),
        "mental_phq9": mental.get("phq9_score") or mental.get("phq9") or demo.get("phq9"),
        "mental_phq2": mental.get("phq2_score") or mental.get("phq2") or demo.get("phq2"),
        "mental_mmse": mental.get("mmse_result") or mental.get("mmse") or demo.get("mmse"),
        "mental_depression": mental.get("depression_status") or mental.get("depression") or demo.get("depression"),
        "mental_anxiety": mental.get("anxiety_status") or mental.get("anxiety") or demo.get("anxiety"),
    }
    for attr, new_val in field_map.items():
        if new_val and not getattr(patient, attr, None):
            setattr(patient, attr, new_val)

    # Always update alternate_names (accumulate)
    if demo.get("alternate_names"):
        existing = patient.alternate_names or []
        new_names = demo["alternate_names"] if isinstance(demo["alternate_names"], list) else [demo["alternate_names"]]
        merged = list(set(existing + new_names))
        patient.alternate_names = _safe_json(merged)

    # Increment chart count
    patient.chart_count = (patient.chart_count or 1) + 1


def _find_or_create_patient(
    session: Session, chart_id: int, run_id: int, demo: Dict[str, Any],
) -> Optional[int]:
    """Find an existing patient or create a new one. Returns patient_id.

    Matching logic:
      1. By member_id (exact match via patient_member_ids table)
      2. By normalized (patient_name + date_of_birth)
    If matched: update demographics with new data, add new vitals/providers.
    If not matched: create new patient record.
    """
    if not demo or "_error" in demo:
        return None

    name = demo.get("patient_name", "")
    dob = demo.get("date_of_birth", "")

    # Extract member IDs from demographics
    raw_member_ids: List[str] = []
    for mid in demo.get("member_ids", []):
        if isinstance(mid, dict):
            val = mid.get("member_id") or mid.get("id", "")
        else:
            val = str(mid) if mid else ""
        if val:
            raw_member_ids.append(val)

    # Try to find existing patient
    existing = _find_matching_patient(session, name, dob, raw_member_ids)

    if existing:
        patient = existing
        _update_patient_demographics(patient, demo)
        patient.chart_id = chart_id  # Update to latest chart
        patient.run_id = run_id
        session.flush()
        patient_id = patient.id
        matched = True
    else:
        # Create new patient
        address = demo.get("address", {}) if isinstance(demo.get("address"), dict) else {}
        social = demo.get("social_history", {}) if isinstance(demo.get("social_history"), dict) else {}
        mental = demo.get("mental_health", {}) if isinstance(demo.get("mental_health"), dict) else {}

        patient = Patient(
            chart_id=chart_id, run_id=run_id,
            patient_name=name or None,
            alternate_names=_safe_json(demo.get("alternate_names")),
            date_of_birth=dob or None,
            gender=demo.get("gender"),
            age=_try_int(demo.get("age")),
            language=demo.get("language"),
            race_ethnicity=demo.get("race_ethnicity"),
            insurance=demo.get("insurance"),
            allergies=_safe_json(demo.get("allergies")),
            advance_directives=demo.get("advance_directives"),
            address_street=address.get("street"),
            address_city=address.get("city"),
            address_state=address.get("state"),
            address_zip=address.get("zip"),
            address_full=demo.get("address") if isinstance(demo.get("address"), str) else None,
            social_smoking=social.get("smoking_status") or social.get("smoking") or demo.get("smoking"),
            social_alcohol=social.get("alcohol_use") or social.get("alcohol") or demo.get("alcohol"),
            social_drugs=social.get("drug_use") or social.get("drugs") or demo.get("drug_use"),
            social_marital=social.get("marital_status") or demo.get("marital_status"),
            social_employment=social.get("employment") or demo.get("employment"),
            social_living=social.get("living_situation") or demo.get("living_situation"),
            mental_phq9=mental.get("phq9_score") or mental.get("phq9") or demo.get("phq9"),
            mental_phq2=mental.get("phq2_score") or mental.get("phq2") or demo.get("phq2"),
            mental_mmse=mental.get("mmse_result") or mental.get("mmse") or demo.get("mmse"),
            mental_depression=mental.get("depression_status") or mental.get("depression") or demo.get("depression"),
            mental_anxiety=mental.get("anxiety_status") or mental.get("anxiety") or demo.get("anxiety"),
            chart_count=1,
        )
        session.add(patient)
        session.flush()
        patient_id = patient.id
        matched = False

    # Add vitals from this chart (always — vitals accumulate across charts)
    for v in demo.get("vitals", []):
        if isinstance(v, dict):
            session.add(PatientVital(
                patient_id=patient_id,
                chart_id=chart_id,
                measurement_date=v.get("date"),
                bp_systolic=str(v.get("bp_systolic", "")) if v.get("bp_systolic") else None,
                bp_diastolic=str(v.get("bp_diastolic", "")) if v.get("bp_diastolic") else None,
                weight=str(v.get("weight", "")) if v.get("weight") else None,
                height=str(v.get("height", "")) if v.get("height") else None,
                bmi=str(v.get("bmi", "")) if v.get("bmi") else None,
                pulse=str(v.get("pulse", "")) if v.get("pulse") else None,
                temperature=str(v.get("temperature", "")) if v.get("temperature") else None,
                oxygen_saturation=str(v.get("oxygen_saturation", "")) if v.get("oxygen_saturation") else None,
            ))

    # Providers (add new ones, skip duplicates by name)
    existing_provider_names = set()
    if matched:
        for p in patient.providers:
            if p.name:
                existing_provider_names.add(p.name.lower().strip())

    for p in demo.get("providers", []):
        pname = p.get("name") if isinstance(p, dict) else (p if isinstance(p, str) else None)
        if pname and pname.lower().strip() not in existing_provider_names:
            if isinstance(p, dict):
                session.add(PatientProvider(
                    patient_id=patient_id,
                    name=p.get("name"), specialty=p.get("specialty"),
                    facility=p.get("facility"), address=p.get("address"),
                    phone=p.get("phone"), role=p.get("role"),
                ))
            else:
                session.add(PatientProvider(patient_id=patient_id, name=pname))
            existing_provider_names.add(pname.lower().strip())

    # Family history (add new conditions)
    existing_fh = set()
    if matched:
        for fh in patient.family_history:
            if fh.condition:
                existing_fh.add(fh.condition.lower().strip())

    for fh in demo.get("family_history", []):
        cond = fh.get("condition") if isinstance(fh, dict) else (fh if isinstance(fh, str) else None)
        if cond and cond.lower().strip() not in existing_fh:
            if isinstance(fh, dict):
                session.add(PatientFamilyHistory(
                    patient_id=patient_id, condition=fh.get("condition"), relation=fh.get("relation"),
                ))
            else:
                session.add(PatientFamilyHistory(patient_id=patient_id, condition=fh))
            existing_fh.add(cond.lower().strip())

    # Member IDs (add new ones)
    existing_mids = set()
    if matched:
        for mid in patient.member_ids:
            if mid.member_id:
                existing_mids.add(mid.member_id)

    for mid_val in raw_member_ids:
        if mid_val not in existing_mids:
            session.add(PatientMemberID(patient_id=patient_id, member_id=mid_val))
            existing_mids.add(mid_val)

    # Phones (add new numbers)
    existing_phones = set()
    if matched:
        for ph in patient.phones:
            if ph.number:
                existing_phones.add(ph.number.strip())

    for ph in demo.get("phones", demo.get("phone_numbers", [])):
        num = ph.get("number") if isinstance(ph, dict) else (ph if isinstance(ph, str) else None)
        if num and num.strip() not in existing_phones:
            if isinstance(ph, dict):
                session.add(PatientPhone(patient_id=patient_id, number=ph.get("number"), phone_type=ph.get("type")))
            else:
                session.add(PatientPhone(patient_id=patient_id, number=num))
            existing_phones.add(num.strip())

    session.flush()
    log.info(
        "Patient %s: patient_id=%d, name='%s', charts=%d",
        "MATCHED" if matched else "CREATED",
        patient_id, name, patient.chart_count or 1,
    )
    return patient_id


# -----------------------------------------------------------------------
# NEW: Diagnoses persistence (from risk pipeline)
# -----------------------------------------------------------------------

def _persist_diagnoses(
    session: Session, chart_id: int, run_id: int,
    risk_data: Dict[str, Any], hcc_pack: Dict[str, Any],
) -> int:
    diagnoses = risk_data.get("diagnoses", [])
    if not diagnoses:
        return 0

    # Build a lookup: icd10_code -> list of HCC mappings from the pack
    icd_hcc_map: Dict[str, List[Dict]] = {}
    for hcc in hcc_pack.get("payable_hccs", []) + hcc_pack.get("suppressed_hccs", []):
        for icd_info in hcc.get("supported_icds", []):
            code = (icd_info.get("icd10_code") or "").upper()
            if code:
                icd_hcc_map.setdefault(code, []).append(hcc)

    count = 0
    for dx in diagnoses:
        icd10 = (dx.get("icd10_code") or "").strip()
        obj = Diagnosis(
            chart_id=chart_id, run_id=run_id,
            icd10_code=icd10,
            icd9_code=dx.get("icd9_code"),
            snomed_code=dx.get("snomed_code"),
            description=dx.get("description"),
            negation_status=(dx.get("negation_status") or "active").lower(),
            negation_trigger=dx.get("negation_trigger"),
            supporting_text=dx.get("supporting_text"),
            source_section=dx.get("source_section"),
            date_of_service=dx.get("date_of_service"),
            provider=dx.get("provider"),
        )
        session.add(obj)
        session.flush()
        count += 1

        # Link HCC mappings to this diagnosis
        for hcc in icd_hcc_map.get(icd10.upper(), []):
            is_suppressed = "suppressed_by" in hcc
            session.add(DiagnosisHCCMapping(
                diagnosis_id=obj.id,
                chart_id=chart_id,
                run_id=run_id,
                hcc_category=_try_int(hcc.get("hcc_code", "").replace("HCC ", "")),
                hcc_description=hcc.get("hcc_description"),
                raf_weight=hcc.get("raf_weight", 0),
                counts_for_raf=not is_suppressed,
                exclusion_reason=f"suppressed by {hcc['suppressed_by']}" if is_suppressed else None,
            ))

    session.flush()
    return count


# -----------------------------------------------------------------------
# NEW: Encounters persistence
# -----------------------------------------------------------------------

def _persist_encounters(
    session: Session, chart_id: int, run_id: int, enc_data: Dict[str, Any],
) -> int:
    encounters = enc_data.get("encounters", [])
    if not encounters:
        return 0

    count = 0
    for enc in encounters:
        telehealth = enc.get("telehealth", {}) if isinstance(enc.get("telehealth"), dict) else {}
        obj = Encounter(
            chart_id=chart_id, run_id=run_id,
            encounter_date=enc.get("date") or enc.get("encounter_date"),
            encounter_ext_id=enc.get("encounter_id"),
            provider=enc.get("provider"),
            facility=enc.get("facility"),
            encounter_type=enc.get("type") or enc.get("encounter_type"),
            chief_complaint=enc.get("chief_complaint"),
            telehealth_platform=telehealth.get("platform"),
            telehealth_type=telehealth.get("type"),
            telehealth_prearranged=telehealth.get("prearranged"),
            counseling_topics=_safe_json(enc.get("counseling_topics")),
            time_spent=enc.get("time_spent"),
            signed_by=enc.get("signed_by"),
        )
        session.add(obj)
        session.flush()
        enc_id = obj.id
        count += 1

        for med in enc.get("medications", []):
            if isinstance(med, dict):
                session.add(EncounterMedication(
                    encounter_id=enc_id,
                    name=med.get("name") or med.get("medication"),
                    dose_form=med.get("dose_form") or med.get("dose"),
                    instructions=med.get("instructions"),
                    indication=med.get("indication"),
                    action=med.get("action"),
                ))

        for lab in enc.get("lab_orders", enc.get("labs", [])):
            if isinstance(lab, dict):
                session.add(EncounterLabOrder(
                    encounter_id=enc_id,
                    test_name=lab.get("test_name") or lab.get("test") or lab.get("name"),
                    status=lab.get("status"),
                    result=lab.get("result"),
                    date_ordered=lab.get("date_ordered"),
                    date_resulted=lab.get("date_resulted"),
                ))

        for proc in enc.get("procedures", []):
            if isinstance(proc, dict):
                session.add(EncounterProcedure(
                    encounter_id=enc_id,
                    name=proc.get("name") or proc.get("procedure"),
                    cpt_code=proc.get("cpt_code"),
                    status=proc.get("status"),
                    result=proc.get("result"),
                ))

        for ref in enc.get("referrals", []):
            if isinstance(ref, dict):
                session.add(EncounterReferral(
                    encounter_id=enc_id,
                    to_provider=ref.get("to_provider") or ref.get("to"),
                    reason=ref.get("reason"),
                    status=ref.get("status"),
                    urgency=ref.get("urgency"),
                ))

        for edx in enc.get("diagnoses_this_visit", enc.get("diagnoses", [])):
            if isinstance(edx, dict):
                session.add(EncounterDiagnosis(
                    encounter_id=enc_id,
                    icd10_code=edx.get("icd10_code") or edx.get("code"),
                    description=edx.get("description"),
                ))

    session.flush()
    return count


# -----------------------------------------------------------------------
# NEW: Clinical sentences persistence
# -----------------------------------------------------------------------

def _persist_clinical_sentences(
    session: Session, chart_id: int, run_id: int, sent_data: Dict[str, Any],
) -> int:
    sentences = sent_data.get("sentences", [])
    if not sentences:
        return 0

    count = 0
    for s in sentences:
        session.add(ClinicalSentence(
            chart_id=chart_id, run_id=run_id,
            sentence_text=s.get("text", ""),
            category=s.get("category"),
            is_negated=s.get("is_negated", False),
            negation_trigger=s.get("negation_trigger"),
            negated_item=s.get("negated_item"),
        ))
        count += 1

    session.flush()
    return count


# -----------------------------------------------------------------------
# NEW: HEDIS evidence persistence (normalized tables)
# -----------------------------------------------------------------------

def _persist_hedis_evidence(
    session: Session, chart_id: int, run_id: int, hedis_data: Dict[str, Any],
) -> Dict[str, int]:
    counts: Dict[str, int] = {}

    # BP readings
    bp_count = 0
    for bp in hedis_data.get("blood_pressure_readings", []):
        if isinstance(bp, dict):
            session.add(HEDISBPReading(
                chart_id=chart_id, run_id=run_id,
                reading_date=_fit_text(bp.get("date"), 20),
                systolic=_try_int(bp.get("systolic")),
                diastolic=_try_int(bp.get("diastolic")),
                location=_fit_text(bp.get("location"), 30),
                within_target=bp.get("within_target"),
                target_note=_fit_text(bp.get("target_note"), 100),
            ))
            bp_count += 1
    counts["hedis_bp_readings"] = bp_count

    # Lab results
    lab_count = 0
    for lab in hedis_data.get("lab_results", []):
        if isinstance(lab, dict):
            session.add(HEDISLabResult(
                chart_id=chart_id, run_id=run_id,
                test_name=_fit_text(lab.get("test_name"), 100),
                result_value=_fit_text(lab.get("result_value"), 50),
                result_date=_fit_text(lab.get("result_date"), 20),
                reference_range=_fit_text(lab.get("reference_range"), 50),
                hedis_measure=_fit_text(lab.get("hedis_measure"), 20),
                within_target=lab.get("within_target"),
            ))
            lab_count += 1
    counts["hedis_lab_results"] = lab_count

    # Screenings
    scr_count = 0
    for scr in hedis_data.get("screenings", []):
        if isinstance(scr, dict):
            screening_type = scr.get("screening_type") or scr.get("type")
            screening_date = scr.get("date") or scr.get("screening_date")
            session.add(HEDISScreening(
                chart_id=chart_id, run_id=run_id,
                screening_type=_fit_text(screening_type, 50),
                screening_date=_fit_text(screening_date, 20),
                result=scr.get("result"),
                hedis_measure=_fit_text(scr.get("hedis_measure"), 20),
                status=_fit_text(scr.get("status"), 30),
            ))
            scr_count += 1
    counts["hedis_screenings"] = scr_count

    # Depression screening
    dep = hedis_data.get("depression_screening", {})
    if dep and isinstance(dep, dict) and any(dep.get(k) is not None for k in ["phq2_score", "phq9_score"]):
        session.add(HEDISDepressionScreening(
            chart_id=chart_id, run_id=run_id,
            phq2_score=_fit_text(dep.get("phq2_score"), 20),
            phq2_date=_fit_text(dep.get("phq2_date"), 20),
            phq9_score=_fit_text(dep.get("phq9_score"), 20),
            phq9_date=_fit_text(dep.get("phq9_date"), 20),
            positive_screen=dep.get("positive_screen", False),
            follow_up_plan=dep.get("follow_up_plan"),
        ))
        counts["hedis_depression_screenings"] = 1

    # Falls risk
    falls = hedis_data.get("falls_risk", {})
    if falls and isinstance(falls, dict) and falls.get("assessed") is not None:
        session.add(HEDISFallsRisk(
            chart_id=chart_id, run_id=run_id,
            assessed=falls.get("assessed", False),
            risk_level=_fit_text(falls.get("risk_level"), 20),
            interventions=_safe_json(falls.get("interventions")),
            assessment_date=_fit_text(falls.get("assessment_date"), 20),
        ))
        counts["hedis_falls_risk"] = 1

    # Eligibility conditions
    elig_count = 0
    for ec in hedis_data.get("eligibility_conditions", []):
        if isinstance(ec, dict):
            session.add(HEDISEligibility(
                chart_id=chart_id, run_id=run_id,
                condition=_fit_text(ec.get("condition"), 100),
                is_present=ec.get("is_present", False),
                evidence=ec.get("evidence"),
            ))
            elig_count += 1
    counts["hedis_eligibility"] = elig_count

    # HEDIS-relevant medications
    med_count = 0
    for med in hedis_data.get("medications_for_measures", hedis_data.get("medications", [])):
        if isinstance(med, dict):
            session.add(HEDISMedication(
                chart_id=chart_id, run_id=run_id,
                medication=_fit_text(med.get("medication") or med.get("name"), 255),
                indication=_fit_text(med.get("indication"), 255),
                hedis_relevance=_fit_text(med.get("hedis_relevance"), 100),
            ))
            med_count += 1
    counts["hedis_medications"] = med_count

    session.flush()
    return counts


# -----------------------------------------------------------------------
# NEW: Raw extraction results (for debugging/reprocessing)
# -----------------------------------------------------------------------

def _persist_extraction_results(
    session: Session, run_id: int, extraction_results: Dict[str, Dict],
) -> int:
    count = 0
    for pipeline_name, data in extraction_results.items():
        session.add(ExtractionResult(
            run_id=run_id,
            pipeline_name=pipeline_name,
            raw_json=_safe_json(data),
            chunk_count=data.get("_chunk_count") if isinstance(data, dict) else None,
        ))
        count += 1
    session.flush()
    return count


# -----------------------------------------------------------------------
# NEW: Chart pages persistence
# -----------------------------------------------------------------------

def _persist_chart_pages(
    session: Session, chart_id: int, run_id: int, pages_meta: List[Dict],
) -> int:
    if not pages_meta:
        return 0
    count = 0
    for pg in pages_meta:
        if isinstance(pg, dict):
            session.add(ChartPage(
                chart_id=chart_id, run_id=run_id,
                page_number=pg.get("page_number", pg.get("page", count + 1)),
                text_content=pg.get("text", pg.get("text_content")),
                text_length=pg.get("text_length") or len(pg.get("text", "")),
                quality_score=pg.get("quality_score") or pg.get("score"),
                extraction_method=pg.get("method", "text"),
                page_best_dos=pg.get("page_best_dos"),
            ))
            count += 1
    session.flush()
    return count


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _try_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# -----------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------

def persist_chart_results(
    engine: Engine,
    chart_name: str,
    source_file: str,
    assertions: List[Dict[str, Any]],
    hcc_pack: Dict[str, Any],
    hedis_result: Dict[str, Any],
    measurement_year: int = 2026,
    page_count: int = 0,
    elapsed_seconds: float = 0.0,
    extraction_results: Optional[Dict[str, Dict]] = None,
    pages_meta: Optional[List[Dict]] = None,
    model_used: str = "gpt-4o-mini",
    existing_chart_id: Optional[int] = None,
    upload_source: str = "batch",
) -> Dict[str, Any]:
    """Persist all pipeline results for a single chart.

    Populates both assertion-centric tables AND normalized tables.
    """
    session = _make_session(engine)
    result: Dict[str, Any] = {"chart_id": None, "run_id": None, "tables": {}}

    try:
        # 1. Chart record (new or update existing upload-backed chart)
        if existing_chart_id is not None:
            chart = session.get(Chart, existing_chart_id)
            if not chart:
                raise ValueError(f"Chart not found for persistence: {existing_chart_id}")
            _clear_chart_data(session, existing_chart_id)
            chart.filename = chart_name
            chart.file_path = source_file
            chart.page_count = page_count
            chart.pages_with_text = page_count
            chart.total_chars = sum(len(a.get("text") or "") for a in assertions)
            chart.status = "completed"
            chart.quality_score_avg = 100.0
            chart.upload_source = chart.upload_source or upload_source
            session.flush()
            chart_id = chart.id
        else:
            chart = Chart(
                filename=chart_name,
                file_path=source_file,
                page_count=page_count,
                pages_with_text=page_count,
                total_chars=sum(len(a.get("text") or "") for a in assertions),
                upload_source=upload_source,
                status="completed",
                quality_score_avg=100.0,
            )
            session.add(chart)
            session.flush()
            chart_id = chart.id
        result["chart_id"] = chart_id

        # 2. Pipeline run
        run = PipelineRun(
            chart_id=chart_id,
            run_number=1,
            status="completed",
            mode="full",
            model=model_used,
            chunk_count=1,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_seconds=elapsed_seconds,
            assertions_raw=len(assertions),
            assertions_audited=len(assertions),
        )
        session.add(run)
        session.flush()
        run_id = run.id
        result["run_id"] = run_id

        # 3. Assertions (legacy central table)
        result["tables"]["assertions"] = _persist_assertions(session, chart_id, run_id, assertions)

        # 4. HCC pack
        hcc_counts = _persist_hcc_pack(session, chart_id, run_id, hcc_pack, measurement_year)
        result["tables"].update(hcc_counts)
        result["tables"]["raf_summaries"] = 1

        # 5. HEDIS evaluation results
        hedis_counts = _persist_hedis(session, chart_id, run_id, hedis_result, measurement_year)
        result["tables"].update(hedis_counts)
        result["tables"]["hedis_summaries"] = 1

        # 6. Processing stats
        session.add(ProcessingStats(
            chart_id=chart_id, run_id=run_id,
            total_processing_seconds=elapsed_seconds,
            pages_processed=page_count,
            assertions_raw=len(assertions),
            assertions_audited=len(assertions),
            model_used=model_used,
        ))
        result["tables"]["processing_stats"] = 1

        # --- NORMALIZED TABLES (from raw extraction results) ---
        if extraction_results:
            # 7. Patient demographics (with matching)
            demo = extraction_results.get("demographics", {})
            patient_id = _find_or_create_patient(session, chart_id, run_id, demo)
            if patient_id:
                # Link chart -> patient
                chart.patient_id = patient_id
                session.flush()
                result["patient_id"] = patient_id
            result["tables"]["patients"] = 1 if patient_id else 0

            # 8. Diagnoses + HCC mappings
            risk = extraction_results.get("risk", {})
            result["tables"]["diagnoses"] = _persist_diagnoses(
                session, chart_id, run_id, risk, hcc_pack,
            )

            # 9. Encounters + child tables
            enc = extraction_results.get("encounters", {})
            result["tables"]["encounters"] = _persist_encounters(session, chart_id, run_id, enc)

            # 10. Clinical sentences
            sent = extraction_results.get("sentences", {})
            result["tables"]["clinical_sentences"] = _persist_clinical_sentences(
                session, chart_id, run_id, sent,
            )

            # 11. HEDIS evidence tables
            hedis_raw = extraction_results.get("hedis", {})
            hedis_ev_counts = _persist_hedis_evidence(session, chart_id, run_id, hedis_raw)
            result["tables"].update(hedis_ev_counts)

            # 12. Raw extraction results
            result["tables"]["extraction_results"] = _persist_extraction_results(
                session, run_id, extraction_results,
            )

        # 12b. Codex audit lineage tables
        codex_counts = _persist_codex_lineage(
            session,
            chart_id=chart_id,
            run_id=run_id,
            patient_id=result.get("patient_id"),
            hcc_pack=hcc_pack,
            hedis_result=hedis_result,
        )
        result["tables"].update(codex_counts)

        # 13. Chart pages
        if pages_meta:
            result["tables"]["chart_pages"] = _persist_chart_pages(
                session, chart_id, run_id, pages_meta,
            )

        session.commit()
        log.info("Persisted chart %s (id=%d): %s", chart_name, chart_id, result["tables"])
        return result

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_stats(engine: Engine) -> Dict[str, int]:
    """Get row counts for all main tables."""
    from sqlalchemy import func, select

    session = _make_session(engine)
    try:
        stats = {}
        for model in [
            Chart, PipelineRun, Assertion, PayableHCC, SuppressedHCC,
            RAFSummary, HEDISResult, HEDISSummary, ProcessingStats,
            Patient, Diagnosis, Encounter, ClinicalSentence,
            HEDISBPReading, HEDISLabResult, HEDISScreening,
            ExtractionResult,
        ]:
            count = session.execute(
                select(func.count()).select_from(model)
            ).scalar_one()
            stats[model.__tablename__] = count
        return stats
    finally:
        session.close()


# -----------------------------------------------------------------------
# Member-level queries (multi-chart aggregation)
# -----------------------------------------------------------------------

def get_member_charts(engine: Engine, patient_id: int) -> List[Dict[str, Any]]:
    """Get all charts linked to a patient/member."""
    from sqlalchemy import select

    session = _make_session(engine)
    try:
        charts = session.execute(
            select(Chart).where(Chart.patient_id == patient_id).order_by(Chart.created_at)
        ).scalars().all()
        return [
            {
                "chart_id": c.id,
                "filename": c.filename,
                "page_count": c.page_count,
                "status": c.status,
                "created_at": str(c.created_at) if c.created_at else None,
            }
            for c in charts
        ]
    finally:
        session.close()


def get_member_summary(engine: Engine, patient_id: int) -> Dict[str, Any]:
    """Aggregate data across all charts for a patient/member.

    Returns combined diagnoses, HCCs, RAF, encounters, and HEDIS from all charts.
    """
    from sqlalchemy import func, select

    session = _make_session(engine)
    try:
        # Get patient info
        patient = session.get(Patient, patient_id)
        if not patient:
            return {"error": f"Patient {patient_id} not found"}

        # Get all chart IDs for this patient
        chart_ids = [
            row[0] for row in
            session.execute(
                select(Chart.id).where(Chart.patient_id == patient_id)
            ).all()
        ]

        if not chart_ids:
            return {
                "patient_id": patient_id,
                "patient_name": patient.patient_name,
                "charts": 0,
                "message": "No charts linked to this patient",
            }

        # Aggregate diagnoses across all charts
        all_diagnoses = session.execute(
            select(Diagnosis).where(Diagnosis.chart_id.in_(chart_ids))
        ).scalars().all()

        active_dx = [d for d in all_diagnoses if d.negation_status == "active"]

        # Unique ICD codes across charts
        unique_icds: Dict[str, Dict] = {}
        for d in active_dx:
            if d.icd10_code and d.icd10_code not in unique_icds:
                unique_icds[d.icd10_code] = {
                    "icd10_code": d.icd10_code,
                    "description": d.description,
                    "charts_found_in": [],
                }
            if d.icd10_code:
                unique_icds[d.icd10_code]["charts_found_in"].append(d.chart_id)

        # Deduplicate chart lists
        for icd_info in unique_icds.values():
            icd_info["charts_found_in"] = sorted(set(icd_info["charts_found_in"]))
            icd_info["chart_count"] = len(icd_info["charts_found_in"])

        # Aggregate HCCs — union of payable HCCs across all charts
        all_hccs = session.execute(
            select(PayableHCC).where(PayableHCC.chart_id.in_(chart_ids))
        ).scalars().all()

        unique_hccs: Dict[str, Dict] = {}
        for h in all_hccs:
            if h.hcc_code not in unique_hccs:
                unique_hccs[h.hcc_code] = {
                    "hcc_code": h.hcc_code,
                    "hcc_description": h.hcc_description,
                    "raf_weight": float(h.raf_weight or 0),
                    "charts_found_in": [],
                }
            unique_hccs[h.hcc_code]["charts_found_in"].append(h.chart_id)

        for hcc_info in unique_hccs.values():
            hcc_info["charts_found_in"] = sorted(set(hcc_info["charts_found_in"]))

        # Aggregate RAF — sum unique HCC weights
        member_hcc_raf = sum(h["raf_weight"] for h in unique_hccs.values())

        # Aggregate encounters
        enc_count = session.execute(
            select(func.count()).select_from(Encounter).where(Encounter.chart_id.in_(chart_ids))
        ).scalar_one()

        # Aggregate HEDIS — take best status per measure across charts
        all_hedis = session.execute(
            select(HEDISResult).where(HEDISResult.chart_id.in_(chart_ids))
        ).scalars().all()

        hedis_by_measure: Dict[str, Dict] = {}
        for h in all_hedis:
            mid = h.measure_id
            if mid not in hedis_by_measure:
                hedis_by_measure[mid] = {
                    "measure_id": mid,
                    "measure_name": h.measure_name,
                    "best_status": h.status,
                    "applicable": h.applicable,
                    "compliant": h.compliant,
                }
            # "met" wins over "gap" wins over "not_applicable"
            if h.status == "met":
                hedis_by_measure[mid]["best_status"] = "met"
                hedis_by_measure[mid]["compliant"] = True
            elif h.status == "gap" and hedis_by_measure[mid]["best_status"] != "met":
                hedis_by_measure[mid]["best_status"] = "gap"
            if h.applicable:
                hedis_by_measure[mid]["applicable"] = True

        return {
            "patient_id": patient_id,
            "patient_name": patient.patient_name,
            "date_of_birth": patient.date_of_birth,
            "gender": patient.gender,
            "chart_count": len(chart_ids),
            "chart_ids": chart_ids,
            "diagnoses": {
                "total_across_charts": len(all_diagnoses),
                "active_across_charts": len(active_dx),
                "unique_active_icd_codes": len(unique_icds),
                "unique_icds": list(unique_icds.values()),
            },
            "hcc_summary": {
                "unique_payable_hccs": len(unique_hccs),
                "member_hcc_raf": round(member_hcc_raf, 3),
                "hccs": list(unique_hccs.values()),
            },
            "encounters_total": enc_count,
            "hedis": {
                "measures": list(hedis_by_measure.values()),
                "met": sum(1 for m in hedis_by_measure.values() if m["best_status"] == "met"),
                "gap": sum(1 for m in hedis_by_measure.values() if m["best_status"] == "gap"),
            },
        }
    finally:
        session.close()


def list_patients(engine: Engine) -> List[Dict[str, Any]]:
    """List all patients with chart counts."""
    from sqlalchemy import select

    session = _make_session(engine)
    try:
        patients = session.execute(
            select(Patient).order_by(Patient.id)
        ).scalars().all()
        return [
            {
                "patient_id": p.id,
                "patient_name": p.patient_name,
                "date_of_birth": p.date_of_birth,
                "gender": p.gender,
                "chart_count": p.chart_count or 1,
                "created_at": str(p.created_at) if p.created_at else None,
            }
            for p in patients
        ]
    finally:
        session.close()
