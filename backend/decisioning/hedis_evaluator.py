"""HEDIS measure eligibility evaluation and gap identification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# HEDIS measure definitions
HEDIS_MEASURES = {
    "CBP": {
        "code": "CBP",
        "name": "Controlling Blood Pressure",
        "description": "Blood pressure <140/90",
        "target_systolic": 140,
        "target_diastolic": 90,
        "age_min": 18,
        "age_max": 85,
        "gender": "All",
        "requires_condition": "hypertension",
    },
    "GSD": {
        "code": "GSD",
        "name": "Glycemic Status Assessment",
        "description": "HbA1c <9% for diabetics",
        "target_value": 9.0,
        "age_min": 18,
        "age_max": 75,
        "gender": "All",
        "requires_condition": "diabetes",
    },
    "BCS": {
        "code": "BCS",
        "name": "Breast Cancer Screening",
        "description": "Mammogram within 2 years",
        "age_min": 50,
        "age_max": 74,
        "gender": "F",
        "lookback_months": 27,
    },
    "COL": {
        "code": "COL",
        "name": "Colorectal Cancer Screening",
        "description": "Colonoscopy within 10 years or FIT within 1 year",
        "age_min": 45,
        "age_max": 75,
        "gender": "All",
        "lookback_months": 120,
    },
    "CCS": {
        "code": "CCS",
        "name": "Cervical Cancer Screening",
        "description": "Pap smear within 3 years or HPV within 5 years",
        "age_min": 21,
        "age_max": 64,
        "gender": "F",
        "lookback_months": 36,
    },
    "OMW": {
        "code": "OMW",
        "name": "Osteoporosis Management in Women",
        "description": "DEXA scan or treatment for women with fracture",
        "age_min": 67,
        "age_max": 85,
        "gender": "F",
    },
    "DSF": {
        "code": "DSF",
        "name": "Depression Screening and Follow-Up",
        "description": "PHQ-2/PHQ-9 screening with follow-up if positive",
        "age_min": 12,
        "age_max": 999,
        "gender": "All",
    },
}


class HEDISEvaluator:
    """Evaluates HEDIS measure eligibility and identifies care gaps."""

    def __init__(self, reference_dir: Path) -> None:
        self.reference_dir = Path(reference_dir)

    def evaluate(
        self,
        hedis_evidence: Dict[str, Any],
        demographics: Dict[str, Any],
        encounters: Dict[str, Any],
        measurement_year: int = 2026,
    ) -> Dict[str, Any]:
        """Evaluate HEDIS measures and identify gaps.

        Args:
            hedis_evidence: Extracted HEDIS evidence from Pipeline 4.
            demographics: Patient demographics.
            encounters: Extracted encounters.
            measurement_year: HEDIS measurement year.

        Returns:
            HEDIS quality pack with measure statuses and gaps.
        """
        age = demographics.get("age")
        gender = (demographics.get("gender", "") or "").upper()[:1]

        # Determine eligibility conditions
        conditions = set()
        for ec in hedis_evidence.get("eligibility_conditions", []):
            if ec.get("is_present"):
                conditions.add(ec.get("condition", "").lower())

        measures_result = []
        gaps = []

        for measure_code, spec in HEDIS_MEASURES.items():
            # Check eligibility
            eligible = self._check_eligibility(age, gender, conditions, spec)

            if not eligible:
                measures_result.append({
                    "measure_code": measure_code,
                    "measure_name": spec["name"],
                    "eligible": False,
                    "status": "not_applicable",
                    "evidence": [],
                })
                continue

            # Evaluate measure
            status, evidence = self._evaluate_measure(
                measure_code, spec, hedis_evidence, measurement_year
            )

            measures_result.append({
                "measure_code": measure_code,
                "measure_name": spec["name"],
                "eligible": True,
                "status": status,
                "evidence": evidence,
                "target": spec.get("description", ""),
            })

            if status in ("not_met", "gap"):
                gaps.append({
                    "measure_code": measure_code,
                    "measure_name": spec["name"],
                    "gap_description": f"{spec['name']} — {spec['description']}",
                    "missing_evidence": self._describe_gap(measure_code, evidence),
                    "recommended_action": self._recommend_action(measure_code),
                    "priority": "standard",
                })

        return {
            "measurement_year": measurement_year,
            "measures": measures_result,
            "gaps": gaps,
            "total_eligible": sum(1 for m in measures_result if m["eligible"]),
            "total_met": sum(1 for m in measures_result if m["status"] == "met"),
            "total_gaps": len(gaps),
        }

    def _check_eligibility(
        self,
        age: int | None,
        gender: str,
        conditions: set,
        spec: Dict[str, Any],
    ) -> bool:
        """Check if patient is eligible for a measure."""
        if age is not None:
            if age < spec.get("age_min", 0) or age > spec.get("age_max", 999):
                return False

        spec_gender = spec.get("gender", "All")
        if spec_gender != "All" and gender and gender != spec_gender:
            return False

        required_condition = spec.get("requires_condition")
        if required_condition and required_condition not in conditions:
            return False

        return True

    def _evaluate_measure(
        self,
        code: str,
        spec: Dict[str, Any],
        evidence: Dict[str, Any],
        year: int,
    ) -> tuple[str, List[Dict]]:
        """Evaluate a specific measure against evidence."""
        if code == "CBP":
            return self._evaluate_cbp(spec, evidence)
        elif code == "GSD":
            return self._evaluate_gsd(spec, evidence)
        elif code == "BCS":
            return self._evaluate_screening(evidence, "mammogram", "BCS")
        elif code == "COL":
            return self._evaluate_screening(evidence, "colonoscopy", "COL")
        elif code == "CCS":
            return self._evaluate_screening(evidence, "pap_smear", "CCS")
        elif code == "DSF":
            return self._evaluate_dsf(evidence)
        elif code == "OMW":
            return self._evaluate_screening(evidence, "DEXA", "OMW")
        return "unknown", []

    def _evaluate_cbp(self, spec: Dict, evidence: Dict) -> tuple[str, List[Dict]]:
        """Evaluate Controlling Blood Pressure."""
        readings = evidence.get("blood_pressure_readings", [])
        if not readings:
            return "not_met", []

        # Use most recent reading
        latest = readings[-1]
        sys = latest.get("systolic", 999)
        dia = latest.get("diastolic", 999)
        met = sys < spec["target_systolic"] and dia < spec["target_diastolic"]

        return ("met" if met else "not_met"), [latest]

    def _evaluate_gsd(self, spec: Dict, evidence: Dict) -> tuple[str, List[Dict]]:
        """Evaluate Glycemic Status Assessment (A1C)."""
        labs = evidence.get("lab_results", [])
        a1c_labs = [l for l in labs if "a1c" in (l.get("test_name", "") or "").lower()
                    or "hba1c" in (l.get("test_name", "") or "").lower()]

        if not a1c_labs:
            return "not_met", []

        latest = a1c_labs[-1]
        value_str = str(latest.get("result_value", "")).replace("%", "").strip()
        try:
            value = float(value_str)
            met = value < spec["target_value"]
            return ("met" if met else "not_met"), [latest]
        except ValueError:
            return "not_met", [latest]

    def _evaluate_screening(self, evidence: Dict, screening_type: str, measure: str) -> tuple[str, List[Dict]]:
        """Evaluate screening measures (BCS, COL, CCS, OMW)."""
        screenings = evidence.get("screenings", [])
        relevant = [s for s in screenings
                    if screening_type.lower() in (s.get("screening_type", "") or "").lower()
                    or measure in (s.get("hedis_measure", "") or "")]

        if not relevant:
            return "not_met", []

        completed = [s for s in relevant if s.get("status") == "completed"]
        if completed:
            return "met", completed

        return "not_met", relevant

    def _evaluate_dsf(self, evidence: Dict) -> tuple[str, List[Dict]]:
        """Evaluate Depression Screening and Follow-Up."""
        ds = evidence.get("depression_screening", {})
        if not ds:
            return "not_met", []

        has_screening = ds.get("phq2_score") is not None or ds.get("phq9_score") is not None
        if not has_screening:
            return "not_met", []

        if ds.get("positive_screen") and not ds.get("follow_up_plan"):
            return "not_met", [ds]

        return "met", [ds]

    def _describe_gap(self, code: str, evidence: List) -> str:
        """Describe what's missing for a gap."""
        descriptions = {
            "CBP": "No BP reading below 140/90 found",
            "GSD": "No HbA1c result below 9% found",
            "BCS": "No mammogram found within lookback period",
            "COL": "No colonoscopy or FIT found within lookback period",
            "CCS": "No cervical cancer screening found within lookback period",
            "DSF": "No depression screening or missing follow-up for positive screen",
            "OMW": "No bone density assessment found",
        }
        return descriptions.get(code, f"Missing evidence for {code}")

    def _recommend_action(self, code: str) -> str:
        """Recommend action to close a gap."""
        actions = {
            "CBP": "Schedule BP check; consider medication adjustment",
            "GSD": "Order HbA1c test; review diabetes management",
            "BCS": "Schedule mammogram",
            "COL": "Schedule colonoscopy or order FIT test",
            "CCS": "Schedule Pap smear or HPV test",
            "DSF": "Administer PHQ-2/PHQ-9; document follow-up plan if positive",
            "OMW": "Order DEXA scan; evaluate fracture risk",
        }
        return actions.get(code, f"Review {code} measure requirements")
