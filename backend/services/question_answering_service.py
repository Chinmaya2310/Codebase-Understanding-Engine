"""RAG question answering service."""
from __future__ import annotations
import logging, uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.code_element import CodeElement
from backend.services.embedding_service import EmbeddingService
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)

SYSTEM = (
    "You are an expert software engineer assistant. Answer the user's question about "
    "the codebase using ONLY the provided code context. Reference specific files and "
    "functions by name. If context is insufficient, say so clearly."
)


class QuestionAnsweringService:
    def __init__(self, embedding_service=None, llm_service=None) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.llm_service = llm_service or LLMService()

    async def answer(self, db: AsyncSession, repository_id: uuid.UUID, question: str, top_k: int = 8) -> dict:
        qv = self.embedding_service.embed_text(question)
        stmt = (select(CodeElement)
                .where(CodeElement.repository_id == repository_id)
                .where(CodeElement.embedding.isnot(None))
                .order_by(CodeElement.embedding.cosine_distance(qv))
                .limit(top_k))
        result = await db.execute(stmt)
        elements = list(result.scalars().all())
        if not elements:
            return {"answer": "No analyzed code found for this repository yet. Please wait for analysis to complete.", "sources": []}
        blocks = []
        sources = []
        for el in elements:
            block = f"### {el.qualified_name} ({el.element_type.value}) — {el.file_path}\n"
            if el.docstring: block += f"Docstring: {el.docstring}\n"
            if el.signature: block += f"Signature: {el.signature}\n"
            if el.source_code: block += f"```\n{el.source_code[:1500]}\n```\n"
            blocks.append(block)
            sources.append({"file_path": el.file_path, "qualified_name": el.qualified_name, "element_type": el.element_type.value})
        context = "\n\n".join(blocks)
        user_prompt = f"## Code context\n{context}\n\n## Question\n{question}\n\nAnswer concisely with file/function citations."
        answer_text = await self.llm_service.generate(SYSTEM, user_prompt, max_tokens=600)
        return {"answer": answer_text, "sources": sources}
