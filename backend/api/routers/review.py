"""Review workflow endpoints — CRUD for diagnoses, HCCs, HEDIS measures.

Abstractors/coders can accept, reject, add, update, and delete clinical data
with full audit trail and comments.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from services.review_service import ReviewService

router = APIRouter()


# =========================================================================
# REQUEST MODELS
# =========================================================================

class ReviewRequest(BaseModel):
    reviewer: str
    notes: Optional[str] = None


class AcceptDiagnosisRequest(ReviewRequest):
    date_of_service: Optional[str] = None


class AddDiagnosisRequest(BaseModel):
    chart_id: int
    icd10_code: str
    description: str
    reviewer: str
    notes: Optional[str] = None
    date_of_service: Optional[str] = None
    page_number: Optional[int] = None
    exact_quote: Optional[str] = None
    hcc_code: Optional[str] = None
    status: str = "active"


class UpdateDiagnosisRequest(BaseModel):
    reviewer: str
    icd10_code: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    date_of_service: Optional[str] = None
    status: Optional[str] = None


class AddHCCRequest(BaseModel):
    chart_id: int
    hcc_code: str
    hcc_description: str
    raf_weight: float
    reviewer: str
    notes: Optional[str] = None
    supported_icds: Optional[list[dict]] = None
    measurement_year: Optional[int] = None


class AddHEDISRequest(BaseModel):
    chart_id: int
    measure_id: str
    measure_name: str
    status: str  # met | gap | not_applicable | excluded
    reviewer: str
    notes: Optional[str] = None
    evidence: Optional[list[dict]] = None
    measurement_year: Optional[int] = None


class UpdateHEDISRequest(BaseModel):
    reviewer: str
    status: Optional[str] = None
    evidence: Optional[list[dict]] = None
    notes: Optional[str] = None


class SaveDocumentRequest(BaseModel):
    reviewer: str
    comments: Optional[str] = None


# =========================================================================
# DIAGNOSIS ENDPOINTS
# =========================================================================

@router.post("/diagnosis")
async def add_diagnosis(
    request: AddDiagnosisRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a new diagnosis (coder-added ICD code)."""
    svc = ReviewService(db)
    result = await svc.add_diagnosis(
        chart_id=request.chart_id,
        icd10_code=request.icd10_code,
        description=request.description,
        reviewer=request.reviewer,
        notes=request.notes,
        date_of_service=request.date_of_service,
        page_number=request.page_number,
        exact_quote=request.exact_quote,
        hcc_code=request.hcc_code,
        status=request.status,
    )
    await db.commit()
    return result


@router.put("/diagnosis/{assertion_id}/accept")
async def accept_diagnosis(
    assertion_id: int,
    request: AcceptDiagnosisRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept a diagnosis assertion with optional comments."""
    svc = ReviewService(db)
    result = await svc.accept_diagnosis(
        assertion_id, request.reviewer, request.notes, request.date_of_service,
    )
    if not result:
        raise HTTPException(404, f"Assertion not found: {assertion_id}")
    await db.commit()
    return result


@router.put("/diagnosis/{assertion_id}/reject")
async def reject_diagnosis(
    assertion_id: int,
    request: ReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reject a diagnosis assertion with comments."""
    svc = ReviewService(db)
    result = await svc.reject_diagnosis(assertion_id, request.reviewer, request.notes)
    if not result:
        raise HTTPException(404, f"Assertion not found: {assertion_id}")
    await db.commit()
    return result


@router.put("/diagnosis/{assertion_id}")
async def update_diagnosis(
    assertion_id: int,
    request: UpdateDiagnosisRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a diagnosis (edit ICD code, description, DOS, status)."""
    svc = ReviewService(db)
    result = await svc.update_diagnosis(
        assertion_id, request.reviewer,
        icd10_code=request.icd10_code,
        description=request.description,
        notes=request.notes,
        date_of_service=request.date_of_service,
        status=request.status,
    )
    if not result:
        raise HTTPException(404, f"Assertion not found: {assertion_id}")
    await db.commit()
    return result


@router.delete("/diagnosis/{assertion_id}")
async def delete_diagnosis(
    assertion_id: int,
    reviewer: str = Query(...),
    notes: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Delete (reject) a diagnosis with reason."""
    svc = ReviewService(db)
    deleted = await svc.delete_diagnosis(assertion_id, reviewer, notes)
    if not deleted:
        raise HTTPException(404, f"Assertion not found: {assertion_id}")
    await db.commit()
    return {"status": "deleted", "assertion_id": assertion_id}


# =========================================================================
# HCC ENDPOINTS
# =========================================================================

@router.post("/hcc")
async def add_hcc(
    request: AddHCCRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a new payable HCC (coder-added)."""
    svc = ReviewService(db)
    result = await svc.add_hcc(
        chart_id=request.chart_id,
        hcc_code=request.hcc_code,
        hcc_description=request.hcc_description,
        raf_weight=request.raf_weight,
        reviewer=request.reviewer,
        notes=request.notes,
        supported_icds=request.supported_icds,
        measurement_year=request.measurement_year,
    )
    await db.commit()
    return result


@router.put("/hcc/{hcc_id}/accept")
async def accept_hcc(
    hcc_id: int,
    request: ReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept a payable HCC with comments."""
    svc = ReviewService(db)
    result = await svc.accept_hcc(hcc_id, request.reviewer, request.notes)
    if not result:
        raise HTTPException(404, f"HCC not found: {hcc_id}")
    await db.commit()
    return result


@router.put("/hcc/{hcc_id}/reject")
async def reject_hcc(
    hcc_id: int,
    request: ReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reject a payable HCC (moves to suppressed)."""
    svc = ReviewService(db)
    deleted = await svc.reject_hcc(hcc_id, request.reviewer, request.notes)
    if not deleted:
        raise HTTPException(404, f"HCC not found: {hcc_id}")
    await db.commit()
    return {"status": "rejected", "hcc_id": hcc_id}


# =========================================================================
# HEDIS ENDPOINTS
# =========================================================================

@router.post("/hedis")
async def add_hedis(
    request: AddHEDISRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a new HEDIS measure result (coder-added)."""
    svc = ReviewService(db)
    result = await svc.add_hedis(
        chart_id=request.chart_id,
        measure_id=request.measure_id,
        measure_name=request.measure_name,
        status=request.status,
        reviewer=request.reviewer,
        notes=request.notes,
        evidence=request.evidence,
        measurement_year=request.measurement_year,
    )
    await db.commit()
    return result


@router.put("/hedis/{hedis_id}/accept")
async def accept_hedis(
    hedis_id: int,
    request: ReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept a HEDIS measure result."""
    svc = ReviewService(db)
    result = await svc.accept_hedis(hedis_id, request.reviewer, request.notes)
    if not result:
        raise HTTPException(404, f"HEDIS result not found: {hedis_id}")
    await db.commit()
    return result


@router.put("/hedis/{hedis_id}/reject")
async def reject_hedis(
    hedis_id: int,
    request: ReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reject a HEDIS measure result."""
    svc = ReviewService(db)
    deleted = await svc.reject_hedis(hedis_id, request.reviewer, request.notes)
    if not deleted:
        raise HTTPException(404, f"HEDIS result not found: {hedis_id}")
    await db.commit()
    return {"status": "rejected", "hedis_id": hedis_id}


@router.put("/hedis/{hedis_id}")
async def update_hedis(
    hedis_id: int,
    request: UpdateHEDISRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a HEDIS measure result."""
    svc = ReviewService(db)
    result = await svc.update_hedis(
        hedis_id, request.reviewer,
        status=request.status,
        evidence=request.evidence,
        notes=request.notes,
    )
    if not result:
        raise HTTPException(404, f"HEDIS result not found: {hedis_id}")
    await db.commit()
    return result


# =========================================================================
# DOCUMENT SAVE & REVIEW SUMMARY
# =========================================================================

@router.post("/save-document/{chart_id}")
async def save_document(
    chart_id: int,
    request: SaveDocumentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save all reviewed data for a chart as a structured document with comments."""
    svc = ReviewService(db)
    result = await svc.save_document(chart_id, request.reviewer, request.comments)
    await db.commit()
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/summary/{chart_id}")
async def get_review_summary(
    chart_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get summary of all review actions for a chart."""
    svc = ReviewService(db)
    return await svc.get_review_summary(chart_id)
