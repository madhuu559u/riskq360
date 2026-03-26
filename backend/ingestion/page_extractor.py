"""Raw text extraction from PDF pages with page boundary preservation."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def extract_pages(pdf_path: Path) -> List[Dict]:
    """Extract raw text from each page of a PDF.

    Returns list of dicts: {page_number, text, text_length}.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))
    pages = []
    for i in range(len(doc)):
        text = doc[i].get_text("text")
        pages.append({
            "page_number": i + 1,
            "text": text,
            "text_length": len(text),
        })
    doc.close()
    return pages
