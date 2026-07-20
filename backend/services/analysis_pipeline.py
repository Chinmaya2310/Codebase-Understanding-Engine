"""
Main analysis pipeline orchestrator — Windows-safe chunked persistence.

Key Windows fixes applied here:
  - Embeddings are persisted in small chunks (CHUNK_SIZE = 50) rather
    than a single giant flush, preventing WinError 10055.
  - Each chunk is committed and the session is flushed before moving on,
    keeping the SQLAlchemy connection pool pressure low.
  - Graph persistence is also chunked for the same reason.
"""
from __future__ import annotations

import logging
import uuid

from backend.db.database import AsyncSessionLocal
from backend.models.analysis import AnalysisResult, AnalysisType
from backend.models.code_element import CodeElement, CodeElementType
from backend.models.repository import Repository, RepositoryStatus
from backend.services.dead_code_service import DeadCodeService
from backend.services.diagram_service import DiagramService
from backend.services.embedding_service import EmbeddingService
from backend.services.graph_service import GraphService
from backend.services.parser_service import ParserService
from backend.services.repository_service import (
    RepositoryIngestionError,
    RepositoryService,
    parse_github_url,
)

logger = logging.getLogger(__name__)

# Number of code elements persisted + embedded per database transaction.
# Smaller values use less socket/memory on Windows.
CHUNK_SIZE = 50

_ETYPE = {
    "module":    CodeElementType.MODULE,
    "class":     CodeElementType.CLASS,
    "function":  CodeElementType.FUNCTION,
    "method":    CodeElementType.METHOD,
    "variable":  CodeElementType.VARIABLE,
    "import":    CodeElementType.IMPORT,
    "interface": CodeElementType.INTERFACE,
    "struct":    CodeElementType.STRUCT,
}


async def _set_status(
    db,
    repo: Repository,
    status: RepositoryStatus,
    progress: float,
    error: str | None = None,
) -> None:
    repo.status = status
    repo.progress = progress
    if error:
        repo.error_message = error
    db.add(repo)
    await db.commit()


async def run_analysis_pipeline(repository_id: uuid.UUID) -> None:
    """
    Full ingestion + analysis pipeline.  Runs as a FastAPI BackgroundTask.
    All exceptions are caught so they never crash the server process.
    """
    async with AsyncSessionLocal() as db:
        repo = await db.get(Repository, repository_id)
        if repo is None:
            logger.error("Repository %s not found", repository_id)
            return

        try:
            # ── 1. Clone ──────────────────────────────────────────────
            await _set_status(db, repo, RepositoryStatus.CLONING, 0.05)
            svc = RepositoryService()
            local_path = svc.clone(repo.url, str(repo.id))
            repo.local_path = local_path
            await db.commit()
            logger.info("Cloned to %s", local_path)

            # ── 2. Parse ──────────────────────────────────────────────
            await _set_status(db, repo, RepositoryStatus.PARSING, 0.20)
            files = svc.enumerate_source_files(local_path)
            parser = ParserService()
            parse_results = parser.parse_files(files)
            stats = parser.summarize(parse_results)
            repo.total_files = stats["total_files"]
            repo.total_lines = stats["total_lines"]
            await db.commit()
            logger.info(
                "Parsed %d files / %d lines / %d elements",
                stats["total_files"], stats["total_lines"], stats["total_elements"],
            )

            # ── 3. Build graph ────────────────────────────────────────
            await _set_status(db, repo, RepositoryStatus.BUILDING_GRAPH, 0.45)
            graph_svc = GraphService()
            graph = graph_svc.build_graph(parse_results)
            logger.info(
                "Graph: %d nodes / %d edges",
                graph.number_of_nodes(), graph.number_of_edges(),
            )

            # ── 4. Embed + persist code elements in chunks ────────────
            await _set_status(db, repo, RepositoryStatus.EMBEDDING, 0.55)
            emb_svc = EmbeddingService()

            # Collect all candidate nodes first
            all_nodes = [
                (qn, data)
                for qn, data in graph.nodes(data=True)
                if data.get("node_type") in _ETYPE
            ]

            # Build embedding texts
            texts = [
                emb_svc.build_embedding_text(
                    name=data.get("label", qn),
                    element_type=data.get("node_type", "unknown"),
                    signature=data.get("signature"),
                    docstring=data.get("docstring"),
                    source_code=data.get("source_code"),
                )
                for qn, data in all_nodes
            ]

            # Encode ALL embeddings up-front (CPU-only, no DB involvement)
            logger.info("Encoding %d embeddings…", len(texts))
            all_vectors = emb_svc.embed_batch(texts, batch_size=16)
            logger.info("Encoding complete")

            # Persist in small chunks to avoid WinError 10055
            qn_to_id: dict[str, uuid.UUID] = {}
            total = len(all_nodes)

            for chunk_start in range(0, total, CHUNK_SIZE):
                chunk_nodes = all_nodes[chunk_start : chunk_start + CHUNK_SIZE]
                chunk_vecs  = all_vectors[chunk_start : chunk_start + CHUNK_SIZE]

                chunk_elements: list[CodeElement] = []
                for (qn, data), vec in zip(chunk_nodes, chunk_vecs):
                    el = CodeElement(
                        repository_id=repo.id,
                        element_type=_ETYPE[data["node_type"]],
                        name=data.get("label", qn),
                        qualified_name=qn,
                        file_path=data.get("file_path", ""),
                        language=data.get("language", "unknown"),
                        start_line=data.get("start_line", 0),
                        end_line=data.get("end_line", 0),
                        source_code=data.get("source_code"),
                        docstring=data.get("docstring"),
                        signature=data.get("signature"),
                        embedding=vec,
                    )
                    chunk_elements.append(el)
                    db.add(el)

                await db.flush()

                for el in chunk_elements:
                    qn_to_id[el.qualified_name] = el.id

                await db.commit()

                pct = 0.55 + 0.10 * (chunk_start + len(chunk_nodes)) / max(total, 1)
                repo.progress = min(pct, 0.65)
                db.add(repo)
                await db.commit()

                logger.info(
                    "Embedded %d/%d elements",
                    chunk_start + len(chunk_nodes), total,
                )

            # ── 5. Persist graph structure ────────────────────────────
            await _set_status(db, repo, RepositoryStatus.EMBEDDING, 0.70)
            await graph_svc.persist_graph(db, repo.id, graph, qn_to_id)

            # ── 6. Run analyses ───────────────────────────────────────
            await _set_status(db, repo, RepositoryStatus.ANALYZING, 0.85)

            diag_svc = DiagramService()
            arch       = diag_svc.detect_architecture(graph)
            dep_diag   = diag_svc.generate_dependency_diagram(graph)
            arch_diag  = diag_svc.generate_architecture_diagram(graph, arch["layers"])
            graph_json = diag_svc.generate_code_graph_json(graph)

            dead_svc  = DeadCodeService()
            dead      = dead_svc.find_dead_code(graph)

            # Mark dead-code elements
            dead_qns = {f["qualified_name"] for f in dead}
            if dead_qns:
                for qn, el_id in qn_to_id.items():
                    if qn in dead_qns:
                        el = await db.get(CodeElement, el_id)
                        if el:
                            el.is_dead_code = True
                            db.add(el)
                await db.commit()

            db.add(AnalysisResult(
                repository_id=repo.id,
                analysis_type=AnalysisType.ARCHITECTURE,
                result=arch,
            ))
            db.add(AnalysisResult(
                repository_id=repo.id,
                analysis_type=AnalysisType.DIAGRAM,
                result={
                    "dependency_diagram":  dep_diag,
                    "architecture_diagram": arch_diag,
                    "code_graph":          graph_json,
                },
            ))
            db.add(AnalysisResult(
                repository_id=repo.id,
                analysis_type=AnalysisType.DEAD_CODE,
                result={"findings": dead},
            ))

            await _set_status(db, repo, RepositoryStatus.READY, 1.0)
            logger.info("Pipeline complete for repo %s", repository_id)

        except RepositoryIngestionError as exc:
            logger.error("Ingestion error: %s", exc)
            await _set_status(db, repo, RepositoryStatus.FAILED, repo.progress, str(exc))

        except Exception as exc:
            logger.exception("Pipeline failed for repo %s", repository_id)
            await _set_status(db, repo, RepositoryStatus.FAILED, repo.progress, str(exc))
