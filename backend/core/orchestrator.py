"""Main pipeline orchestrator — MiniMax single-pass architecture.

Processes a medical chart PDF through the unified pipeline:
  1. PDF Ingestion → text extraction (+ OCR fallback)
  2. MiniMax Single-Pass Extraction → ALL assertions in one LLM call per chunk
  3. Deterministic Enrichment → codes, dates, quotes, vitals, conditions
  4. HCC Bridge → ICD→HCC V28 mapping + hierarchy + RAF
  5. HEDIS Bridge → measure evaluation (met/gap/not-applicable)
  6. Output Generation → JSON files per chart run
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from config.feature_flags import get_feature_flags
from config.settings import PipelineMode, get_settings
from core.exceptions import PipelineError

logger = structlog.get_logger(__name__)


class PipelineResult:
    """Container for the results of a full pipeline run."""

    def __init__(self, chart_id: str, chart_path: str) -> None:
        self.chart_id = chart_id
        self.chart_path = chart_path
        self.run_id = str(uuid.uuid4())
        self.started_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.status: str = "running"
        self.error: Optional[str] = None

        # MiniMax assertion output
        self.extraction_result: Dict[str, Any] = {}
        self.assertions: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {}
        self.meta: Dict[str, Any] = {}

        # HCC / RAF
        self.hcc_pack: Dict[str, Any] = {}
        self.raf_summary: Dict[str, Any] = {}

        # HEDIS
        self.hedis_result: Dict[str, Any] = {}

        # Pipeline log
        self.pipeline_log: List[Dict[str, Any]] = []

    def log_step(self, step: str, status: str, duration: float, details: Dict | None = None) -> None:
        self.pipeline_log.append({
            "step": step,
            "status": status,
            "duration_seconds": round(duration, 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(details or {}),
        })

    def finalize(self, status: str = "completed", error: str | None = None) -> None:
        self.completed_at = datetime.now(timezone.utc)
        self.status = status
        self.error = error


class Orchestrator:
    """Coordinates the MiniMax single-pass pipeline for chart processing."""

    def __init__(
        self,
        mode: PipelineMode = PipelineMode.FULL,
        config_overrides: Dict[str, Any] | None = None,
    ) -> None:
        self.settings = get_settings()
        self.flags = get_feature_flags()
        self.mode = mode

        # Apply mode-based feature flags
        self.flags.apply_mode(mode)

        # Config overrides
        self._overrides = config_overrides or {}

        # Lazy-loaded components
        self._extractor = None
        self._hcc_mapper = None
        self._raf_calculator = None

    # -- Lazy component loading ------------------------------------------------

    @property
    def extractor(self):
        if self._extractor is None:
            from extraction.assertion_extractor import AssertionExtractor

            api_key = (
                self._overrides.get("openai_api_key")
                or self.settings.openai.api_key
            )
            model = self._overrides.get("model") or self.settings.llm.active_llm_model or "gpt-4.1-mini"
            chunk_chars = self._overrides.get("chunk_chars", 9000)
            enable_ocr = self._overrides.get("enable_ocr", self.flags.ocr_fallback)
            max_parallel = self._overrides.get("max_parallel_chunks", 4)

            self._extractor = AssertionExtractor(
                openai_api_key=api_key,
                model=model,
                chunk_chars=chunk_chars,
                enable_ocr=enable_ocr,
                max_parallel_chunks=max_parallel,
            )
        return self._extractor

    @property
    def hcc_mapper(self):
        if self._hcc_mapper is None:
            from decisioning.hcc_mapper import HCCMapper
            self._hcc_mapper = HCCMapper(self.settings.paths.reference_data_dir)
        return self._hcc_mapper

    @property
    def raf_calculator(self):
        if self._raf_calculator is None:
            from decisioning.raf_calculator import RAFCalculator
            self._raf_calculator = RAFCalculator(self.settings.paths.reference_data_dir)
        return self._raf_calculator

    # -- Main pipeline ---------------------------------------------------------

    async def process_chart(self, chart_path: str | Path) -> PipelineResult:
        """Process a single medical chart through the full MiniMax pipeline."""
        chart_path = Path(chart_path)
        if not chart_path.exists():
            raise PipelineError(f"Chart file not found: {chart_path}")

        chart_id = chart_path.stem
        result = PipelineResult(chart_id=chart_id, chart_path=str(chart_path))

        logger.info("pipeline.start", chart_id=chart_id, mode=self.mode.value)
        total_start = time.time()

        try:
            # --- Step 1+2: MiniMax Single-Pass Extraction ---
            t0 = time.time()
            extraction = self.extractor.process_pdf(str(chart_path))
            result.extraction_result = extraction
            result.assertions = extraction.get("assertions", [])
            result.summary = extraction.get("summary", {})
            result.meta = extraction.get("meta", {})

            result.log_step("minimax_extraction", "completed", time.time() - t0, {
                "assertions_audited": len(result.assertions),
                "assertions_raw": extraction.get("meta", {}).get("assertions_total_raw", 0),
                "drops": extraction.get("meta", {}).get("drops_total", 0),
                "pages": extraction.get("meta", {}).get("page_count", 0),
                "model": extraction.get("meta", {}).get("model", ""),
            })
            logger.info("pipeline.extraction_done", chart_id=chart_id,
                        assertions=len(result.assertions))

            if not result.assertions:
                raise PipelineError("No assertions extracted from chart")

            # --- Step 3: HCC Mapping + RAF ---
            if self.flags.risk_adjustment and self.mode in (PipelineMode.FULL, PipelineMode.RISK_ONLY, PipelineMode.HCC_PACK):
                t0 = time.time()
                result.hcc_pack = self._build_hcc_pack(result)
                result.raf_summary = result.hcc_pack.get("raf_summary", {})
                result.log_step("hcc_mapping_raf", "completed", time.time() - t0, {
                    "payable_hccs": result.raf_summary.get("payable_hcc_count", 0),
                    "total_raf": result.raf_summary.get("total_raf_score", 0),
                })
                logger.info("pipeline.hcc_done", chart_id=chart_id,
                            payable_hccs=result.raf_summary.get("payable_hcc_count", 0))
            else:
                result.log_step("hcc_mapping_raf", "skipped", 0.0)

            # --- Step 4: HEDIS Evaluation ---
            if self.flags.hedis and self.mode in (PipelineMode.FULL, PipelineMode.HEDIS_ONLY):
                t0 = time.time()
                result.hedis_result = self._evaluate_hedis(result)
                result.log_step("hedis_evaluation", "completed", time.time() - t0, {
                    "measures": result.hedis_result.get("summary", {}).get("total_measures", 0),
                    "met": result.hedis_result.get("summary", {}).get("met", 0),
                    "gap": result.hedis_result.get("summary", {}).get("gap", 0),
                })
                logger.info("pipeline.hedis_done", chart_id=chart_id,
                            measures=result.hedis_result.get("summary", {}).get("total_measures", 0))
            else:
                result.log_step("hedis_evaluation", "skipped", 0.0)

            # --- Step 5: Save Outputs ---
            t0 = time.time()
            self._save_outputs(result)
            result.log_step("output_generation", "completed", time.time() - t0)

            result.finalize(status="completed")

        except Exception as e:
            logger.error("pipeline.failed", chart_id=chart_id, error=str(e))
            result.finalize(status="failed", error=str(e))
            raise

        total_time = time.time() - total_start
        logger.info("pipeline.completed", chart_id=chart_id,
                     total_seconds=round(total_time, 2), status=result.status)
        return result

    def process_chart_sync(self, chart_path: str | Path) -> PipelineResult:
        """Synchronous version of process_chart for CLI usage."""
        import asyncio
        return asyncio.run(self.process_chart(chart_path))

    # -- HCC Pack building ---

    def _build_hcc_pack(self, result: PipelineResult) -> Dict[str, Any]:
        """Build HCC pack from assertion output."""
        from core.hcc_bridge import build_hcc_pack

        # Extract demographic info from summary
        demographics = {}
        summary = result.summary
        if summary:
            dob_dates = summary.get("dob_dates_found", [])
            if dob_dates:
                demographics["date_of_birth"] = dob_dates[0]

        measurement_year = self._overrides.get("measurement_year", 2026)

        return build_hcc_pack(
            assertions=result.assertions,
            hcc_mapper=self.hcc_mapper,
            raf_calculator=self.raf_calculator,
            chart_id=result.chart_id,
            demographics=demographics,
            measurement_year=measurement_year,
        )

    # -- HEDIS evaluation ---

    def _evaluate_hedis(self, result: PipelineResult) -> Dict[str, Any]:
        """Evaluate HEDIS measures from assertions."""
        from core.hedis_bridge import evaluate_hedis_measures

        measurement_year = self._overrides.get("measurement_year", 2025)
        pdf_name = result.meta.get("pdf", "")

        dob = self._overrides.get("dob")
        gender = self._overrides.get("gender")

        return evaluate_hedis_measures(
            assertions=result.assertions,
            measurement_year=measurement_year,
            pdf_name=pdf_name,
            summary=result.summary,
            dob=dob,
            gender=gender,
        )

    # -- Output saving ---

    def _save_outputs(self, result: PipelineResult) -> None:
        """Save all output JSON files for the chart run.

        Generates evidence-rich sub-JSON files organized by domain:
        - assertions.json: Full extraction output
        - risk_adjustment.json: HCC/ICD/RAF with evidence and page numbers
        - hedis_quality.json: Measures with met/gap/evidence/page numbers
        - clinical_data.json: Medications, vitals, labs, encounters with evidence
        - diagnoses.json: All diagnoses with ICD codes and evidence
        - evidence_index.json: Page-by-page evidence map
        - pipeline_log.json: Processing log
        - summary.json: Human-readable overview
        """
        output_dir = self.settings.paths.output_dir / result.chart_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # -- Categorize assertions --
        diagnoses = [a for a in result.assertions if a.get("category") in ("diagnosis", "assessment")]
        medications = [a for a in result.assertions if a.get("category") == "medication"]
        vitals = [a for a in result.assertions if a.get("category") == "vital_sign"]
        labs = [a for a in result.assertions if a.get("category") in ("lab_result", "lab_order")]
        procedures = [a for a in result.assertions if a.get("category") in ("procedure", "screening")]
        encounters_list = []
        seen_dates = set()
        for a in result.assertions:
            ed = a.get("effective_date")
            if ed and ed not in seen_dates:
                seen_dates.add(ed)
                encounters_list.append({
                    "date": ed,
                    "page_number": a.get("page_number"),
                    "source": a.get("exact_quote", "")[:200],
                })
        screenings = [a for a in result.assertions if a.get("is_hedis_evidence")]
        counseling = [a for a in result.assertions if a.get("category") == "counseling"]
        social_history = [a for a in result.assertions if a.get("category") == "social_history"]

        # -- Build evidence-rich diagnosis list --
        dx_evidence = []
        for a in diagnoses:
            entry = {
                "concept": a.get("canonical_concept") or a.get("concept"),
                "status": a.get("status"),
                "category": a.get("category"),
                "icd_codes": a.get("icd_codes", []),
                "icd_codes_primary": a.get("icd_codes_primary"),
                "codes": a.get("codes", []),
                "effective_date": a.get("effective_date"),
                "page_number": a.get("page_number"),
                "exact_quote": a.get("exact_quote", ""),
                "char_start": a.get("char_start"),
                "char_end": a.get("char_end"),
                "is_payable_ra_candidate": a.get("is_payable_ra_candidate", False),
                "is_hcc_candidate": a.get("is_hcc_candidate", False),
                "is_hedis_evidence": a.get("is_hedis_evidence", False),
                "condition_group_id_v3": a.get("condition_group_id_v3"),
                "evidence_rank": a.get("evidence_rank"),
            }
            dx_evidence.append(entry)

        # -- Build medication list with evidence --
        med_evidence = []
        for a in medications:
            med_evidence.append({
                "name": a.get("medication_normalized") or a.get("canonical_concept") or a.get("concept"),
                "status": a.get("status"),
                "text": a.get("clean_text") or a.get("text"),
                "effective_date": a.get("effective_date"),
                "page_number": a.get("page_number"),
                "exact_quote": a.get("exact_quote", ""),
                "char_start": a.get("char_start"),
                "char_end": a.get("char_end"),
                "is_hedis_evidence": a.get("is_hedis_evidence", False),
            })

        # -- Build vitals list with evidence --
        vital_evidence = []
        for a in vitals:
            structured = a.get("structured") or {}
            vital_evidence.append({
                "concept": a.get("canonical_concept") or a.get("concept"),
                "text": a.get("clean_text") or a.get("text"),
                "systolic": structured.get("bp_systolic"),
                "diastolic": structured.get("bp_diastolic"),
                "effective_date": a.get("effective_date"),
                "page_number": a.get("page_number"),
                "exact_quote": a.get("exact_quote", ""),
                "char_start": a.get("char_start"),
                "char_end": a.get("char_end"),
            })

        # -- Build labs list with evidence --
        lab_evidence = []
        for a in labs:
            lab_evidence.append({
                "concept": a.get("canonical_concept") or a.get("concept"),
                "text": a.get("clean_text") or a.get("text"),
                "effective_date": a.get("effective_date"),
                "page_number": a.get("page_number"),
                "exact_quote": a.get("exact_quote", ""),
                "char_start": a.get("char_start"),
                "char_end": a.get("char_end"),
            })

        # -- Build page-level evidence index --
        page_evidence: Dict[int, List[Dict]] = {}
        for a in result.assertions:
            pg = a.get("page_number")
            if pg is None:
                continue
            if pg not in page_evidence:
                page_evidence[pg] = []
            page_evidence[pg].append({
                "category": a.get("category"),
                "concept": a.get("canonical_concept") or a.get("concept"),
                "status": a.get("status"),
                "effective_date": a.get("effective_date"),
                "exact_quote": (a.get("exact_quote") or "")[:200],
                "icd_codes": [c.get("code") for c in (a.get("icd_codes") or [])],
                "is_ra_candidate": a.get("is_payable_ra_candidate", False),
                "is_hedis_evidence": a.get("is_hedis_evidence", False),
            })

        # -- Assemble files --
        files = {
            # Full MiniMax output
            "assertions.json": {
                "meta": result.meta,
                "summary": result.summary,
                "drops": result.extraction_result.get("drops", []),
                "assertions": result.assertions,
            },

            # Risk Adjustment sub-JSON with full evidence
            "risk_adjustment.json": {
                "chart_id": result.chart_id,
                "measurement_year": self._overrides.get("measurement_year", 2026),
                "diagnoses": dx_evidence,
                "diagnoses_count": len(dx_evidence),
                "payable_ra_candidates": sum(1 for d in dx_evidence if d.get("is_payable_ra_candidate")),
                "hcc_candidates": sum(1 for d in dx_evidence if d.get("is_hcc_candidate")),
                "icd10_codes_found": result.summary.get("icd10cm_codes_found", []),
                "icd9_codes_found": result.summary.get("icd9cm_codes_found", []),
                "hcc_pack": result.hcc_pack,
                "raf_summary": result.raf_summary,
            },

            # HEDIS Quality sub-JSON with evidence
            "hedis_quality.json": result.hedis_result,

            # Clinical data sub-JSON with evidence and page numbers
            "clinical_data.json": {
                "chart_id": result.chart_id,
                "demographics": {
                    "dob": result.summary.get("dob_dates_found", [None])[0] if result.summary.get("dob_dates_found") else None,
                    "date_of_service": result.summary.get("best_guess_date_of_service"),
                },
                "medications": {
                    "items": med_evidence,
                    "count": len(med_evidence),
                    "unique": result.summary.get("unique_medications", []),
                },
                "vitals": {
                    "items": vital_evidence,
                    "count": len(vital_evidence),
                    "summary": result.summary.get("structured_vitals_summary", {}),
                },
                "labs": {
                    "items": lab_evidence,
                    "count": len(lab_evidence),
                },
                "procedures": {
                    "items": [{
                        "concept": a.get("canonical_concept") or a.get("concept"),
                        "codes": a.get("codes", []),
                        "effective_date": a.get("effective_date"),
                        "page_number": a.get("page_number"),
                        "exact_quote": a.get("exact_quote", ""),
                    } for a in procedures],
                    "count": len(procedures),
                },
                "encounters": {
                    "dates": encounters_list,
                    "count": len(encounters_list),
                    "page_best_dos": result.summary.get("page_best_dos", {}),
                },
                "screenings": {
                    "items": [{
                        "concept": a.get("canonical_concept") or a.get("concept"),
                        "effective_date": a.get("effective_date"),
                        "page_number": a.get("page_number"),
                        "exact_quote": a.get("exact_quote", ""),
                    } for a in screenings],
                    "count": len(screenings),
                },
                "counseling": {
                    "items": [{
                        "concept": a.get("canonical_concept") or a.get("concept"),
                        "text": a.get("clean_text") or a.get("text"),
                        "page_number": a.get("page_number"),
                        "exact_quote": a.get("exact_quote", ""),
                    } for a in counseling],
                    "count": len(counseling),
                },
                "social_history": {
                    "items": [{
                        "concept": a.get("canonical_concept") or a.get("concept"),
                        "text": a.get("clean_text") or a.get("text"),
                        "page_number": a.get("page_number"),
                        "exact_quote": a.get("exact_quote", ""),
                    } for a in social_history],
                    "count": len(social_history),
                },
            },

            # Page-level evidence index
            "evidence_index.json": {
                "chart_id": result.chart_id,
                "total_pages": result.meta.get("page_count", 0),
                "pages": {str(pg): items for pg, items in sorted(page_evidence.items())},
            },

            # Pipeline log
            "pipeline_log.json": result.pipeline_log,

            # Summary
            "summary.json": {
                "chart_id": result.chart_id,
                "run_id": result.run_id,
                "status": result.status,
                "mode": self.mode.value,
                "started_at": result.started_at.isoformat(),
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "total_seconds": (
                    (result.completed_at - result.started_at).total_seconds()
                    if result.completed_at else None
                ),
                "extraction": {
                    "assertions_count": len(result.assertions),
                    "pages": result.meta.get("page_count", 0),
                    "model": result.meta.get("model", ""),
                    "diagnoses": len(diagnoses),
                    "medications": len(medications),
                    "vitals": len(vitals),
                    "labs": len(labs),
                    "procedures": len(procedures),
                    "icd10_codes": len(result.summary.get("icd10cm_codes_found", [])),
                },
                "risk_adjustment": result.raf_summary,
                "hedis": result.hedis_result.get("summary", {}),
                "date_of_service": result.summary.get("best_guess_date_of_service"),
                "dob": result.summary.get("dob_dates_found", [None])[0] if result.summary.get("dob_dates_found") else None,
            },
        }

        for filename, data in files.items():
            filepath = output_dir / filename
            filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

        logger.info("outputs.saved", chart_id=result.chart_id, output_dir=str(output_dir),
                     files=list(files.keys()))
