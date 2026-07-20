"""Diagram routes."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.schemas import DiagramResponse
from backend.db.database import get_db
from backend.models.analysis import AnalysisResult, AnalysisType

router = APIRouter(prefix="/api/repositories/{repository_id}", tags=["diagrams"])


@router.get("/diagrams", response_model=DiagramResponse)
async def get_diagrams(repository_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = (select(AnalysisResult)
            .where(AnalysisResult.repository_id == repository_id, AnalysisResult.analysis_type == AnalysisType.DIAGRAM)
            .order_by(AnalysisResult.created_at.desc()).limit(1))
    result = await db.execute(stmt)
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Diagrams not yet available")
    return a.result
