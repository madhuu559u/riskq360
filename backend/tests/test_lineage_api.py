"""API regression tests for reviewer-facing lineage endpoints."""

from __future__ import annotations

import os
from datetime import date

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.pop("POSTGRES_HOST", None)
os.environ.pop("POSTGRES_USER", None)
os.environ.pop("POSTGRES_PASSWORD", None)
os.environ.pop("POSTGRES_DB", None)
os.environ.pop("POSTGRES_PORT", None)

from api.main import app
from database.models import Base, Chart, DecisionTraceEvent, DiagnosisCandidate, DiagnosisCandidateEvidence
from database.session import get_db


@pytest_asyncio.fixture
async def lineage_api_client(tmp_path):
    db_path = tmp_path / "lineage_api.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        chart = Chart(filename="sample-chart.pdf", file_path=str(tmp_path / "sample-chart.pdf"), status="completed")
        session.add(chart)
        await session.flush()

        payable = DiagnosisCandidate(
            chart_id=chart.id,
            candidate_key="candidate:e11_65",
            icd10_code="E11.65",
            hcc_code="HCC37",
            source_type="assertion",
            lifecycle_state="payable_candidate",
            reason_code="accepted_supported",
            reason_text="MEAT supported and hierarchy-safe",
            confidence=0.96,
            effective_date=date(2025, 8, 15),
            provider_name="Dr. Sarah Johnson",
            page_number=1,
            exact_quote="Type 2 diabetes with hyperglycemia",
            review_status="pending",
            payload={"candidate_state": "payable_candidate"},
        )
        rejected = DiagnosisCandidate(
            chart_id=chart.id,
            candidate_key="candidate:i10",
            icd10_code="I10",
            hcc_code=None,
            source_type="assertion",
            lifecycle_state="rejected_candidate",
            reason_code="missing_meat",
            reason_text="Diagnosis mention lacked MEAT support",
            confidence=0.44,
            effective_date=date(2025, 8, 15),
            provider_name="Dr. Sarah Johnson",
            page_number=2,
            exact_quote="History of hypertension",
            review_status="pending",
            payload={"candidate_state": "rejected_candidate"},
        )
        session.add_all([payable, rejected])
        await session.flush()

        session.add(DiagnosisCandidateEvidence(
            candidate_id=payable.id,
            chart_id=chart.id,
            page_number=1,
            char_start=14,
            char_end=48,
            exact_quote="Type 2 diabetes with hyperglycemia",
            section_name="assessment",
            is_primary=True,
            confidence=0.96,
        ))
        session.add_all([
            DecisionTraceEvent(
                chart_id=chart.id,
                entity_type="diagnosis_candidate",
                entity_key=payable.candidate_key,
                lifecycle_state="payable_candidate",
                reason_code="accepted_supported",
                reason_text="Accepted after HCC verification",
                icd10_code="E11.65",
                hcc_code="HCC37",
                event_date=date(2025, 8, 15),
                payload={"step": "verification"},
            ),
            DecisionTraceEvent(
                chart_id=chart.id,
                entity_type="diagnosis_candidate",
                entity_key=rejected.candidate_key,
                lifecycle_state="rejected_candidate",
                reason_code="missing_meat",
                reason_text="Rejected because only historical mention was found",
                icd10_code="I10",
                event_date=date(2025, 8, 15),
                payload={"step": "screening"},
            ),
            DecisionTraceEvent(
                chart_id=chart.id,
                entity_type="hedis_measure",
                entity_key="BCS-E",
                lifecycle_state="indeterminate",
                reason_code="measure_evaluation",
                reason_text="Enrollment data missing",
                measure_id="BCS-E",
                payload={"missing_data": ["continuous_enrollment"]},
            ),
        ])
        await session.commit()

        async def override_get_db():
            async with session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as client:
                yield client, chart.id, payable.id
        finally:
            app.dependency_overrides.clear()
            await engine.dispose()


@pytest.mark.asyncio
async def test_get_diagnosis_candidates_returns_lineage(lineage_api_client):
    client, chart_id, _ = lineage_api_client

    response = client.get(f"/api/clinical/{chart_id}/diagnosis-candidates", params={"include_trace": "true"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["diagnosis_candidates"]) == 2
    payable = next(item for item in body["diagnosis_candidates"] if item["candidate_key"] == "candidate:e11_65")
    assert payable["lifecycle_state"] == "payable_candidate"
    assert payable["evidence"][0]["section_name"] == "assessment"
    assert payable["trace"][0]["reason_code"] == "accepted_supported"


@pytest.mark.asyncio
async def test_get_diagnosis_candidate_detail_returns_evidence_and_trace(lineage_api_client):
    client, _, candidate_id = lineage_api_client

    response = client.get(f"/api/audit/diagnosis-candidates/{candidate_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["candidate"]["id"] == candidate_id
    assert body["evidence"][0]["exact_quote"] == "Type 2 diabetes with hyperglycemia"
    assert body["trace"][0]["entity_type"] == "diagnosis_candidate"


@pytest.mark.asyncio
async def test_get_chart_decision_trace_supports_entity_filters(lineage_api_client):
    client, chart_id, _ = lineage_api_client

    response = client.get(
        f"/api/audit/{chart_id}/decision-trace",
        params={"entity_type": "hedis_measure", "measure_id": "BCS-E"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["decision_trace"][0]["reason_code"] == "measure_evaluation"
    assert body["decision_trace"][0]["measure_id"] == "BCS-E"
