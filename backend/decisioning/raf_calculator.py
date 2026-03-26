"""RAF score computation — encounter and member-year level.

Adapted from ra-training-data-factory's scoring/raf.py.
Uses CMS V28 coefficients by demographic segment.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from core.exceptions import RAFCalculationError

logger = structlog.get_logger(__name__)

# Default demographic segment
DEFAULT_SEGMENT = "coefficient_community_nondual_aged"


class RAFCalculator:
    """Computes Risk Adjustment Factor scores from payable HCCs."""

    def __init__(self, reference_dir: Path) -> None:
        self.reference_dir = Path(reference_dir)
        self._coefficients: Dict[str, Dict[str, float]] = {}
        self._is_loaded = False

    def _load(self) -> None:
        """Load V28 RAF coefficients."""
        if self._is_loaded:
            return

        coeff_file = self.reference_dir / "v28_coefficients.csv"
        coeff_json = self.reference_dir / "v28_coefficients.json"

        if coeff_json.exists():
            with open(coeff_json, encoding="utf-8") as f:
                raw = json.load(f)
            for hcc_code, data in raw.items():
                if isinstance(data, dict):
                    self._coefficients[hcc_code.upper()] = data
                else:
                    self._coefficients[hcc_code.upper()] = {DEFAULT_SEGMENT: float(data)}
            logger.info("raf.coefficients_loaded_json", count=len(self._coefficients))

        elif coeff_file.exists():
            with open(coeff_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    hcc = row.get("hcc_code", "").upper()
                    if hcc:
                        self._coefficients[hcc] = {}
                        for key, val in row.items():
                            if key != "hcc_code" and val:
                                try:
                                    self._coefficients[hcc][key] = float(val)
                                except ValueError:
                                    pass
            logger.info("raf.coefficients_loaded_csv", count=len(self._coefficients))
        else:
            logger.warning("raf.no_coefficients_found", dir=str(self.reference_dir))

        self._is_loaded = True

    def calculate(
        self,
        payable_hccs: List[Dict[str, Any]],
        demographics: Dict[str, Any] | None = None,
        segment: str = DEFAULT_SEGMENT,
    ) -> Dict[str, Any]:
        """Calculate RAF score from payable HCCs and demographics.

        Args:
            payable_hccs: List of payable HCC dicts from HCCMapper.
            demographics: Patient demographics for demographic RAF component.
            segment: Coefficient segment key.

        Returns:
            RAF summary dict with scores and breakdown.
        """
        self._load()

        hcc_raf = 0.0
        hcc_details: List[Dict[str, Any]] = []

        for phcc in payable_hccs:
            hcc_code = phcc.get("hcc_code", "").upper()
            coeff_data = self._coefficients.get(hcc_code, {})
            weight = coeff_data.get(segment, phcc.get("raf_weight", 0))

            hcc_raf += weight
            hcc_details.append({
                "hcc_code": hcc_code,
                "hcc_description": phcc.get("hcc_description", ""),
                "raf_weight": round(weight, 4),
                "icd_count": len(phcc.get("supported_icds", [])),
            })

        # Demographic RAF component (simplified — age + gender based)
        demographic_raf = self._calculate_demographic_raf(demographics)

        total_raf = round(demographic_raf + hcc_raf, 4)

        return {
            "total_raf_score": total_raf,
            "demographic_raf": round(demographic_raf, 4),
            "hcc_raf": round(hcc_raf, 4),
            "hcc_count": len(payable_hccs),
            "payable_hcc_count": len(payable_hccs),
            "suppressed_hcc_count": 0,  # filled by mapper
            "hcc_details": hcc_details,
            "segment": segment,
        }

    def _calculate_demographic_raf(self, demographics: Dict[str, Any] | None) -> float:
        """Calculate demographic component of RAF.

        Based on age-sex interaction from CMS tables.
        This is a simplified version — production would use full CMS demographic tables.
        """
        if not demographics:
            return 0.0

        age = demographics.get("age")
        gender = demographics.get("gender", "").lower()

        if age is None:
            return 0.0

        # Simplified CMS age-sex factors (community, non-dual, aged)
        # In production, these come from the full CMS coefficient tables
        if gender in ("female", "f"):
            if age < 35:
                return 0.197
            elif age < 45:
                return 0.243
            elif age < 55:
                return 0.314
            elif age < 65:
                return 0.414
            elif age < 70:
                return 0.423
            elif age < 75:
                return 0.473
            elif age < 80:
                return 0.545
            elif age < 85:
                return 0.625
            elif age < 90:
                return 0.729
            elif age < 95:
                return 0.814
            else:
                return 0.856
        else:  # male
            if age < 35:
                return 0.089
            elif age < 45:
                return 0.166
            elif age < 55:
                return 0.238
            elif age < 65:
                return 0.350
            elif age < 70:
                return 0.420
            elif age < 75:
                return 0.488
            elif age < 80:
                return 0.601
            elif age < 85:
                return 0.689
            elif age < 90:
                return 0.770
            elif age < 95:
                return 0.856
            else:
                return 0.920

    def get_coefficient(self, hcc_code: str, segment: str = DEFAULT_SEGMENT) -> float:
        """Look up a single HCC coefficient."""
        self._load()
        return self._coefficients.get(hcc_code.upper(), {}).get(segment, 0.0)
