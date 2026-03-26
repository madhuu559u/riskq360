"""Smart PDF text extraction with quality scoring and vision OCR fallback.

For each page:
  1. Extract text via PyMuPDF
  2. Score text quality (0-100)
  3. If quality < threshold: render as image, send to GPT-4o vision
  4. Merge all results

Ported and adapted from medinsights_platform/pipeline/smart_pdf.py.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

log = logging.getLogger(__name__)

VISION_SYSTEM_PROMPT = """You are a medical chart data extractor with OCR capabilities.
You are analyzing a PAGE IMAGE from a medical chart PDF.
This page may contain: handwritten notes, printed forms with handwritten
entries, medical tables, scanned documents, fax headers, signatures.

EXTRACT ALL TEXT AND DATA. Return JSON with:
- page_type: one of (handwritten_notes, printed_form, mixed, table, scanned, lab_report)
- confidence: one of (high, medium, low)
- extracted_text: all readable text in reading order
- structured_data: object with any of (patient_info, vitals, diagnoses, medications, lab_results, procedures, notes, signatures)
- handwriting_notes: text that appears handwritten
- table_data: tabular data formatted as readable text

Return ONLY valid JSON. No markdown fences."""


def score_text_quality(
    text: str,
    page_width: float = 0,
    page_height: float = 0,
    image_area_ratio: float = 0.0,
) -> int:
    """Score extracted text quality from 0-100.

    Factors: text length, character quality, word length, consonant clusters,
    line structure, text density, embedded image coverage.
    """
    if not text or not text.strip():
        return 0

    score = 100.0
    text_stripped = text.strip()
    length = len(text_stripped)

    if length < 20:
        return max(0, int(length * 1.5))
    if length < 50:
        score -= 30
    elif length < 100:
        score -= 15
    elif length < 200:
        score -= 5

    # Character quality
    normal_chars = sum(
        1 for c in text_stripped
        if c.isalnum() or c in ' \n\t.,;:!?()-/\'\"@#$%&*+=<>[]{}|\\~`_'
    )
    char_ratio = normal_chars / len(text_stripped)
    if char_ratio < 0.7:
        score -= 40
    elif char_ratio < 0.85:
        score -= 20
    elif char_ratio < 0.95:
        score -= 5

    # Average word length
    words = text_stripped.split()
    if words:
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len > 15:
            score -= 30
        elif avg_word_len > 10:
            score -= 15
        elif avg_word_len < 2:
            score -= 20

    # Consonant cluster detection
    consonant_pattern = re.compile(r'[bcdfghjklmnpqrstvwxyz]{5,}', re.IGNORECASE)
    clusters = consonant_pattern.findall(text_stripped)
    cluster_ratio = len(clusters) / max(len(words), 1) if words else 0
    if cluster_ratio > 0.1:
        score -= 25
    elif cluster_ratio > 0.05:
        score -= 10

    # Line structure
    lines = text_stripped.split('\n')
    non_empty_lines = [ln for ln in lines if ln.strip()]
    if non_empty_lines:
        avg_line_len = sum(len(ln) for ln in non_empty_lines) / len(non_empty_lines)
        if avg_line_len < 5 and len(non_empty_lines) > 5:
            score -= 20

    # Text density
    if page_width > 0 and page_height > 0:
        page_area = page_width * page_height
        if length / page_area < 0.001:
            score -= 15

    # Image coverage
    if image_area_ratio > 0.7:
        score -= 25
    elif image_area_ratio > 0.5:
        score -= 10

    return max(0, min(100, int(score)))


def _compute_image_area_ratio(page: Any) -> float:
    """Compute ratio of page area covered by images."""
    page_rect = page.rect
    page_area = page_rect.width * page_rect.height
    if page_area == 0:
        return 0.0
    image_area = 0.0
    for img in page.get_images(full=True):
        try:
            xref = img[0]
            for r in page.get_image_rects(xref):
                image_area += r.width * r.height
        except Exception:
            continue
    return min(image_area / page_area, 1.0)


def _render_page_as_base64(page: Any, dpi: int = 200) -> str:
    """Render a PDF page as a base64-encoded PNG."""
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")
    return base64.b64encode(png_bytes).decode("utf-8")


def _call_vision_api(
    client: Any,
    base64_image: str,
    vision_model: str = "gpt-4o",
) -> Dict[str, Any]:
    """Send a page image to a vision-capable model for OCR extraction."""
    response = client.chat.completions.create(
        model=vision_model,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text and structured data from this medical chart page image."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}", "detail": "high"}},
                ],
            },
        ],
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"extracted_text": raw, "parse_error": True}


def smart_extract_pdf(
    pdf_path: str,
    client: Any,
    vision_model: str = "gpt-4o",
    quality_threshold: int = 50,
) -> Tuple[str, List[Dict], Dict[int, Dict], Dict[str, Any]]:
    """Extract text from a PDF using smart text+vision strategy.

    Args:
        pdf_path: Path to the PDF file.
        client: OpenAI-compatible client instance.
        vision_model: Model name for vision OCR.
        quality_threshold: Quality score below which vision OCR is used.

    Returns:
        (full_text, pages_metadata, vision_results, stats)
    """
    doc = fitz.open(pdf_path)

    all_text_parts: List[str] = []
    pages_metadata: List[Dict] = []
    vision_results: Dict[int, Dict] = {}
    text_pages = 0
    vision_pages = 0
    total_chars = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        text_len = len(text.strip()) if text else 0
        image_ratio = _compute_image_area_ratio(page)

        score = score_text_quality(
            text,
            page_width=page.rect.width,
            page_height=page.rect.height,
            image_area_ratio=image_ratio,
        )

        page_meta: Dict[str, Any] = {
            "page_num": page_num + 1,
            "text_length": text_len,
            "quality_score": score,
            "image_area_ratio": round(image_ratio, 3),
            "method": "text",
        }

        if score < quality_threshold:
            page_meta["method"] = "vision"
            vision_pages += 1
            try:
                b64_image = _render_page_as_base64(page)
                vision_result = _call_vision_api(client, b64_image, vision_model)
                vision_results[page_num + 1] = vision_result

                vision_text = vision_result.get("extracted_text", "")
                page_text = f"\n--- PAGE {page_num + 1} [VISION EXTRACTED] ---\n"
                if text and text.strip():
                    page_text += f"[Original text (low quality, score={score})]:\n{text}\n"
                page_text += f"[Vision extracted text]:\n{vision_text}\n"
                all_text_parts.append(page_text)
                total_chars += len(vision_text)
            except Exception as e:
                page_meta["vision_error"] = str(e)
                page_meta["method"] = "text_fallback"
                log.warning("Vision OCR failed for page %d: %s", page_num + 1, e)
                if text and text.strip():
                    all_text_parts.append(f"\n--- PAGE {page_num + 1} [TEXT - vision failed] ---\n{text}")
                    total_chars += text_len
        else:
            text_pages += 1
            if text and text.strip():
                all_text_parts.append(f"\n--- PAGE {page_num + 1} [TEXT] ---\n{text}")
                total_chars += text_len

        pages_metadata.append(page_meta)

    doc.close()

    full_text = "\n".join(all_text_parts)
    stats = {
        "total_pages": len(pages_metadata),
        "text_pages": text_pages,
        "vision_pages": vision_pages,
        "total_chars": total_chars,
        "quality_threshold": quality_threshold,
        "vision_model": vision_model,
    }

    return full_text, pages_metadata, vision_results, stats


def basic_extract_pdf(pdf_path: str) -> Tuple[str, List[Dict], Dict[str, Any]]:
    """Simple text-only extraction (no vision).

    Returns:
        (full_text, pages_metadata, stats)
    """
    doc = fitz.open(pdf_path)
    parts: List[str] = []
    pages_metadata: List[Dict] = []
    total_chars = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        text_len = len(text.strip()) if text else 0
        score = score_text_quality(text, page.rect.width, page.rect.height)

        pages_metadata.append({
            "page_num": page_num + 1,
            "text_length": text_len,
            "quality_score": score,
            "method": "text",
        })

        if text and text.strip():
            parts.append(f"\n--- PAGE {page_num + 1} ---\n{text}")
            total_chars += text_len

    doc.close()

    full_text = "\n".join(parts)
    stats = {
        "total_pages": len(pages_metadata),
        "text_pages": len(pages_metadata),
        "vision_pages": 0,
        "total_chars": total_chars,
    }
    return full_text, pages_metadata, stats
