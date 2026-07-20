import enum, uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.database import Base


class AnalysisType(str, enum.Enum):
    ARCHITECTURE = "architecture"; DEPENDENCIES = "dependencies"
    DEAD_CODE = "dead_code"; QA = "qa"; DIAGRAM = "diagram"


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"))
    analysis_type: Mapped[AnalysisType] = mapped_column(Enum(AnalysisType), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    repository: Mapped["Repository"] = relationship("Repository", back_populates="analyses")
