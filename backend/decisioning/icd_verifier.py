"""GPT-4o structured ICD + MEAT verification.

Adapted from ra-training-data-factory's llm_verifier.py.
Verifies candidate ICD codes against clinical text with MEAT validation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

import structlog

from extraction.llm_client import UnifiedLLMClient

logger = structlog.get_logger(__name__)


class ICDVerifier:
    """Verifies candidate ICD-10 codes using GPT-4o with structured JSON output."""

    def __init__(self, llm_client: UnifiedLLMClient) -> None:
        self.llm_client = llm_client
        self._cache: Dict[str, Dict] = {}
        self._prompt: str | None = None

    @property
    def system_prompt(self) -> str:
        if self._prompt is None:
            prompt_path = Path("config/prompts/icd_meat_verification.txt")
            if prompt_path.exists():
                self._prompt = prompt_path.read_text(encoding="utf-8")
            else:
                self._prompt = self._default_prompt()
        return self._prompt

    def _default_prompt(self) -> str:
        return (
            "You are a CMS-HCC risk adjustment auditor. Verify each candidate ICD-10 code "
            "against the clinical note text. Return JSON with verified_codes array."
        )

    async def verify_batch(
        self,
        note_text: str,
        candidates: List[Dict[str, Any]],
        threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Verify a batch of candidate ICD codes.

        Args:
            note_text: Full clinical note text.
            candidates: List of candidate ICD dicts with icd10_code, description, etc.
            threshold: Minimum confidence to include in results.

        Returns:
            Dict with verified_codes list.
        """
        if not candidates:
            return {"verified_codes": []}

        # Check cache
        cache_key = self._make_cache_key(note_text, candidates)
        if cache_key in self._cache:
            logger.info("verifier.cache_hit")
            return self._cache[cache_key]

        # Build candidate list for the prompt
        candidate_lines = []
        for c in candidates:
            code = c.get("icd10_code", "")
            desc = c.get("description", "")
            candidate_lines.append(f"- {code}: {desc}")

        user_prompt = (
            f"CLINICAL NOTE TEXT:\n\n{note_text}\n\n"
            f"---\n\n"
            f"CANDIDATE ICD-10 CODES TO VERIFY:\n\n"
            + "\n".join(candidate_lines)
            + "\n\nVerify each code against the note. Return the verified_codes JSON."
        )

        try:
            result = await self.llm_client.call(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                model="gpt-4o",
                json_mode=True,
            )

            # Ensure we have the expected structure
            if "verified_codes" not in result:
                # Try to wrap raw list
                if isinstance(result, list):
                    result = {"verified_codes": result}
                else:
                    result = {"verified_codes": []}

            # Filter by threshold
            result["verified_codes"] = [
                v for v in result.get("verified_codes", [])
                if v.get("confidence", 0) >= threshold or v.get("supported", False)
            ]

            # Cache the result
            self._cache[cache_key] = result

            logger.info("verifier.done",
                         total=len(candidates),
                         verified=len(result["verified_codes"]))
            return result

        except Exception as e:
            logger.error("verifier.failed", error=str(e))
            return {"verified_codes": [], "error": str(e)}

    def _make_cache_key(self, text: str, candidates: List[Dict]) -> str:
        """Create a deterministic cache key from note text and candidates."""
        codes = sorted(c.get("icd10_code", "") for c in candidates)
        content = text[:500] + "|" + ",".join(codes)
        return hashlib.sha256(content.encode()).hexdigest()
