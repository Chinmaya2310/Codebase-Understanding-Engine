import enum, uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.database import Base


class EdgeType(str, enum.Enum):
    IMPORTS = "imports"; CALLS = "calls"; INHERITS = "inherits"
    IMPLEMENTS = "implements"; CONTAINS = "contains"; REFERENCES = "references"


class GraphNode(Base):
    __tablename__ = "graph_nodes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"))
    code_element_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("code_elements.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    node_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    repository: Mapped["Repository"] = relationship("Repository", back_populates="graph_nodes")
    outgoing_edges: Mapped[list["GraphEdge"]] = relationship("GraphEdge", foreign_keys="GraphEdge.source_id", back_populates="source", cascade="all, delete-orphan")
    incoming_edges: Mapped[list["GraphEdge"]] = relationship("GraphEdge", foreign_keys="GraphEdge.target_id", back_populates="target", cascade="all, delete-orphan")


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"))
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"))
    edge_type: Mapped[EdgeType] = mapped_column(Enum(EdgeType), nullable=False)
    source: Mapped["GraphNode"] = relationship("GraphNode", foreign_keys=[source_id], back_populates="outgoing_edges")
    target: Mapped["GraphNode"] = relationship("GraphNode", foreign_keys=[target_id], back_populates="incoming_edges")
