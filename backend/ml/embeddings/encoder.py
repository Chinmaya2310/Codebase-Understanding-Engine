"""
Shared embedding service singleton.

Both the analysis pipeline and the GNN training pipeline use the same
`EmbeddingService` instance so the underlying sentence-transformer model
is loaded only once per process.
"""
from __future__ import annotations

from backend.services.embedding_service import EmbeddingService

_shared: EmbeddingService | None = None


def get_shared_embedding_service() -> EmbeddingService:
    """Return the process-wide cached `EmbeddingService` instance."""
    global _shared
    if _shared is None:
        _shared = EmbeddingService()
    return _shared
