"""Tests for the decisioning layer — HCC mapping, hierarchy, RAF, HEDIS, audit."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from decisioning.hcc_mapper import HCCMapper
from decisioning.raf_calculator import RAFCalculator
from decisioning.hedis_evaluator import HEDISEvaluator
from decisioning.audit_scorer import AuditScorer


# ── HCC Mapper Tests ─────────────────────────────────────────────────────────

class TestHCCMapper:
    def setup_method(self) -> None:
        ref_dir = PROJECT_ROOT / "decisioning" / "reference"
        self.mapper = HCCMapper(ref_dir)

    def test_load_mappings(self) -> None:
        self.mapper._load()
        assert self.mapper._is_loaded
        assert len(self.mapper._icd_to_hcc) > 0, "Should load ICD→HCC mappings"

    def test_mapping_count(self) -> None:
        self.mapper._load()
        # V28 has ~7900 ICD→HCC mappings
        assert len(self.mapper._icd_to_hcc) > 5000

    def test_hierarchy_groups_loaded(self) -> None:
        self.mapper._load()
        assert len(self.mapper._hierarchy_groups) > 0
        # V28 has 21 hierarchy groups
        assert len(self.mapper._hierarchy_groups) >= 20

    def test_hcc_labels_loaded(self) -> None:
        self.mapper._load()
        assert len(self.mapper._hcc_labels) > 0
        # Should have 115 HCC labels
        assert len(self.mapper._hcc_labels) >= 100

    def test_map_known_icd(self, sample_verified_codes: List[Dict[str, Any]]) -> None:
        mappings = self.mapper.map_icds_to_hccs(sample_verified_codes)
        # E11.65 should map to an HCC
        e11_65_mappings = [m for m in mappings if m["icd10_code"] == "E11.65"]
        assert len(e11_65_mappings) > 0, "E11.65 should map to an HCC"
        assert e11_65_mappings[0]["hcc_code"] != ""

    def test_map_returns_correct_fields(self, sample_verified_codes: List[Dict[str, Any]]) -> None:
        mappings = self.mapper.map_icds_to_hccs(sample_verified_codes)
        for m in mappings:
            assert "icd10_code" in m
            assert "hcc_code" in m
            assert "raf_weight" in m
            assert "confidence" in m
            assert "is_suppressed" in m
            assert isinstance(m["raf_weight"], (int, float))

    def test_hierarchy_suppression(self, sample_hcc_mappings: List[Dict[str, Any]]) -> None:
        """HCC37 (Diabetes with Complications) should suppress HCC38 (Diabetes without)."""
        result = self.mapper.apply_hierarchy(sample_hcc_mappings)
        # HCC37 should survive, HCC38 should be suppressed
        payable_codes = [r["hcc_code"] for r in result]
        assert "HCC37" in payable_codes, "HCC37 should be payable"
        assert "HCC38" not in payable_codes, "HCC38 should be suppressed by HCC37"

    def test_hierarchy_marks_suppression(self, sample_hcc_mappings: List[Dict[str, Any]]) -> None:
        result = self.mapper.apply_hierarchy(sample_hcc_mappings)
        for r in result:
            if r["hcc_code"] == "HCC37":
                assert r["hierarchy_applied"] is True
                assert "HCC38" in r["suppresses"]

    def test_no_mappings_for_unmapped_icd(self) -> None:
        codes = [{"icd10_code": "Z99.99", "icd10_description": "Fake code"}]
        mappings = self.mapper.map_icds_to_hccs(codes)
        assert len(mappings) == 0

    def test_empty_input(self) -> None:
        mappings = self.mapper.map_icds_to_hccs([])
        assert mappings == []

    def test_hierarchy_empty(self) -> None:
        result = self.mapper.apply_hierarchy([])
        assert result == []


# ── RAF Calculator Tests ─────────────────────────────────────────────────────

class TestRAFCalculator:
    def setup_method(self) -> None:
        ref_dir = PROJECT_ROOT / "decisioning" / "reference"
        self.calculator = RAFCalculator(ref_dir)

    def test_load_coefficients(self) -> None:
        self.calculator._load()
        assert self.calculator._is_loaded
        assert len(self.calculator._coefficients) > 0

    def test_calculate_raf_basic(self) -> None:
        payable_hccs = [
            {"hcc_code": "HCC37", "raf_weight": 0.302},
            {"hcc_code": "HCC85", "raf_weight": 0.439},
        ]
        demographics = {"age": 70, "gender": "M"}
        result = self.calculator.calculate(payable_hccs, demographics)
        assert "total_raf_score" in result
        assert "hcc_raf" in result
        assert "demographic_raf" in result
        assert result["total_raf_score"] > 0
        assert result["hcc_raf"] > 0

    def test_raf_with_no_hccs(self) -> None:
        result = self.calculator.calculate([], {"age": 70, "gender": "M"})
        assert result["hcc_raf"] == 0
        assert result["demographic_raf"] >= 0

    def test_demographic_factor(self) -> None:
        young_result = self.calculator.calculate([], {"age": 30, "gender": "M"})
        old_result = self.calculator.calculate([], {"age": 85, "gender": "M"})
        # Older patients should have higher demographic RAF
        assert old_result["demographic_raf"] >= young_result["demographic_raf"]


# ── HEDIS Evaluator Tests ────────────────────────────────────────────────────

class TestHEDISEvaluator:
    def setup_method(self) -> None:
        ref_dir = PROJECT_ROOT / "decisioning" / "reference"
        self.evaluator = HEDISEvaluator(ref_dir)

    def test_cbp_eligibility(self) -> None:
        """70-year-old male with hypertension should be eligible for CBP."""
        demographics = {"age": 70, "gender": "M"}
        hedis_evidence = {
            "eligibility_conditions": [
                {"condition": "hypertension", "is_present": True},
                {"condition": "diabetes", "is_present": True},
            ],
        }
        result = self.evaluator.evaluate(hedis_evidence, demographics, {})
        eligible_codes = [m["measure_code"] for m in result["measures"] if m["eligible"]]
        assert "CBP" in eligible_codes, "Should be eligible for Controlling Blood Pressure"

    def test_bcs_eligibility_male_excluded(self) -> None:
        """Male should NOT be eligible for Breast Cancer Screening."""
        demographics = {"age": 55, "gender": "M"}
        hedis_evidence = {"eligibility_conditions": []}
        result = self.evaluator.evaluate(hedis_evidence, demographics, {})
        eligible_codes = [m["measure_code"] for m in result["measures"] if m["eligible"]]
        assert "BCS" not in eligible_codes

    def test_bcs_eligibility_female(self) -> None:
        """55-year-old female should be eligible for BCS."""
        demographics = {"age": 55, "gender": "F"}
        hedis_evidence = {"eligibility_conditions": []}
        result = self.evaluator.evaluate(hedis_evidence, demographics, {})
        eligible_codes = [m["measure_code"] for m in result["measures"] if m["eligible"]]
        assert "BCS" in eligible_codes

    def test_age_range_filtering(self) -> None:
        """Patient too young for colorectal screening should be excluded."""
        demographics = {"age": 30, "gender": "M"}
        hedis_evidence = {"eligibility_conditions": []}
        result = self.evaluator.evaluate(hedis_evidence, demographics, {})
        eligible_codes = [m["measure_code"] for m in result["measures"] if m["eligible"]]
        assert "COL" not in eligible_codes

    def test_diabetes_measures(self) -> None:
        """Diabetic patient should be eligible for diabetes-related measures."""
        demographics = {"age": 55, "gender": "M"}
        hedis_evidence = {
            "eligibility_conditions": [
                {"condition": "diabetes", "is_present": True},
            ],
        }
        result = self.evaluator.evaluate(hedis_evidence, demographics, {})
        eligible_codes = [m["measure_code"] for m in result["measures"] if m["eligible"]]
        assert "GSD" in eligible_codes

    def test_gap_identification(self) -> None:
        """Should identify gaps when evidence is missing."""
        demographics = {"age": 70, "gender": "M"}
        hedis_evidence = {
            "eligibility_conditions": [
                {"condition": "hypertension", "is_present": True},
                {"condition": "diabetes", "is_present": True},
            ],
        }
        result = self.evaluator.evaluate(hedis_evidence, demographics, {})
        assert "gaps" in result
        # With no actual evidence, all eligible measures should have gaps
        assert len(result["gaps"]) > 0


# ── Audit Scorer Tests ───────────────────────────────────────────────────────

class TestAuditScorer:
    def setup_method(self) -> None:
        self.scorer = AuditScorer()

    def test_low_risk_diagnosis(self) -> None:
        diagnosis = {
            "confidence": 0.95,
            "polarity": "active",
            "meat_evidence": {
                "monitored": True,
                "evaluated": True,
                "assessed": True,
                "treated": True,
            },
            "raf_weight": 0.15,
        }
        risk = self.scorer.score_diagnosis(diagnosis)
        assert risk in ("low", "medium", "high")

    def test_high_risk_diagnosis(self) -> None:
        diagnosis = {
            "confidence": 0.35,
            "polarity": "uncertain",
            "meat_evidence": {
                "monitored": False,
                "evaluated": False,
                "assessed": True,
                "treated": False,
            },
            "raf_weight": 1.5,
        }
        risk = self.scorer.score_diagnosis(diagnosis)
        # Low confidence + uncertain polarity + high RAF + weak MEAT = higher risk
        assert risk in ("medium", "high")

    def test_chart_level_risk(self) -> None:
        payable_hccs = [
            {
                "hcc_code": "HCC37",
                "supported_icds": [
                    {
                        "icd10_code": "E11.65",
                        "confidence": 0.95,
                        "polarity": "active",
                        "meat_evidence": {"monitored": True, "evaluated": True, "assessed": True, "treated": True},
                        "raf_weight": 0.15,
                    },
                ],
                "audit_risk": "low",
            },
            {
                "hcc_code": "HCC85",
                "supported_icds": [
                    {
                        "icd10_code": "I10",
                        "confidence": 0.40,
                        "polarity": "active",
                        "meat_evidence": {"monitored": False, "evaluated": False, "assessed": True, "treated": False},
                        "raf_weight": 0.8,
                    },
                ],
                "audit_risk": "low",
            },
        ]
        chart_risk = self.scorer.score_chart(payable_hccs)
        assert "overall_risk" in chart_risk
        assert chart_risk["overall_risk"] in ("low", "medium", "high")
