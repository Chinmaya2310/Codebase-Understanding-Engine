"""Repository CRUD routes."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.schemas import RepositoryCreateRequest, RepositoryResponse
from backend.core.security import get_current_user, rate_limit_dependency
from backend.db.database import get_db
from backend.models.repository import Repository, RepositoryStatus
from backend.services.analysis_pipeline import run_analysis_pipeline
from backend.services.repository_service import RepositoryIngestionError, parse_github_url

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryResponse, status_code=201, dependencies=[Depends(rate_limit_dependency)])
async def create_repository(payload: RepositoryCreateRequest, background_tasks: BackgroundTasks,
                             db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    try:
        owner, name = parse_github_url(str(payload.url))
    except RepositoryIngestionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    repo = Repository(url=str(payload.url), owner=owner, name=name,
                      default_branch=payload.branch or "main", status=RepositoryStatus.PENDING)
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    background_tasks.add_task(run_analysis_pipeline, repo.id)
    return repo


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Repository).order_by(Repository.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(repository_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.delete("/{repository_id}", status_code=204)
async def delete_repository(repository_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.local_path:
        from backend.services.repository_service import RepositoryService
        RepositoryService().cleanup(repo.local_path)
    await db.delete(repo)
    await db.commit()


@router.post("/{repository_id}/reanalyze", response_model=RepositoryResponse, dependencies=[Depends(rate_limit_dependency)])
async def reanalyze(repository_id: uuid.UUID, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    repo.status = RepositoryStatus.PENDING
    repo.progress = 0.0
    repo.error_message = None
    await db.commit()
    background_tasks.add_task(run_analysis_pipeline, repo.id)
    return repo
