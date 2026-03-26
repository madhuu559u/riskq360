"""Regression tests for Codex lineage persistence."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.models import Base, DecisionTraceEvent, DiagnosisCandidate, DiagnosisCandidateEvidence, HEDISScreening
from database.persist import persist_chart_results


def _mk_db_path(prefix: str) -> Path:
    root = PROJECT_ROOT / "run_outputs"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{prefix}_{uuid.uuid4().hex[:8]}.db"


def test_codex_lineage_persists_to_sqlite() -> None:
    db_path = _mk_db_path("codex")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)

    hcc_pack = {
        "chart_id": "chart-1",
        "measurement_year": 2025,
        "payable_hccs": [],
        "suppressed_hccs": [],
        "unmapped_icds": [],
        "hierarchy_log": [],
        "raf_summary": {"total_raf_score": 0.3, "demographic_raf": 0.0, "hcc_raf": 0.3, "hcc_count": 1, "payable_hcc_count": 1, "suppressed_hcc_count": 0, "unmapped_icd_count": 0},
        "payable_icd_count": 1,
        "decision_trace": [
            {
                "assertion_id": 101,
                "icd10_code": "E11.65",
                "hcc_code": "HCC37",
                "candidate_state": "payable_candidate",
                "reason_code": "payable_hcc",
                "reason": "Mapped to final payable HCC37 after hierarchy review.",
                "page_number": 2,
                "exact_quote": "Type 2 diabetes mellitus with hyperglycemia (E11.65)",
                "effective_date": "2025-08-15",
                "category": "diagnosis",
                "condition_group_id_v3": "dx-1",
            }
        ],
        "candidate_summary": {"supported_candidate_count": 1, "payable_candidate_count": 1, "suppressed_candidate_count": 0, "rejected_candidate_count": 0},
    }
    hedis_result = {
        "summary": {"total_measures": 1, "applicable": 0, "met": 0, "gap": 0, "excluded": 0, "indeterminate": 1, "not_applicable": 0},
        "measures": [
            {
                "measure_id": "CDC-A1C-TEST",
                "measure_name": "Diabetes Care - HbA1c Testing",
                "status": "indeterminate",
                "applicable": False,
                "compliant": False,
                "trace": [{"rule": "enrollment_check", "result": False, "detail": "Enrollment data unavailable"}],
                "missing_data": ["continuous_enrollment"],
                "eligibility_reason": ["Enrollment data unavailable"],
                "compliance_reason": [],
                "gaps": [],
                "evidence_used": [],
            }
        ],
    }

    persist_chart_results(
        engine=engine,
        chart_name="chart-1",
        source_file="chart-1.pdf",
        assertions=[],
        hcc_pack=hcc_pack,
        hedis_result=hedis_result,
        measurement_year=2025,
    )

    with Session(engine) as session:
        candidate_count = session.scalar(select(func.count(DiagnosisCandidate.id)))
        evidence_count = session.scalar(select(func.count(DiagnosisCandidateEvidence.id)))
        trace_count = session.scalar(select(func.count(DecisionTraceEvent.id)))
        candidate = session.scalar(select(DiagnosisCandidate))

        assert candidate_count == 1
        assert evidence_count == 1
        assert trace_count == 2
        assert candidate is not None
        assert candidate.lifecycle_state == "payable_candidate"
        assert candidate.icd10_code == "E11.65"


def test_persist_truncates_overlong_hedis_screening_type() -> None:
    db_path = _mk_db_path("screening_truncate")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)

    hedis_result = {
        "summary": {"total_measures": 1, "applicable": 1, "met": 0, "gap": 1, "excluded": 0, "indeterminate": 0, "not_applicable": 0},
        "measures": [
            {
                "measure_id": "COL",
                "measure_name": "Colorectal Cancer Screening",
                "status": "gap",
                "applicable": True,
                "compliant": False,
                "trace": [],
                "gaps": [],
                "evidence_used": [],
            }
        ],
    }
    extraction_results = {
        "demographics": {},
        "risk": {"diagnoses": []},
        "encounters": {"encounters": []},
        "sentences": {"sentences": []},
        "hedis": {
            "screenings": [
                {
                    "screening_type": "This screening label is intentionally very long and should be truncated before DB insert",
                    "date": "2026-01-01",
                    "result": "declined",
                }
            ]
        },
    }

    persist_chart_results(
        engine=engine,
        chart_name="screening-test",
        source_file="screening-test.pdf",
        assertions=[],
        hcc_pack={
            "payable_hccs": [],
            "suppressed_hccs": [],
            "raf_summary": {
                "total_raf_score": 0.0,
                "demographic_raf": 0.0,
                "hcc_raf": 0.0,
                "hcc_count": 0,
                "payable_hcc_count": 0,
                "suppressed_hcc_count": 0,
                "unmapped_icd_count": 0,
            },
            "decision_trace": [],
        },
        hedis_result=hedis_result,
        measurement_year=2026,
        extraction_results=extraction_results,
    )

    with Session(engine) as session:
        screening = session.scalar(select(HEDISScreening))
        assert screening is not None
        assert screening.screening_type is not None
        assert len(screening.screening_type) <= 50
