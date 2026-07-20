"""
Embedding service — Windows-safe batched encoding.

The root cause of WinError 10055 during embedding is trying to persist
thousands of large vector objects in a single database flush.  We now:

  1. Encode in small CPU batches (16 items) to keep memory low.
  2. Return plain Python lists so SQLAlchemy never holds large tensors.
  3. Provide a ``batch_generator`` helper used by the pipeline to
     persist embeddings in chunks rather than all at once.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Generator

from sentence_transformers import SentenceTransformer

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Smaller batch size reduces peak memory and avoids socket-buffer
# exhaustion on Windows when flushing many rows at once.
_DEFAULT_BATCH = 16


@lru_cache()
def _load_model() -> SentenceTransformer:
    logger.info("Loading embedding model: %s", settings.embedding_model_name)
    model = SentenceTransformer(settings.embedding_model_name)
    return model


class EmbeddingService:
    """Generates 384-dim text embeddings for code elements."""

    def __init__(self) -> None:
        self._model = _load_model()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed_text(self, text: str) -> list[float]:
        """Embed a single string.  Returns a plain Python list."""
        if not text or not text.strip():
            return [0.0] * settings.embedding_dimension
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = _DEFAULT_BATCH,
    ) -> list[list[float]]:
        """
        Embed a list of strings in small batches.

        Returns a list of plain Python float lists — never tensors —
        so they are safe to pass directly to SQLAlchemy / pgvector.
        """
        if not texts:
            return []

        cleaned = [t.strip() if t and t.strip() else " " for t in texts]
        results: list[list[float]] = []

        for start in range(0, len(cleaned), batch_size):
            chunk = cleaned[start : start + batch_size]
            vecs = self._model.encode(
                chunk,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            results.extend(v.tolist() for v in vecs)

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_embedding_text(
        name: str,
        element_type: str,
        signature: str | None,
        docstring: str | None,
        source_code: str | None,
    ) -> str:
        """Build a short text blob summarising a code element for embedding."""
        parts = [f"{element_type}: {name}"]
        if signature:
            parts.append(signature)
        if docstring:
            parts.append(docstring[:300])
        if source_code:
            parts.append(source_code[:600])   # keep short to avoid OOM
        return "\n".join(parts)

    @staticmethod
    def chunk_list(
        items: list,
        chunk_size: int,
    ) -> Generator[list, None, None]:
        """Yield successive ``chunk_size``-length slices of *items*."""
        for i in range(0, len(items), chunk_size):
            yield items[i : i + chunk_size]
