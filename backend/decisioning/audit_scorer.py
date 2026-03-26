"""Audit risk scoring per diagnosis and per chart."""

from __future__ import annotations

from typing import Any, Dict, List


class AuditScorer:
    """Scores audit risk for diagnoses and charts."""

    def score_diagnosis(self, diagnosis: Dict[str, Any]) -> str:
        """Score audit risk for a single diagnosis.

        Returns: 'low', 'medium', or 'high'.
        """
        risk_score = 0.0

        confidence = diagnosis.get("confidence", 0)
        if confidence < 0.6:
            risk_score += 3.0
        elif confidence < 0.8:
            risk_score += 1.0

        # MEAT completeness
        meat = diagnosis.get("meat_evidence", {})
        meat_count = sum([
            bool(meat.get("monitored")),
            bool(meat.get("evaluated")),
            bool(meat.get("assessed")),
            bool(meat.get("treated")),
        ])
        if meat_count == 0:
            risk_score += 4.0
        elif meat_count == 1:
            risk_score += 2.0
        elif meat_count == 2:
            risk_score += 1.0

        # Polarity uncertainty
        polarity = diagnosis.get("polarity", "active")
        if polarity == "uncertain":
            risk_score += 3.0
        elif polarity == "historical":
            risk_score += 2.0

        # High RAF weight diagnoses need more scrutiny
        raf_weight = diagnosis.get("raf_weight", 0)
        if raf_weight > 1.0:
            risk_score += 2.0
        elif raf_weight > 0.5:
            risk_score += 1.0

        if risk_score >= 6.0:
            return "high"
        elif risk_score >= 3.0:
            return "medium"
        return "low"

    def score_chart(self, payable_hccs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Score overall audit risk for a chart's payable HCCs."""
        if not payable_hccs:
            return {"overall_risk": "low", "high_risk_count": 0, "flags": []}

        risks = []
        flags = []
        for hcc in payable_hccs:
            for icd in hcc.get("supported_icds", []):
                risk = self.score_diagnosis(icd)
                risks.append(risk)
                if risk == "high":
                    flags.append(f"{icd.get('icd10_code', '?')}: high audit risk")
            hcc["audit_risk"] = max(
                (self.score_diagnosis(icd) for icd in hcc.get("supported_icds", [])),
                default="low",
                key=lambda r: {"low": 0, "medium": 1, "high": 2}.get(r, 0),
            )

        high_count = risks.count("high")
        if high_count >= 3 or high_count / max(len(risks), 1) > 0.3:
            overall = "high"
        elif high_count >= 1 or risks.count("medium") >= 3:
            overall = "medium"
        else:
            overall = "low"

        return {
            "overall_risk": overall,
            "high_risk_count": high_count,
            "medium_risk_count": risks.count("medium"),
            "low_risk_count": risks.count("low"),
            "flags": flags,
        }
