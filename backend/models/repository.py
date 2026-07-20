import enum, uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.database import Base


class RepositoryStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    BUILDING_GRAPH = "building_graph"
    EMBEDDING = "embedding"
    ANALYZING = "analyzing"
    READY = "ready"
    FAILED = "failed"


class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    local_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[RepositoryStatus] = mapped_column(Enum(RepositoryStatus), default=RepositoryStatus.PENDING)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    total_lines: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    code_elements: Mapped[list["CodeElement"]] = relationship("CodeElement", back_populates="repository", cascade="all, delete-orphan")
    graph_nodes: Mapped[list["GraphNode"]] = relationship("GraphNode", back_populates="repository", cascade="all, delete-orphan")
    analyses: Mapped[list["AnalysisResult"]] = relationship("AnalysisResult", back_populates="repository", cascade="all, delete-orphan")
