"""PDF intake and processing — adapted from medinsights smartpdf.py.

Extracts text per page, scores quality, invokes GPT-4o Vision OCR for low-quality pages.
"""

from __future__ import annotations

import base64
import io
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from config.feature_flags import FeatureFlagRegistry
from config.settings import Settings
from core.exceptions import OCRError, PDFProcessingError
from ingestion.quality_scorer import QualityScorer

logger = structlog.get_logger(__name__)


class PageResult:
    """Result for a single extracted page."""

    def __init__(
        self,
        page_number: int,
        text: str,
        quality_score: float,
        extraction_method: str = "text",
        image_area_ratio: float = 0.0,
        vision_result: Dict[str, Any] | None = None,
    ) -> None:
        self.page_number = page_number
        self.text = text
        self.quality_score = quality_score
        self.extraction_method = extraction_method
        self.image_area_ratio = image_area_ratio
        self.vision_result = vision_result


class PDFProcessor:
    """Processes PDF files: text extraction + quality scoring + OCR fallback."""

    def __init__(self, settings: Settings, flags: FeatureFlagRegistry) -> None:
        self.settings = settings
        self.flags = flags
        self.quality_scorer = QualityScorer()
        self.quality_threshold = settings.pipeline.quality_threshold

    async def process(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract and process all pages from a PDF file.

        Returns dict with:
          - full_text: concatenated text from all pages
          - pages: list of per-page results
          - page_count: total pages
          - ocr_pages: count of pages that used OCR
          - quality_scores: per-page quality scores
        """
        import fitz  # PyMuPDF

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise PDFProcessingError(f"PDF file not found: {pdf_path}")

        logger.info("pdf.processing_start", path=str(pdf_path))
        start_time = time.time()

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            raise PDFProcessingError(f"Cannot open PDF: {e}")

        pages: List[PageResult] = []
        ocr_count = 0

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Extract text
            raw_text = page.get_text("text")
            text_length = len(raw_text.strip())

            # Calculate image area ratio
            image_area_ratio = self._get_image_area_ratio(page)

            # Score quality
            quality_score = self.quality_scorer.score(
                text=raw_text,
                image_area_ratio=image_area_ratio,
            )

            extraction_method = "text"
            vision_result = None

            # OCR fallback for low-quality pages
            if (
                quality_score < self.quality_threshold
                and self.flags.ocr_fallback
                and text_length < 50
            ):
                try:
                    vision_result = await self._call_vision_ocr(page, page_num + 1)
                    if vision_result and vision_result.get("extracted_text"):
                        raw_text = vision_result["extracted_text"]
                        extraction_method = "vision"
                        ocr_count += 1
                except OCRError as e:
                    logger.warning("pdf.ocr_failed", page=page_num + 1, error=str(e))
                    extraction_method = "text_fallback"

            pages.append(PageResult(
                page_number=page_num + 1,
                text=raw_text,
                quality_score=quality_score,
                extraction_method=extraction_method,
                image_area_ratio=image_area_ratio,
                vision_result=vision_result,
            ))

        doc.close()

        full_text = "\n\n".join(p.text for p in pages)
        elapsed = time.time() - start_time

        logger.info("pdf.processing_done", pages=len(pages), ocr_pages=ocr_count,
                     total_chars=len(full_text), seconds=round(elapsed, 2))

        return {
            "full_text": full_text,
            "pages": [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "text_length": len(p.text),
                    "quality_score": p.quality_score,
                    "extraction_method": p.extraction_method,
                    "image_area_ratio": p.image_area_ratio,
                    "vision_result": p.vision_result,
                }
                for p in pages
            ],
            "page_count": len(pages),
            "ocr_pages": ocr_count,
            "total_chars": len(full_text),
            "quality_scores": [p.quality_score for p in pages],
            "quality_avg": sum(p.quality_score for p in pages) / max(len(pages), 1),
            "file_size_bytes": pdf_path.stat().st_size,
            "processing_seconds": round(elapsed, 2),
        }

    def _get_image_area_ratio(self, page) -> float:
        """Calculate ratio of image area to page area."""
        try:
            page_rect = page.rect
            page_area = page_rect.width * page_rect.height
            if page_area == 0:
                return 0.0

            image_area = 0.0
            for img in page.get_images(full=True):
                try:
                    bbox = page.get_image_bbox(img)
                    if bbox:
                        image_area += bbox.width * bbox.height
                except Exception:
                    pass

            return min(image_area / page_area, 1.0)
        except Exception:
            return 0.0

    async def _call_vision_ocr(self, page, page_number: int) -> Dict[str, Any]:
        """Send a page image to GPT-4o Vision for OCR extraction."""
        from extraction.llm_client import UnifiedLLMClient

        try:
            # Render page as PNG
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            client = UnifiedLLMClient(self.settings.llm)
            result = await client.call_vision(
                image_b64=img_b64,
                prompt=(
                    "Extract ALL text from this medical chart page. "
                    "Return a JSON object with: page_type, confidence, extracted_text, "
                    "structured_data (any tables/forms as objects), handwriting_notes."
                ),
            )
            return result
        except Exception as e:
            raise OCRError(f"Vision OCR failed for page {page_number}: {e}")
