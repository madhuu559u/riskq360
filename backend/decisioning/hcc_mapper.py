"""ICD-10 → HCC V28 mapping with hierarchy suppression.

Adapted from ra-training-data-factory's hierarchy/v28.py.
Maps verified ICD codes to HCC categories and applies CMS hierarchy rules.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import structlog

from core.exceptions import HCCMappingError, HierarchyError

logger = structlog.get_logger(__name__)


class HCCMapper:
    """Maps ICD-10-CM codes to HCC categories and applies V28 hierarchy."""

    def __init__(self, reference_dir: Path, default_segment: str = "Community_NonDual_Aged") -> None:
        self.reference_dir = Path(reference_dir)
        self._icd_to_hcc: Dict[str, Dict[str, Any]] = {}
        self._hcc_labels: Dict[str, str] = {}
        self._hierarchy_groups: List[Dict[str, Any]] = []
        self._hcc_coefficients: Dict[str, float] = {}  # HCC code → RAF weight
        self._default_segment = default_segment
        self._is_loaded = False

    def _load(self) -> None:
        """Load V28 reference data."""
        if self._is_loaded:
            return

        # Load HCC coefficients first (so we can join to mapping table)
        coeff_file = self.reference_dir / "v28_coefficients.csv"
        if coeff_file.exists():
            with open(coeff_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    hcc = row.get("hcc_code", "").strip()
                    segment = row.get("segment", "").strip()
                    coeff = row.get("coefficient", row.get("coefficient_community_nondual_aged", "0"))
                    if hcc and segment == self._default_segment:
                        try:
                            self._hcc_coefficients[hcc] = float(coeff) if coeff else 0.0
                        except ValueError:
                            pass
            # Fallback: if no segment match, use any row (some files have different format)
            if not self._hcc_coefficients:
                with open(coeff_file, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        hcc = row.get("hcc_code", "").strip()
                        coeff = row.get("coefficient", row.get("coefficient_community_nondual_aged", "0"))
                        if hcc and hcc not in self._hcc_coefficients:
                            try:
                                self._hcc_coefficients[hcc] = float(coeff) if coeff else 0.0
                            except ValueError:
                                pass
            logger.info("hcc_mapper.coefficients_loaded", count=len(self._hcc_coefficients))

        # Load ICD → HCC mappings
        mapping_file = self.reference_dir / "v28_icd_hcc_mappings.csv"
        if mapping_file.exists():
            with open(mapping_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get("icd10_code", "").strip()
                    if code:
                        hcc_code = row.get("hcc_code", "")
                        # Get RAF weight from coefficients table (joined by HCC code)
                        raf_weight = self._hcc_coefficients.get(hcc_code, 0.0)
                        # Also try with "HCC " prefix removed/added
                        if raf_weight == 0.0:
                            raf_weight = self._hcc_coefficients.get(f"HCC {hcc_code.replace('HCC','').strip()}", 0.0)
                        self._icd_to_hcc[code] = {
                            "hcc_code": hcc_code,
                            "hcc_description": row.get("cc_label", ""),
                            "raf_weight": raf_weight,
                            "is_payment_hcc": row.get("is_payment_hcc", "1") == "1",
                        }
            logger.info("hcc_mapper.mappings_loaded", count=len(self._icd_to_hcc))
        else:
            logger.warning("hcc_mapper.mapping_file_not_found", path=str(mapping_file))

        # Load HCC labels
        labels_file = self.reference_dir / "v28_hcc_labels.json"
        if labels_file.exists():
            with open(labels_file, encoding="utf-8") as f:
                self._hcc_labels = json.load(f)

        # Load hierarchy rules
        hierarchy_file = self.reference_dir / "v28_hierarchy_rules.json"
        if hierarchy_file.exists():
            with open(hierarchy_file, encoding="utf-8") as f:
                raw = json.load(f)
                # Handle nested format: {"groups": {...}} or flat format: {...}
                groups = raw.get("groups", raw) if isinstance(raw, dict) else {}
                for group_name, group_data in groups.items():
                    if isinstance(group_data, dict):
                        ordered = group_data.get("ordered_hccs", [])
                        self._hierarchy_groups.append({
                            "group_name": group_name,
                            "ordered_hccs": ordered,
                        })
            logger.info("hcc_mapper.hierarchy_loaded", groups=len(self._hierarchy_groups))

        self._is_loaded = True

    def map_icds_to_hccs(self, verified_codes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map verified ICD-10 codes to HCC categories.

        Args:
            verified_codes: List of verified ICD dicts with icd10_code, supported=True, etc.

        Returns:
            List of HCC mapping dicts with icd10_code, hcc_code, raf_weight, etc.
        """
        self._load()

        mappings: List[Dict[str, Any]] = []
        for vc in verified_codes:
            code = vc.get("icd10_code", "")
            if not code:
                continue

            # Try both dotted (E11.65) and un-dotted (E1165) formats
            mapping = self._icd_to_hcc.get(code)
            if not mapping:
                mapping = self._icd_to_hcc.get(code.replace(".", ""))
            if mapping and mapping.get("is_payment_hcc"):
                mappings.append({
                    "icd10_code": code,
                    "icd10_description": vc.get("icd10_description", ""),
                    "hcc_code": mapping["hcc_code"],
                    "hcc_description": mapping["hcc_description"],
                    "raf_weight": mapping["raf_weight"],
                    "confidence": vc.get("confidence", 0),
                    "ml_confidence": vc.get("ml_confidence", 0),
                    "llm_confidence": vc.get("confidence", 0),
                    "polarity": vc.get("polarity", "active"),
                    "meat_evidence": vc.get("meat_evidence", {}),
                    "evidence_spans": vc.get("evidence_spans", []),
                    "date_of_service": vc.get("date_of_service"),
                    "provider": vc.get("provider"),
                    "is_suppressed": False,
                    "suppressed_by": None,
                })
            else:
                logger.debug("hcc_mapper.no_hcc_mapping", icd10=code)

        return mappings

    def apply_hierarchy(self, hcc_mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply CMS V28 hierarchy suppression rules.

        Higher-ranked HCCs suppress lower-ranked ones in the same group.
        E.g., HCC 35 (Pancreas Transplant) suppresses HCC 36, 37, 38 (Diabetes).

        Returns:
            List of payable HCC dicts with hierarchy information.
        """
        self._load()

        # Collect unique HCC codes present
        present_hccs: Set[str] = set()
        hcc_to_mappings: Dict[str, List[Dict]] = {}
        for m in hcc_mappings:
            hcc = m["hcc_code"].upper()
            present_hccs.add(hcc)
            hcc_to_mappings.setdefault(hcc, []).append(m)

        suppressed: Set[str] = set()
        suppression_log: List[Dict[str, str]] = []

        # Apply hierarchy rules
        for group in self._hierarchy_groups:
            ordered = group["ordered_hccs"]
            # Find the highest-ranked HCC that is present
            highest = None
            for hcc in ordered:
                hcc_upper = hcc.upper()
                if hcc_upper in present_hccs:
                    if highest is None:
                        highest = hcc_upper
                    else:
                        # This HCC is suppressed by the higher one
                        suppressed.add(hcc_upper)
                        suppression_log.append({
                            "suppressed_hcc": hcc_upper,
                            "suppressed_by": highest,
                            "group": group["group_name"],
                        })

        # Build payable HCC list
        payable_hccs: List[Dict[str, Any]] = []
        for hcc_code, mappings in hcc_to_mappings.items():
            is_suppressed = hcc_code in suppressed
            suppressor = None
            for s in suppression_log:
                if s["suppressed_hcc"] == hcc_code:
                    suppressor = s["suppressed_by"]
                    break

            # Mark suppression on individual mappings
            for m in mappings:
                m["is_suppressed"] = is_suppressed
                m["suppressed_by"] = suppressor

            if not is_suppressed:
                # Group ICDs supporting this HCC
                best_mapping = max(mappings, key=lambda m: m.get("confidence", 0))
                suppresses_list = [
                    s["suppressed_hcc"] for s in suppression_log
                    if s["suppressed_by"] == hcc_code
                ]
                payable_hccs.append({
                    "hcc_code": hcc_code,
                    "hcc_description": best_mapping.get("hcc_description", self._hcc_labels.get(hcc_code, "")),
                    "raf_weight": best_mapping["raf_weight"],
                    "hierarchy_applied": len(suppresses_list) > 0,
                    "suppresses": suppresses_list,
                    "supported_icds": mappings,
                    "audit_risk": "low",  # placeholder — audit scorer fills this
                })

        logger.info("hcc_mapper.hierarchy_done",
                     total_hccs=len(hcc_to_mappings),
                     payable=len(payable_hccs),
                     suppressed=len(suppressed))

        return payable_hccs
