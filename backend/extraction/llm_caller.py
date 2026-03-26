"""LLM calling for single-pass assertion extraction.

Handles OpenAI/Azure/Gemini calls with the MiniMax system prompt,
retry logic, JSON parsing, and optional image-based OCR fallback.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────

SYSTEM_PROMPT = r"""
You output ONLY valid JSON.

Task: Convert clinical chart text into AUDITABLE, ATOMIC clinical assertions for downstream ICD/HCC/ML and audit.

Rules:
1) ATOMICITY: one assertion = one fact. Split mixed facts, mixed polarity, mixed subject, mixed status, multiple findings, multiple diagnoses.
2) PROVENANCE: every assertion MUST include:
   - page_number
   - exact_quote: verbatim substring from the page text
   If exact_quote is not verbatim, do not output the item.
3) SUBJECT: patient | family_member | provider_plan | generic_education
4) STATUS: active | negated | historical | resolved | uncertain | family_history

   IMPORTANT STATUS RULES:
   - "PHQ-9 score = X" and "Fall risk low/no fall risk" are ACTIVE assessment results (not negated).
   - NKDA / "No known drug allergies" => allergy_none=true AND status must be "negated" (absence of allergies).
5) EVIDENCE_RANK:
   1 = Assessment/Diagnosis/Problem List/Plan/Orders/Lab Results
   2 = HPI/Chief Complaint/Physical Exam/Vitals/Meds/Allergies/Social/Family/Past history
   3 = ROS templates/boilerplate/patient education/health maintenance templates
6) ADMIN/BILLING QUARANTINE:
   Administrative artifacts are NOT diseases and NOT vitals.
   If the statement is primarily billing/admin/quality reporting, set category="administrative_code".
   Examples:
   - Encounter Z-codes (Z01.818, Z13.31, Z23, Z00.xx)
   - BMI bucket Z68.xx
   - Quality measure codes: ####F (e.g., 3074F, 3079F, 3008F), G#### (e.g., G8510, G9903)
   - Screening/procedure codes like 96127 → administrative_code or screening event, NOT diagnosis.
7) CODES MUST BE TYPED:
   NEVER put CPT/HCPCS/quality codes into ICD10.
   - ICD-10-CM: letter + 2–6 alphanumerics, optional decimal (I10, E03.9, N18.31, Z01.818)
   - CPT Category II: 4 digits + F (3074F)
   - HCPCS: letter + 4 digits (G8510)

Output schema:
{
  "assertions":[
    {
      "category":"chief_complaint|history_present_illness|review_of_systems|physical_exam|assessment|diagnosis|plan|medication|lab_result|lab_order|referral|procedure|screening|counseling|social_history|family_history|preventive_care|mental_health|symptom|vital_sign|allergy|imaging|administrative_code|functional_status|immunization|surgical_history",
      "concept":"short normalized concept (no codes)",
      "text":"clean atomic statement",
      "status":"active|negated|historical|resolved|uncertain|family_history",
      "subject":"patient|family_member|provider_plan|generic_education",
      "page_number":int,
      "exact_quote":"verbatim substring",
      "evidence_rank":1|2|3,
      "negation_trigger":string|null,
      "allergy_none":bool,
      "structured":{ "score_name":"PHQ-9|...", "score_value":number, "risk_level":"low|moderate|high" }
    }
  ]
}

Quality-measure BP lines like:
"MOST RECENT SYSTOLIC BLOOD PRESSURE LESS THAN 130 ... (3074F)"
must be category="administrative_code" (NOT vital_sign). Do NOT fabricate a measured BP from that line.

Return ONLY JSON.
""".strip()


# ── LLM call wrapper ──────────────────────────────────────────────

def call_llm(
    client: Any,
    model: str,
    chunk_text: str,
    max_retries: int = 3,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """Call the LLM with a text chunk and return parsed JSON assertions.

    Uses client.responses.create() (OpenAI Responses API).
    Falls back to client.chat.completions.create() if responses is unavailable.
    """
    last_err: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            result = _call_responses_api(client, model, chunk_text)
            if result is not None:
                return result
            result = _call_chat_api(client, model, chunk_text)
            if result is not None:
                return result
            raise RuntimeError("Both responses and chat APIs returned empty")
        except Exception as e:
            last_err = e
            wait = 2 ** (attempt - 1)
            log.warning(
                "LLM call failed (attempt %d/%d): %s; retrying in %ds",
                attempt, max_retries, repr(e), wait,
            )
            time.sleep(wait)

    raise RuntimeError(f"LLM call failed after {max_retries} retries") from last_err


def _call_responses_api(client: Any, model: str, chunk_text: str) -> Optional[Dict[str, Any]]:
    """Try the OpenAI Responses API (client.responses.create)."""
    try:
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": chunk_text},
            ],
            temperature=0,
        )
        out_text = (resp.output_text or "").strip()
        return _parse_json_response(out_text)
    except AttributeError:
        return None
    except Exception:
        raise


def _call_chat_api(client: Any, model: str, chunk_text: str) -> Optional[Dict[str, Any]]:
    """Fall back to the Chat Completions API."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": chunk_text},
            ],
            temperature=0,
        )
        out_text = (resp.choices[0].message.content or "").strip()
        return _parse_json_response(out_text)
    except AttributeError:
        return None
    except Exception:
        raise


def _parse_json_response(out_text: str) -> Dict[str, Any]:
    """Parse a JSON response, stripping markdown fences if needed."""
    try:
        return json.loads(out_text)
    except json.JSONDecodeError:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", out_text, flags=re.MULTILINE).strip()
        return json.loads(cleaned)


# ── Image-based OCR call ──────────────────────────────────────────

def call_llm_with_image(
    client: Any,
    model: str,
    image_bytes: bytes,
    page_number: int,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """Call the LLM with a page image for OCR-based assertion extraction.

    Encodes the image as base64 and sends via the vision-capable model.
    """
    import base64

    b64 = base64.b64encode(image_bytes).decode("ascii")
    last_err: Optional[Exception] = None

    user_content = [
        {
            "type": "text",
            "text": f"Extract clinical assertions from PAGE {page_number} of this medical chart image. "
                    f"Follow the same JSON schema as for text extraction.",
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        },
    ]

    for attempt in range(1, max_retries + 1):
        try:
            # Try responses API first
            try:
                resp = client.responses.create(
                    model=model,
                    input=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0,
                )
                out_text = (resp.output_text or "").strip()
                return _parse_json_response(out_text)
            except AttributeError:
                pass

            # Fall back to chat completions
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0,
            )
            out_text = (resp.choices[0].message.content or "").strip()
            return _parse_json_response(out_text)
        except Exception as e:
            last_err = e
            wait = 2 ** (attempt - 1)
            log.warning("Image LLM call failed (attempt %d/%d): %s", attempt, max_retries, repr(e))
            time.sleep(wait)

    raise RuntimeError(f"Image LLM call failed after {max_retries} retries") from last_err
