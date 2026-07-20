"""Pydantic request/response schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl
from backend.models.repository import RepositoryStatus


class RepositoryCreateRequest(BaseModel):
    url: HttpUrl
    branch: Optional[str] = None


class RepositoryResponse(BaseModel):
    id: uuid.UUID
    url: str
    owner: str
    name: str
    status: RepositoryStatus
    progress: float
    error_message: Optional[str] = None
    total_files: int
    total_lines: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=20)


class QuestionResponse(BaseModel):
    answer: str
    sources: list[dict]


class CodeElementResponse(BaseModel):
    id: uuid.UUID
    element_type: str
    name: str
    qualified_name: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    is_dead_code: bool
    class Config:
        from_attributes = True


class DeadCodeResponse(BaseModel):
    findings: list[dict]


class ArchitectureResponse(BaseModel):
    pattern: str
    layers: dict[str, list[str]]
    microservices_detected: list[str]
    confidence: float


class DiagramResponse(BaseModel):
    dependency_diagram: str
    architecture_diagram: str
    code_graph: dict
