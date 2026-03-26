"""PDF page extraction and text chunking for LLM processing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

log = logging.getLogger(__name__)


@dataclass
class PageText:
    page_number: int
    text: str


def extract_pages(pdf_path: str) -> List[PageText]:
    """Extract text from each page of a PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    pages: List[PageText] = []
    for i in range(len(doc)):
        t = doc[i].get_text("text") or ""
        t = t.replace("\x00", "")
        pages.append(PageText(page_number=i + 1, text=t))
    doc.close()
    return pages


def pages_to_dict(pages: List[PageText]) -> Dict[int, str]:
    """Convert list of PageText to {page_number: text} dict."""
    return {p.page_number: p.text for p in pages}


def chunk_pages_by_chars(
    pages: List[PageText], max_chars: int = 9000
) -> List[Tuple[int, int]]:
    """Group consecutive pages into chunks that fit within max_chars.

    Returns list of (start_idx, end_idx) ranges into the pages list.
    """
    ranges: List[Tuple[int, int]] = []
    i = 0
    n = len(pages)
    while i < n:
        total = 0
        j = i
        while j < n and total + len(pages[j].text) <= max_chars:
            total += len(pages[j].text)
            j += 1
        if j == i:
            j = i + 1
        ranges.append((i, j))
        i = j
    return ranges


def build_chunk_payload(
    pages: List[PageText], start_idx: int, end_idx: int
) -> str:
    """Build the text payload for a single LLM chunk call.

    Wraps each page in === PAGE N START/END === markers.
    """
    parts = []
    for p in pages[start_idx:end_idx]:
        parts.append(
            f"\n\n=== PAGE {p.page_number} START ===\n"
            f"{p.text}\n"
            f"=== PAGE {p.page_number} END ===\n"
        )
    return "".join(parts).strip()


def extract_page_images(pdf_path: str) -> Dict[int, bytes]:
    """Render each page as a PNG image for OCR fallback.

    Returns {page_number: png_bytes}.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    images: Dict[int, bytes] = {}
    for i in range(len(doc)):
        page = doc[i]
        pix = page.get_pixmap(dpi=200)
        images[i + 1] = pix.tobytes("png")
    doc.close()
    return images
