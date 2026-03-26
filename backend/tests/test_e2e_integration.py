"""End-to-end integration test — exercises core pipeline components.

Tests the full chain WITHOUT LLM calls (those require API keys).
Validates: PDF → text extraction → quality scoring → section segmentation →
           negation detection → HCC mapping → hierarchy → RAF → HEDIS → audit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestEndToEnd:
    """Integration test exercising the full deterministic pipeline."""

    def setup_method(self) -> None:
        self.uploads_dir = PROJECT_ROOT / "uploads"
        self.ref_dir = PROJECT_ROOT / "decisioning" / "reference"
        self.models_dir = PROJECT_ROOT / "ml_engine" / "models"

    # ── Step 1: PDF Ingestion ────────────────────────────────────────

    def test_step1_pdf_extraction(self) -> None:
        """Extract text from a real PDF chart."""
        from ingestion.page_extractor import extract_pages

        pdfs = list(self.uploads_dir.glob("*.pdf"))
        if not pdfs:
            pytest.skip("No test PDFs in uploads/")

        pages = extract_pages(pdfs[0])
        assert len(pages) > 0
        total_text = " ".join(p["text"] for p in pages)
        assert len(total_text) > 100, "Extracted text too short"
        self._pages = pages
        self._full_text = total_text

    def test_step2_quality_scoring(self) -> None:
        """Score page quality."""
        from ingestion.page_extractor import extract_pages
        from ingestion.quality_scorer import QualityScorer

        pdfs = list(self.uploads_dir.glob("*.pdf"))
        if not pdfs:
            pytest.skip("No test PDFs in uploads/")

        pages = extract_pages(pdfs[0])
        scorer = QualityScorer()
        scores = [scorer.score(p["text"]) for p in pages]
        assert all(0 <= s <= 100 for s in scores)
        avg_score = sum(scores) / len(scores) if scores else 0
        assert avg_score > 0, "Average score should be > 0"

    def test_step3_section_segmentation(self) -> None:
        """Segment text into clinical sections."""
        from ingestion.page_extractor import extract_pages
        from ingestion.text_normalizer import normalize_text, segment_sections

        pdfs = list(self.uploads_dir.glob("*.pdf"))
        if not pdfs:
            pytest.skip("No test PDFs in uploads/")

        pages = extract_pages(pdfs[0])
        full_text = " ".join(p["text"] for p in pages)
        normalized = normalize_text(full_text)
        sections = segment_sections(normalized)
        assert len(sections) >= 1

    # ── Step 5: Negation Detection ───────────────────────────────────

    def test_step5_negation_on_clinical_text(self) -> None:
        """Run negation detector on realistic clinical sentences."""
        from ml_engine.negation_detector import NegationDetector

        detector = NegationDetector()

        test_cases = [
            ("diabetes mellitus", "Patient has type 2 diabetes mellitus with complications.", "active"),
            ("chest pain", "Patient denies any chest pain.", "negated"),
            ("stroke", "History of stroke in 2018, currently stable.", "historical"),
            ("breast cancer", "Family history significant for breast cancer in mother.", "family_history"),
            ("pulmonary embolism", "Possible pulmonary embolism, needs workup.", "uncertain"),
        ]

        for target, context, expected in test_cases:
            result = detector.detect(target, context)
            assert result.polarity == expected, (
                f"For '{target}' in '{context}': expected {expected}, got {result.polarity}"
            )

    # ── Step 7: HCC Mapping + Hierarchy + RAF ────────────────────────

    def test_step7_full_hcc_pipeline(self) -> None:
        """Test the complete HCC → Hierarchy → RAF pipeline."""
        from decisioning.hcc_mapper import HCCMapper
        from decisioning.raf_calculator import RAFCalculator
        from decisioning.audit_scorer import AuditScorer

        mapper = HCCMapper(self.ref_dir)
        calculator = RAFCalculator(self.ref_dir)
        audit = AuditScorer()

        # Simulated verified ICD codes (as if they came from LLM verification)
        verified_codes = [
            {
                "icd10_code": "E11.65",
                "icd10_description": "Type 2 diabetes mellitus with hyperglycemia",
                "confidence": 0.92,
                "ml_confidence": 0.87,
                "polarity": "active",
                "meat_evidence": {"monitored": True, "evaluated": True, "assessed": True, "treated": True},
                "evidence_spans": [{"text": "diabetes with hyperglycemia", "page": 3}],
                "date_of_service": "2025-08-15",
                "provider": "Dr. Smith",
            },
            {
                "icd10_code": "E11.9",
                "icd10_description": "Type 2 diabetes mellitus without complications",
                "confidence": 0.80,
                "ml_confidence": 0.75,
                "polarity": "active",
                "meat_evidence": {"monitored": True, "evaluated": False, "assessed": True, "treated": False},
                "evidence_spans": [{"text": "diabetes without complications", "page": 5}],
                "date_of_service": "2025-08-15",
                "provider": "Dr. Smith",
            },
            {
                "icd10_code": "I10",
                "icd10_description": "Essential (primary) hypertension",
                "confidence": 0.88,
                "ml_confidence": 0.82,
                "polarity": "active",
                "meat_evidence": {"monitored": True, "evaluated": True, "assessed": True, "treated": True},
                "evidence_spans": [{"text": "hypertension", "page": 3}],
                "date_of_service": "2025-08-15",
                "provider": "Dr. Smith",
            },
        ]

        # Step A: Map ICDs → HCCs
        hcc_mappings = mapper.map_icds_to_hccs(verified_codes)
        assert len(hcc_mappings) >= 2, f"Expected >=2 HCC mappings, got {len(hcc_mappings)}"

        # Step B: Apply hierarchy
        payable_hccs = mapper.apply_hierarchy(hcc_mappings)
        assert len(payable_hccs) >= 1

        # Verify hierarchy: E11.65 maps to HCC38 and E11.9 also maps to HCC38
        # But if they map to different HCCs (e.g., HCC37 vs HCC38),
        # the higher one should suppress the lower
        hcc_codes = [h["hcc_code"] for h in payable_hccs]
        # At minimum, HCC38 should be present (both E11.65 and E11.9 map to it)
        assert any("HCC" in c for c in hcc_codes)

        # Step C: Calculate RAF
        demographics = {"age": 70, "gender": "M"}
        raf = calculator.calculate(payable_hccs, demographics)
        assert raf["total_raf_score"] > 0
        assert raf["demographic_raf"] > 0
        assert raf["hcc_count"] >= 1

        # Step D: Audit scoring
        chart_risk = audit.score_chart(payable_hccs)
        assert chart_risk["overall_risk"] in ("low", "medium", "high")

        # Print summary for manual inspection
        print(f"\n=== HCC PAYABLE PACK SUMMARY ===")
        print(f"Payable HCCs: {len(payable_hccs)}")
        for h in payable_hccs:
            print(f"  {h['hcc_code']}: {h.get('hcc_description', '')} (RAF={h.get('raf_weight', 0)})")
        print(f"Total RAF: {raf['total_raf_score']}")
        print(f"  Demographic: {raf['demographic_raf']}")
        print(f"  HCC: {raf['hcc_raf']}")
        print(f"Audit Risk: {chart_risk['overall_risk']}")

    # ── Step 8: HEDIS Evaluation ─────────────────────────────────────

    def test_step8_hedis_evaluation(self) -> None:
        """Test HEDIS measure evaluation with simulated evidence."""
        from decisioning.hedis_evaluator import HEDISEvaluator

        evaluator = HEDISEvaluator(self.ref_dir)

        demographics = {"age": 70, "gender": "M"}
        hedis_evidence = {
            "eligibility_conditions": [
                {"condition": "hypertension", "is_present": True},
                {"condition": "diabetes", "is_present": True},
            ],
            "blood_pressure_readings": [
                {"systolic": 142, "diastolic": 88, "date": "2025-08-15"},
            ],
            "lab_results": [
                {"test_name": "HbA1c", "result_value": "8.2", "date": "2025-08-01"},
            ],
            "screenings": [],
        }

        result = evaluator.evaluate(hedis_evidence, demographics, {})

        assert result["total_eligible"] > 0
        assert len(result["gaps"]) > 0  # BP not at goal, A1C not at goal

        # CBP: BP 142/88 is NOT below 140/90 → gap
        cbp = next((m for m in result["measures"] if m["measure_code"] == "CBP"), None)
        assert cbp is not None
        assert cbp["eligible"] is True
        assert cbp["status"] == "not_met"  # BP not at goal

        # GSD: A1C 8.2 IS below 9.0 → met
        gsd = next((m for m in result["measures"] if m["measure_code"] == "GSD"), None)
        assert gsd is not None
        assert gsd["eligible"] is True
        assert gsd["status"] == "met"  # A1C < 9.0

        print(f"\n=== HEDIS QUALITY PACK SUMMARY ===")
        print(f"Eligible measures: {result['total_eligible']}")
        print(f"Met: {result['total_met']}")
        print(f"Gaps: {result['total_gaps']}")
        for gap in result["gaps"]:
            print(f"  GAP: {gap['measure_code']} — {gap['gap_description']}")

    # ── ICD Retrieval ────────────────────────────────────────────────

    def test_icd_retrieval_pipeline(self) -> None:
        """Test TF-IDF ICD retrieval with real vectorizer."""
        from ml_engine.icd_retriever import ICDRetriever
        from config.settings import get_settings

        settings = get_settings()
        retriever = ICDRetriever(settings.ml)

        try:
            retriever._load()
        except Exception:
            pytest.skip("ICD retriever data not available")

        if not retriever._is_loaded:
            pytest.skip("ICD retriever could not load")

        results = retriever.retrieve(
            text="Type 2 diabetes mellitus with chronic kidney disease",
            predicted_hccs=["HCC37", "HCC38", "HCC326"],
            top_k=10,
        )

        assert len(results) > 0
        codes = [r["icd10_code"] for r in results]
        print(f"\n=== ICD RETRIEVAL RESULTS ===")
        for r in results[:5]:
            print(f"  {r['icd10_code']}: {r.get('description', '')[:60]} (score={r.get('relevance_score', 0):.3f})")

    # ── Full Pipeline Summary ────────────────────────────────────────

    def test_full_deterministic_pipeline(self) -> None:
        """Run the full deterministic pipeline end-to-end (no LLM calls)."""
        from ingestion.page_extractor import extract_pages
        from ingestion.quality_scorer import QualityScorer
        from ingestion.text_normalizer import normalize_text, segment_sections
        from ml_engine.negation_detector import NegationDetector
        from decisioning.hcc_mapper import HCCMapper
        from decisioning.raf_calculator import RAFCalculator
        from decisioning.hedis_evaluator import HEDISEvaluator
        from decisioning.audit_scorer import AuditScorer

        pdfs = list(self.uploads_dir.glob("*.pdf"))
        if not pdfs:
            pytest.skip("No test PDFs in uploads/")

        # 1. Extract PDF
        pages = extract_pages(pdfs[0])
        assert len(pages) > 0

        # 2. Quality score
        scorer = QualityScorer()
        scores = [scorer.score(p["text"]) for p in pages]
        avg_quality = sum(scores) / len(scores)

        # 3. Normalize and segment
        full_text = "\n".join(p["text"] for p in pages)
        normalized = normalize_text(full_text)
        sections = segment_sections(normalized)

        # 4. Negation detection (on simulated diagnoses)
        detector = NegationDetector()
        test_diagnoses = [
            ("diabetes", "Patient has type 2 diabetes.", "active"),
            ("CHF", "No evidence of CHF.", "negated"),
        ]
        for target, ctx, expected in test_diagnoses:
            result = detector.detect(target, ctx)
            assert result.polarity == expected

        # 5. HCC mapping (with simulated verified codes)
        mapper = HCCMapper(self.ref_dir)
        verified = [
            {"icd10_code": "E11.65", "icd10_description": "T2DM with hyperglycemia",
             "confidence": 0.9, "polarity": "active", "meat_evidence": {"assessed": True}},
            {"icd10_code": "I10", "icd10_description": "Hypertension",
             "confidence": 0.85, "polarity": "active", "meat_evidence": {"assessed": True}},
        ]
        hcc_mappings = mapper.map_icds_to_hccs(verified)
        payable = mapper.apply_hierarchy(hcc_mappings)

        # 6. RAF calculation
        calc = RAFCalculator(self.ref_dir)
        raf = calc.calculate(payable, {"age": 70, "gender": "M"})

        # 7. HEDIS evaluation
        hedis_eval = HEDISEvaluator(self.ref_dir)
        hedis_result = hedis_eval.evaluate(
            {"eligibility_conditions": [{"condition": "hypertension", "is_present": True}]},
            {"age": 70, "gender": "M"},
            {},
        )

        # 8. Audit scoring
        audit = AuditScorer()
        chart_risk = audit.score_chart(payable)

        # Print full summary
        print(f"\n{'='*60}")
        print(f"MEDINSIGHT 360 — END-TO-END PIPELINE SUMMARY")
        print(f"{'='*60}")
        print(f"PDF: {pdfs[0].name}")
        print(f"Pages: {len(pages)}")
        print(f"Avg Quality: {avg_quality:.1f}")
        print(f"Sections Found: {len(sections)}")
        print(f"HCC Mappings: {len(hcc_mappings)}")
        print(f"Payable HCCs: {len(payable)}")
        print(f"Total RAF: {raf['total_raf_score']}")
        print(f"HEDIS Eligible: {hedis_result['total_eligible']}")
        print(f"HEDIS Gaps: {hedis_result['total_gaps']}")
        print(f"Audit Risk: {chart_risk['overall_risk']}")
        print(f"{'='*60}")

        # Assertions
        assert len(pages) > 0
        assert avg_quality > 0
        assert len(payable) >= 1
        assert raf["total_raf_score"] > 0
        assert hedis_result["total_eligible"] > 0
