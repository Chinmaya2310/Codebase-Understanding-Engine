"""Q&A route."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.schemas import QuestionRequest, QuestionResponse
from backend.core.security import rate_limit_dependency
from backend.db.database import get_db
from backend.models.repository import Repository, RepositoryStatus
from backend.services.llm_service import LLMServiceError
from backend.services.question_answering_service import QuestionAnsweringService

router = APIRouter(prefix="/api/repositories/{repository_id}", tags=["questions"])
_qa = QuestionAnsweringService()


@router.post("/ask", response_model=QuestionResponse, dependencies=[Depends(rate_limit_dependency)])
async def ask(repository_id: uuid.UUID, payload: QuestionRequest, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.status != RepositoryStatus.READY:
        raise HTTPException(status_code=409, detail=f"Repository not ready (status: {repo.status.value})")
    try:
        return await _qa.answer(db, repository_id, payload.question, top_k=payload.top_k)
    except LLMServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))
