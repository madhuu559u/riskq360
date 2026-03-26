"""Tests for core types."""

from datetime import date

from hedis_engine.types import (
    ComplianceStatus,
    Demographics,
    DiagnosisEvent,
    DiagnosisStatus,
    EvidenceRef,
    EvidenceUsed,
    GapDetail,
    Gender,
    MeasureResult,
    MeasureStatus,
    MemberEventStore,
    MemberHedisResults,
    TraceEntry,
)


def test_evidence_ref_to_dict():
    ref = EvidenceRef(pdf="chart.pdf", page_number=3, exact_quote="test")
    d = ref.to_dict()
    assert d["pdf"] == "chart.pdf"
    assert d["page"] == 3
    assert d["exact_quote"] == "test"


def test_evidence_ref_empty():
    ref = EvidenceRef()
    assert ref.to_dict() == {}


def test_trace_entry_to_dict():
    t = TraceEntry(rule="age_check", result=True, detail="Age 60")
    d = t.to_dict()
    assert d["rule"] == "age_check"
    assert d["result"] is True
    assert d["detail"] == "Age 60"


def test_gap_detail_to_dict():
    g = GapDetail(
        gap_type="missing_lab",
        description="Missing A1C",
        required_event="A1C",
        window_start=date(2025, 1, 1),
        window_end=date(2025, 12, 31),
    )
    d = g.to_dict()
    assert d["type"] == "missing_lab"
    assert "2025-01-01..2025-12-31" in d["window"]


def test_evidence_used_to_dict():
    e = EvidenceUsed(
        event_type="lab",
        code="A1C",
        value="7.8",
        event_date=date(2025, 9, 1),
    )
    d = e.to_dict()
    assert d["type"] == "lab"
    assert d["code"] == "A1C"
    assert d["value"] == "7.8"
    assert d["date"] == "2025-09-01"


def test_measure_result_to_dict():
    r = MeasureResult(
        measure_id="TEST-1",
        measure_name="Test Measure",
        applicable=True,
        compliant=ComplianceStatus.COMPLIANT,
        status=MeasureStatus.MET,
    )
    d = r.to_dict()
    assert d["id"] == "TEST-1"
    assert d["applicable"] is True
    assert d["compliant"] is True
    assert d["status"] == "met"


def test_member_results_summary():
    r = MemberHedisResults(member_id="M1", measurement_year=2025)
    r.measures = [
        MeasureResult(measure_id="A", applicable=True, status=MeasureStatus.MET),
        MeasureResult(measure_id="B", applicable=True, status=MeasureStatus.GAP),
        MeasureResult(measure_id="C", applicable=False, status=MeasureStatus.NOT_APPLICABLE),
    ]
    s = r.summary
    assert s["applicable"] == 2
    assert s["met"] == 1
    assert s["gap"] == 1
    assert s["not_applicable"] == 1


def test_member_event_store_defaults():
    store = MemberEventStore()
    assert store.demographics.gender == Gender.UNKNOWN
    assert store.diagnoses == []
    assert store.procedures == []
    assert store.labs == []
    assert store.vitals == []
    assert store.medications == []
    assert store.encounters == []
    assert store.immunizations == []


def test_diagnosis_status_values():
    assert DiagnosisStatus.ACTIVE.value == "active"
    assert DiagnosisStatus.NEGATED.value == "negated"
    assert DiagnosisStatus.RESOLVED.value == "resolved"
    assert DiagnosisStatus.HISTORICAL.value == "historical"
    assert DiagnosisStatus.FAMILY_HISTORY.value == "family_history"
    assert DiagnosisStatus.UNCERTAIN.value == "uncertain"
