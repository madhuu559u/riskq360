"""Coding Helper endpoint — AJAX-like ICD-10 code suggestions for coders."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from services.coding_helper_service import CodingHelperService

router = APIRouter()

_svc = CodingHelperService()


@router.get("/suggest")
async def suggest_codes(
    q: str = Query(..., min_length=1, description="Search query (description text or ICD code prefix)"),
    limit: int = Query(20, ge=1, le=50),
    payment_only: bool = Query(False),
) -> dict:
    """Return ICD-10 code suggestions for a text query using BM25 ranking.

    Used by the frontend coding helper popup when a coder selects text or
    types a description.
    """
    results = _svc.suggest(query=q, limit=limit, payment_only=payment_only)
    return {
        "query": q,
        "results": results,
        "count": len(results),
        "index_size": _svc.get_entry_count(),
    }
