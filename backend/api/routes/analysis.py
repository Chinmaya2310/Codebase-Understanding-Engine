"""Analysis result routes."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.schemas import ArchitectureResponse, CodeElementResponse, DeadCodeResponse
from backend.db.database import get_db
from backend.models.analysis import AnalysisResult, AnalysisType
from backend.models.code_element import CodeElement

router = APIRouter(prefix="/api/repositories/{repository_id}", tags=["analysis"])


async def _get_analysis(db, repository_id, atype):
    stmt = (select(AnalysisResult)
            .where(AnalysisResult.repository_id == repository_id, AnalysisResult.analysis_type == atype)
            .order_by(AnalysisResult.created_at.desc()).limit(1))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.get("/architecture", response_model=ArchitectureResponse)
async def get_architecture(repository_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    a = await _get_analysis(db, repository_id, AnalysisType.ARCHITECTURE)
    if not a:
        raise HTTPException(status_code=404, detail="Architecture analysis not yet available")
    return a.result


@router.get("/dead-code", response_model=DeadCodeResponse)
async def get_dead_code(repository_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    a = await _get_analysis(db, repository_id, AnalysisType.DEAD_CODE)
    if not a:
        raise HTTPException(status_code=404, detail="Dead code analysis not yet available")
    return a.result


@router.get("/elements", response_model=list[CodeElementResponse])
async def list_elements(repository_id: uuid.UUID,
                         element_type: str | None = Query(default=None),
                         dead_code_only: bool = Query(default=False),
                         limit: int = Query(default=100, ge=1, le=1000),
                         offset: int = Query(default=0, ge=0),
                         db: AsyncSession = Depends(get_db)):
    stmt = select(CodeElement).where(CodeElement.repository_id == repository_id)
    if element_type:
        stmt = stmt.where(CodeElement.element_type == element_type)
    if dead_code_only:
        stmt = stmt.where(CodeElement.is_dead_code.is_(True))
    stmt = stmt.order_by(CodeElement.file_path, CodeElement.start_line).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
