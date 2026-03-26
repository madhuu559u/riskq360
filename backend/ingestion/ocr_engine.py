"""GPT-4o Vision OCR engine for low-quality PDF pages."""

from __future__ import annotations

from typing import Any, Dict


async def extract_via_vision(
    image_b64: str,
    llm_client: Any,
    page_number: int = 0,
) -> Dict[str, Any]:
    """Send a page image to GPT-4o Vision API and extract structured text.

    Args:
        image_b64: Base64-encoded PNG image.
        llm_client: UnifiedLLMClient instance.
        page_number: Page number for logging.

    Returns:
        Dict with extracted_text, page_type, confidence, structured_data.
    """
    result = await llm_client.call_vision(
        image_b64=image_b64,
        prompt=(
            "Extract ALL text from this medical chart page. "
            "Return a JSON object with: "
            "page_type (e.g., progress_note, lab_report, cover_sheet), "
            "confidence (0.0-1.0), "
            "extracted_text (full text content), "
            "structured_data (any tables/forms as structured objects), "
            "handwriting_notes (any handwritten text found)."
        ),
    )
    return result
