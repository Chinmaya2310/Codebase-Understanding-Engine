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

_TAINT_SYSTEM = (
    "You are an expert application-security engineer. "
    "You will be given source code of two functions from a real codebase — a *source* "
    "function (where untrusted input enters) and a *sink* function (where that input "
    "could cause harm). Explain in plain English: (1) why this is exploitable, "
    "(2) what kind of attack it enables, and (3) what a developer should do to fix it. "
    "Be concise, specific, and cite file/line numbers where relevant."
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

    async def explain_taint_finding(
        self,
        db: AsyncSession,
        repository_id: uuid.UUID,
        source_qn: str,
        sink_qn: str,
        vuln_class: str,
        confidence: str,
        path: list[str],
    ) -> str:
        """
        Generate a plain-English security explanation for a single taint finding.

        Fetches the source code of both the source function and the sink function
        from the CodeElement table, then asks the LLM to explain exploitability
        and how to fix it.  Does NOT store the result — callers cache if needed.
        """
        # Look up source code for source and sink functions
        async def _get_code(qn: str) -> CodeElement | None:
            stmt = (
                select(CodeElement)
                .where(
                    CodeElement.repository_id == repository_id,
                    CodeElement.qualified_name == qn,
                )
                .limit(1)
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

        src_el  = await _get_code(source_qn)
        sink_el = await _get_code(sink_qn)

        src_block = (
            f"**Source function** `{source_qn}`"
            + (f" ({src_el.file_path}:{src_el.start_line})" if src_el else "")
            + "\n```python\n"
            + ((src_el.source_code or "# source code not available")[:2000] if src_el else "# source code not available")
            + "\n```"
        )
        sink_block = (
            f"**Sink function** `{sink_qn}`"
            + (f" ({sink_el.file_path}:{sink_el.start_line})" if sink_el else "")
            + "\n```python\n"
            + ((sink_el.source_code or "# source code not available")[:2000] if sink_el else "# source code not available")
            + "\n```"
        )
        path_str = " → ".join(path) if path else f"{source_qn} → {sink_qn}"

        user_prompt = (
            f"## Vulnerability class: {vuln_class}  (confidence: {confidence})\n\n"
            f"## Call path\n{path_str}\n\n"
            f"## Code\n\n{src_block}\n\n{sink_block}\n\n"
            "Explain why this is a real security risk, what attack it enables, "
            "and how to fix it."
        )
        return await self.llm_service.generate(_TAINT_SYSTEM, user_prompt, max_tokens=700)
