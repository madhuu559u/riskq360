"""HCC Ensemble V4 — Multi-track ICD/HCC extraction with LLM verification.

Combines 3 independent extraction strategies:
  Track 1: LLM extraction — ICD codes from Pipeline 3 (risk_dx) mapped to HCCs
  Track 2: TF-IDF classifier — 115 HCC multi-label classification from clinical text
  Track 3: Trained BioClinicalBERT — deep learning HCC prediction from clinical text

Then applies:
  Track 4: LLM verification gate — confirms each HCC with evidence check
  Hierarchy: V28 suppression rules
  RAF: Coefficient-based scoring

Usage:
    from core.hcc_ensemble import EnsembleConfig, run_ensemble_hcc

    result = run_ensemble_hcc(
        risk_data=extraction_results["risk"],
        clinical_text=full_text,
        hcc_mapper=mapper,
        client=openai_client,
        model="gpt-4o-mini",
        config=EnsembleConfig(),
    )
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class EnsembleConfig:
    """Configuration for the ensemble HCC extraction."""
    # Track enables
    enable_tfidf: bool = True
    enable_bert: bool = True
    enable_llm_verification: bool = True

    # Thresholds
    tfidf_threshold: float = 0.2
    bert_threshold: float = 0.5
    llm_min_confidence: float = 0.3

    # Model paths (relative to PROJECT_ROOT)
    tfidf_vectorizer_path: str = "ml_engine/models/tfidf_vectorizer.pkl"
    tfidf_classifier_path: str = "ml_engine/models/tfidf_classifier.pkl"
    tfidf_thresholds_path: str = "ml_engine/models/tfidf_thresholds.npy"
    label_mapping_path: str = "ml_engine/models/bioclinicalbert/label_mapping.json"
    bert_model_path: str = ""  # Absolute path, auto-detected

    # Processing
    max_text_length: int = 2500  # BERT input limit
    verification_text_limit: int = 2000  # LLM verification context
    measurement_year: int = 2026


# ---------------------------------------------------------------------------
# TF-IDF HCC Classifier
# ---------------------------------------------------------------------------

class TFIDFHCCClassifier:
    """Multi-label HCC classifier using pre-trained TF-IDF + classifier."""

    def __init__(self, config: EnsembleConfig):
        self.vectorizer = None
        self.classifier = None
        self.idx_to_hcc: Dict[str, str] = {}
        self.thresholds: Optional[np.ndarray] = None
        self._load(config)

    def _load(self, config: EnsembleConfig):
        vec_path = PROJECT_ROOT / config.tfidf_vectorizer_path
        clf_path = PROJECT_ROOT / config.tfidf_classifier_path
        mapping_path = PROJECT_ROOT / config.label_mapping_path
        thresh_path = PROJECT_ROOT / config.tfidf_thresholds_path

        if not vec_path.exists() or not clf_path.exists():
            log.warning("TF-IDF models not found at %s", vec_path.parent)
            return

        try:
            with open(vec_path, "rb") as f:
                self.vectorizer = pickle.load(f)
            with open(clf_path, "rb") as f:
                self.classifier = pickle.load(f)

            if mapping_path.exists():
                with open(mapping_path) as f:
                    mapping = json.load(f)
                self.idx_to_hcc = mapping.get("idx_to_hcc", {})

            if thresh_path.exists():
                self.thresholds = np.load(str(thresh_path))

            log.info("TF-IDF classifier loaded (%d HCC labels)", len(self.idx_to_hcc))
        except Exception as e:
            log.error("Failed to load TF-IDF models: %s", e)

    def predict(self, text: str, threshold: float = 0.2) -> List[Dict[str, Any]]:
        if not self.vectorizer or not self.classifier:
            return []
        try:
            X = self.vectorizer.transform([text])
            probs = self.classifier.predict_proba(X)[0]

            predictions = []
            for idx, prob in enumerate(probs):
                t = self.thresholds[idx] if self.thresholds is not None and idx < len(self.thresholds) else threshold
                if prob >= t:
                    hcc = self.idx_to_hcc.get(str(idx), f"HCC{idx}").replace(" ", "")
                    predictions.append({
                        "hcc_code": hcc,
                        "confidence": round(float(prob), 4),
                        "source": "tfidf",
                    })
            return predictions
        except Exception as e:
            log.error("TF-IDF prediction error: %s", e)
            return []


# ---------------------------------------------------------------------------
# Trained BioClinicalBERT HCC Predictor
# ---------------------------------------------------------------------------

class BERTHCCPredictor:
    """Multi-label HCC predictor using trained BioClinicalBERT."""

    def __init__(self, config: EnsembleConfig):
        self.model = None
        self.tokenizer = None
        self.idx_to_hcc: Dict[int, str] = {}
        self.thresholds: Optional[np.ndarray] = None
        self._load(config)

    def _find_model_path(self, config: EnsembleConfig) -> Optional[str]:
        """Find the best_model.pt file."""
        candidates = [
            config.bert_model_path,
            str(PROJECT_ROOT / "ml_engine/models/bioclinicalbert/model/best_model.pt"),
            "C:/Next-Era/ClaudeProjects/MLDataPrep/ra-training-data-factory/models/hcc_classifier/best_model.pt",
            str(PROJECT_ROOT / "ml_engine/models/bioclinicalbert/best_model.pt"),
        ]
        for p in candidates:
            if p and os.path.exists(p):
                return p
        return None

    def _load(self, config: EnsembleConfig):
        model_path = self._find_model_path(config)
        if not model_path:
            log.info("BioClinicalBERT model not found — BERT track disabled")
            return

        try:
            import torch
            from transformers import AutoTokenizer, AutoModel, AutoConfig
            import torch.nn as nn

            log.info("Loading BioClinicalBERT from %s", model_path)
            checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)

            model_cfg = checkpoint.get("config", {}).get("model", {})
            model_name = model_cfg.get("name", "emilyalsentzer/Bio_ClinicalBERT")
            num_labels = model_cfg.get("num_labels", 115)
            dropout = model_cfg.get("dropout", 0.1)

            hcc_to_idx = checkpoint.get("hcc_to_idx", {})
            self.idx_to_hcc = {v: k for k, v in hcc_to_idx.items()}

            self.tokenizer = AutoTokenizer.from_pretrained(model_name)

            # Build model architecture
            class HCCClassifier(nn.Module):
                def __init__(self, mn, nl, dr):
                    super().__init__()
                    self.config = AutoConfig.from_pretrained(mn)
                    self.encoder = AutoModel.from_pretrained(mn, config=self.config)
                    self.dropout = nn.Dropout(dr)
                    self.classifier = nn.Linear(self.config.hidden_size, nl)

                def forward(self, input_ids, attention_mask):
                    out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
                    cls = self.dropout(out.last_hidden_state[:, 0, :])
                    return {"logits": self.classifier(cls)}

            self.model = HCCClassifier(model_name, num_labels, dropout)
            self.model.load_state_dict(checkpoint["model_state_dict"], strict=False)
            self.model.eval()

            # Load optimal thresholds if available
            thresh_path = os.path.join(os.path.dirname(model_path), "optimal_thresholds.npy")
            if os.path.exists(thresh_path):
                self.thresholds = np.load(thresh_path)

            log.info("BioClinicalBERT loaded (%d labels)", len(self.idx_to_hcc))
        except ImportError:
            log.warning("torch/transformers not installed — BERT track disabled")
        except Exception as e:
            log.error("Failed to load BioClinicalBERT: %s", e)

    def predict(self, text: str, threshold: float = 0.5) -> List[Dict[str, Any]]:
        if not self.model or not self.tokenizer:
            return []
        try:
            import torch
            inputs = self.tokenizer(
                text[:2500], return_tensors="pt",
                truncation=True, max_length=512, padding=True,
            )
            with torch.no_grad():
                logits = self.model(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                )["logits"].numpy()[0]

            probs = 1.0 / (1.0 + np.exp(-logits))  # sigmoid

            predictions = []
            for idx, prob in enumerate(probs):
                t = self.thresholds[idx] if self.thresholds is not None and idx < len(self.thresholds) else threshold
                if prob >= t:
                    hcc = self.idx_to_hcc.get(idx, f"HCC{idx}").replace(" ", "")
                    predictions.append({
                        "hcc_code": hcc,
                        "confidence": round(float(prob), 4),
                        "source": "trained_bert",
                    })
            return predictions
        except Exception as e:
            log.error("BERT prediction error: %s", e)
            return []


# ---------------------------------------------------------------------------
# LLM Verification
# ---------------------------------------------------------------------------

# Common HCC descriptions for verification prompts
HCC_DESCRIPTIONS = {
    "HCC18": "Diabetes with Chronic Complications",
    "HCC19": "Diabetes without Complications",
    "HCC22": "Protein-Calorie Malnutrition",
    "HCC37": "Diabetes with Chronic Complications",
    "HCC38": "Diabetes without Complications",
    "HCC48": "Anemia",
    "HCC62": "Myeloproliferative Disorder",
    "HCC70": "Parkinson's Disease",
    "HCC85": "Congestive Heart Failure",
    "HCC86": "Acute Myocardial Infarction",
    "HCC96": "Cardiac Arrhythmias",
    "HCC108": "Hypertensive Heart Disease",
    "HCC111": "COPD",
    "HCC123": "Glaucoma",
    "HCC124": "Macular Degeneration",
    "HCC125": "Cataract",
    "HCC137": "Obesity / BPH",
    "HCC138": "CKD Stage 1-3",
    "HCC139": "CKD Stage 5 / ESRD",
    "HCC145": "Heart Valve Disorders",
    "HCC151": "Major Depression / Dementia",
    "HCC152": "Dysthymic Disorder / Anxiety",
    "HCC155": "Bipolar / Recurrent Depression",
    "HCC156": "Substance Use Disorder",
    "HCC159": "Hyperlipidemia",
    "HCC186": "Nicotine Dependence",
    "HCC189": "Other Specified Conditions",
    "HCC202": "Hypothyroidism",
    "HCC329": "CKD Stage 3a",
    "HCC330": "CKD Stage 3b-4",
}


def verify_hcc_with_llm(
    client: Any,
    model: str,
    hcc_code: str,
    evidence: str,
    min_confidence: float = 0.3,
) -> Dict[str, Any]:
    """Verify a single HCC prediction using LLM structured output."""
    diagnosis_name = HCC_DESCRIPTIONS.get(hcc_code, hcc_code)

    prompt = f"""You are a medical coding expert verifying HCC predictions for risk adjustment.

Diagnosis Claimed: {diagnosis_name} ({hcc_code})

Clinical Evidence:
{evidence[:2000]}

Questions:
1. Is this diagnosis ACTUALLY present and documented in the evidence above?
2. Is there evidence of active management (monitoring, evaluation, treatment)?
3. What is your confidence level (0.0-1.0)?

Respond in JSON:
{{"is_verified": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "is_verified": result.get("is_verified", False),
            "confidence": result.get("confidence", 0.0),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        log.warning("LLM verification error for %s: %s", hcc_code, e)
        return {"is_verified": False, "confidence": 0.0, "reasoning": f"error: {e}"}


# ---------------------------------------------------------------------------
# Main Ensemble Function
# ---------------------------------------------------------------------------

def run_ensemble_hcc(
    risk_data: Dict[str, Any],
    clinical_text: str,
    hcc_mapper: Any,
    client: Optional[Any] = None,
    model: str = "gpt-4o-mini",
    config: Optional[EnsembleConfig] = None,
) -> Dict[str, Any]:
    """Run the full 4-track ensemble HCC extraction.

    Args:
        risk_data: Output from Pipeline 3 (risk_dx) — dict with "diagnoses" list
        clinical_text: Full clinical text from PDF
        hcc_mapper: decisioning.hcc_mapper.HCCMapper instance (loaded)
        client: OpenAI client (for LLM verification)
        model: LLM model name
        config: Ensemble configuration

    Returns:
        HCC pack dict with payable_hccs, suppressed_hccs, raf_summary, ensemble_metadata
    """
    cfg = config or EnsembleConfig()
    start = time.time()

    hcc_mapper._load()

    # Collect all HCC candidates: hcc_code -> {info}
    all_candidates: Dict[str, Dict[str, Any]] = {}
    track_counts = {"llm": 0, "tfidf": 0, "bert": 0}

    # -----------------------------------------------------------------------
    # Track 1: LLM Extraction (from risk pipeline diagnoses)
    # -----------------------------------------------------------------------
    diagnoses = risk_data.get("diagnoses", [])
    active_dx = [d for d in diagnoses if (d.get("negation_status") or "active").lower() == "active"]
    negated_count = sum(1 for d in diagnoses if (d.get("negation_status") or "").lower() == "negated")
    unmapped_icds: List[Dict] = []

    for dx in active_dx:
        icd10 = (dx.get("icd10_code") or "").strip().upper()
        if not icd10:
            continue

        # Look up HCC mapping (try multiple formats)
        mapping = hcc_mapper._icd_to_hcc.get(icd10)
        if not mapping:
            mapping = hcc_mapper._icd_to_hcc.get(icd10.replace(".", ""))
        if not mapping and len(icd10) > 3 and "." not in icd10:
            mapping = hcc_mapper._icd_to_hcc.get(icd10[:3] + "." + icd10[3:])

        if not mapping:
            unmapped_icds.append(dx)
            continue

        hcc_code = mapping.get("hcc_code", "")
        if not hcc_code:
            unmapped_icds.append(dx)
            continue

        if hcc_code not in all_candidates or all_candidates[hcc_code]["confidence"] < 0.9:
            all_candidates[hcc_code] = {
                "hcc_code": hcc_code,
                "hcc_description": mapping.get("hcc_description", ""),
                "raf_weight": mapping.get("raf_weight", 0),
                "confidence": 0.9,
                "source": "llm",
                "supported_icds": [],
            }

        all_candidates[hcc_code]["supported_icds"].append({
            "icd10_code": icd10,
            "description": dx.get("description", ""),
            "hcc_code": hcc_code,
            "hcc_description": mapping.get("hcc_description", ""),
            "raf_weight": mapping.get("raf_weight", 0),
            "supporting_text": dx.get("supporting_text", ""),
            "date_of_service": dx.get("date_of_service"),
            "provider": dx.get("provider"),
            "source_section": dx.get("source_section"),
        })

    track_counts["llm"] = len(all_candidates)
    log.info("Track 1 (LLM): %d HCCs from %d active diagnoses", len(all_candidates), len(active_dx))

    # -----------------------------------------------------------------------
    # Track 2: TF-IDF Classifier
    # -----------------------------------------------------------------------
    if cfg.enable_tfidf and clinical_text:
        try:
            tfidf = TFIDFHCCClassifier(cfg)
            tfidf_preds = tfidf.predict(clinical_text, cfg.tfidf_threshold)
            new_from_tfidf = 0
            for pred in tfidf_preds:
                hcc = pred["hcc_code"]
                if hcc not in all_candidates:
                    all_candidates[hcc] = {
                        "hcc_code": hcc,
                        "hcc_description": HCC_DESCRIPTIONS.get(hcc, ""),
                        "raf_weight": 0,
                        "confidence": pred["confidence"],
                        "source": "tfidf",
                        "supported_icds": [],
                    }
                    new_from_tfidf += 1
                elif pred["confidence"] > all_candidates[hcc]["confidence"]:
                    all_candidates[hcc]["confidence"] = pred["confidence"]
                    all_candidates[hcc]["source"] = "tfidf"
            track_counts["tfidf"] = len(tfidf_preds)
            log.info("Track 2 (TF-IDF): %d predictions, %d new HCCs", len(tfidf_preds), new_from_tfidf)
        except Exception as e:
            log.warning("TF-IDF track failed: %s", e)

    # -----------------------------------------------------------------------
    # Track 3: Trained BioClinicalBERT
    # -----------------------------------------------------------------------
    if cfg.enable_bert and clinical_text:
        try:
            bert = BERTHCCPredictor(cfg)
            bert_preds = bert.predict(clinical_text, cfg.bert_threshold)
            new_from_bert = 0
            for pred in bert_preds:
                hcc = pred["hcc_code"]
                if hcc not in all_candidates:
                    all_candidates[hcc] = {
                        "hcc_code": hcc,
                        "hcc_description": HCC_DESCRIPTIONS.get(hcc, ""),
                        "raf_weight": 0,
                        "confidence": pred["confidence"],
                        "source": "trained_bert",
                        "supported_icds": [],
                    }
                    new_from_bert += 1
                elif pred["confidence"] > all_candidates[hcc]["confidence"]:
                    all_candidates[hcc]["confidence"] = pred["confidence"]
                    all_candidates[hcc]["source"] = "trained_bert"
            track_counts["bert"] = len(bert_preds)
            log.info("Track 3 (BERT): %d predictions, %d new HCCs", len(bert_preds), new_from_bert)
        except Exception as e:
            log.warning("BERT track failed: %s", e)

    # -----------------------------------------------------------------------
    # Track 4: LLM Verification
    # -----------------------------------------------------------------------
    verified_candidates: Dict[str, Dict[str, Any]] = {}
    unsupported_candidates: List[Dict[str, Any]] = []

    if cfg.enable_llm_verification and client and clinical_text:
        log.info("Track 4 (LLM Verification): verifying %d candidates...", len(all_candidates))
        for hcc_code, info in all_candidates.items():
            source = info.get("source", "")

            # Build evidence context
            if source == "llm" and info.get("supported_icds"):
                evidence_parts = []
                for icd in info["supported_icds"]:
                    evidence_parts.append(icd.get("supporting_text", ""))
                evidence = " ".join(evidence_parts) if any(evidence_parts) else clinical_text[:cfg.verification_text_limit]
            else:
                evidence = clinical_text[:cfg.verification_text_limit]

            result = verify_hcc_with_llm(client, model, hcc_code, evidence, cfg.llm_min_confidence)

            if result["is_verified"] and result["confidence"] >= cfg.llm_min_confidence:
                info["llm_verified"] = True
                info["llm_confidence"] = result["confidence"]
                info["llm_reasoning"] = result["reasoning"]
                verified_candidates[hcc_code] = info
                log.info("  [VERIFIED] %s (%.2f) — %s", hcc_code, result["confidence"], source)
            else:
                unsupported_candidates.append({
                    "hcc_code": hcc_code,
                    "hcc_description": info.get("hcc_description", ""),
                    "source": source,
                    "confidence": info.get("confidence", 0),
                    "llm_verified": False,
                    "llm_confidence": result.get("confidence", 0),
                    "reason": result.get("reasoning", "Not verified"),
                })
                log.info("  [REJECTED] %s (%.2f) — %s: %s",
                         hcc_code, result.get("confidence", 0), source, result.get("reasoning", ""))
    else:
        # No verification — pass through all LLM-sourced candidates
        for hcc_code, info in all_candidates.items():
            info["llm_verified"] = None  # Not verified
            info["llm_confidence"] = None
        verified_candidates = all_candidates

    # -----------------------------------------------------------------------
    # Apply V28 Hierarchy Suppression
    # -----------------------------------------------------------------------
    active_hccs = set(verified_candidates.keys())
    suppressed: Dict[str, str] = {}

    for group in hcc_mapper._hierarchy_groups:
        ordered = group.get("ordered_hccs", [])
        present = [h for h in ordered if h in active_hccs]
        if len(present) <= 1:
            continue
        winner = present[0]
        for loser in present[1:]:
            if loser not in suppressed:
                suppressed[loser] = winner

    # -----------------------------------------------------------------------
    # Build final payable and suppressed lists
    # -----------------------------------------------------------------------
    payable_hccs: List[Dict[str, Any]] = []
    suppressed_hccs: List[Dict[str, Any]] = []
    total_raf = 0.0

    for hcc_code, info in verified_candidates.items():
        entry = {
            "hcc_code": hcc_code,
            "hcc_description": info.get("hcc_description", ""),
            "raf_weight": info.get("raf_weight", 0),
            "confidence": info.get("confidence", 0),
            "source": info.get("source", "unknown"),
            "llm_verified": info.get("llm_verified"),
            "llm_confidence": info.get("llm_confidence"),
            "supported_icds": info.get("supported_icds", []),
            "icd_count": len(info.get("supported_icds", [])),
        }

        if hcc_code in suppressed:
            entry["suppressed_by"] = suppressed[hcc_code]
            suppressed_hccs.append(entry)
        else:
            entry["hierarchy_applied"] = hcc_code in {
                h for g in hcc_mapper._hierarchy_groups for h in g.get("ordered_hccs", [])
            }
            payable_hccs.append(entry)
            total_raf += entry["raf_weight"]

    elapsed = round(time.time() - start, 2)

    return {
        "payable_hccs": payable_hccs,
        "suppressed_hccs": suppressed_hccs,
        "unmapped_icds": unmapped_icds,
        "unsupported_candidates": unsupported_candidates,
        "raf_summary": {
            "total_raf_score": round(total_raf, 3),
            "hcc_raf": round(total_raf, 3),
            "demographic_raf": 0.0,
            "hcc_count": len(verified_candidates),
            "payable_hcc_count": len(payable_hccs),
            "suppressed_hcc_count": len(suppressed_hccs),
            "unmapped_icd_count": len(unmapped_icds),
        },
        "diagnosis_summary": {
            "total_diagnoses": len(diagnoses),
            "active_diagnoses": len(active_dx),
            "negated_diagnoses": negated_count,
        },
        "ensemble_metadata": {
            "ensemble_version": "v4",
            "tracks_enabled": {
                "llm": True,
                "tfidf": cfg.enable_tfidf,
                "bert": cfg.enable_bert,
                "llm_verification": cfg.enable_llm_verification,
            },
            "track_predictions": track_counts,
            "total_candidates": len(all_candidates),
            "verified_count": len(verified_candidates),
            "rejected_count": len(unsupported_candidates),
            "thresholds": {
                "tfidf": cfg.tfidf_threshold,
                "bert": cfg.bert_threshold,
                "llm_min_confidence": cfg.llm_min_confidence,
            },
            "processing_time_seconds": elapsed,
        },
    }
