from __future__ import annotations

from services.hedis_service import HEDISService


class _DummyMeasureRow:
    def __init__(self) -> None:
        self.id = 1
        self.chart_id = 40
        self.measure_id = "CBP"
        self.measure_name = "Controlling Blood Pressure"
        self.status = "met"
        self.applicable = True
        self.compliant = True
        self.evidence_used = [{"type": "vital", "value": "128/78", "page_number": 4}]
        self.gaps = []
        self.trace = [
            {"rule": "age_check", "result": True, "detail": "age in range"},
            {
                "rule": "__measure_payload__",
                "result": True,
                "detail": "Persisted enriched measure payload for API/UI rendering.",
                "meta": {
                    "eligibility_reason": ["Age and diagnosis criteria met"],
                    "compliance_reason": ["Most recent BP < 140/90"],
                    "decision_reasoning": {"status": "met", "evidence_pages": [4]},
                    "clinical_only_preview": {"status": "met"},
                },
            },
        ]
        self.measurement_year = 2026


class _DummySummaryRow:
    total_measures = 122
    applicable_count = 6
    met_count = 2
    gap_count = 3
    excluded_count = 0
    indeterminate_count = 1
    not_applicable_count = 116
    measurement_year = 2026


def test_serialize_measure_recovers_enriched_payload() -> None:
    svc = HEDISService(session=None)  # type: ignore[arg-type]
    serialized = svc._serialize(_DummyMeasureRow())

    assert serialized["measure_id"] == "CBP"
    assert serialized["decision_reasoning"]["status"] == "met"
    assert serialized["eligibility_reason"] == ["Age and diagnosis criteria met"]
    assert serialized["clinical_only_preview"]["status"] == "met"
    assert all(t.get("rule") != "__measure_payload__" for t in serialized["trace"])


def test_serialize_summary_includes_inactive_and_status_breakdown() -> None:
    svc = HEDISService(session=None)  # type: ignore[arg-type]
    serialized = svc._serialize_summary(_DummySummaryRow())

    assert serialized["total_measures"] == 122
    assert serialized["applicable"] == 6
    assert serialized["met"] == 2
    assert serialized["gap"] == 3
    assert serialized["indeterminate"] == 1
    assert serialized["excluded"] == 0
    assert serialized["inactive"] == 116


def test_preview_summary_uses_clinical_preview_when_present() -> None:
    svc = HEDISService(session=None)  # type: ignore[arg-type]
    measures = [
        {
            "measure_id": "COL",
            "status": "indeterminate",
            "applicable": False,
            "clinical_only_preview": {"status": "gap", "applicable": True},
        },
        {
            "measure_id": "CBP",
            "status": "inactive",
            "applicable": False,
        },
    ]
    summary = svc._summarize_preview(measures, measurement_year=2026)
    assert summary["total_measures"] == 2
    assert summary["inactive"] == 1
    assert summary["applicable"] == 1
    assert summary["gap"] == 1
