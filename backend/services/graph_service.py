"""
Graph construction and persistence — Windows-safe chunked DB writes.

Builds a NetworkX MultiDiGraph from parsed code elements, then persists
GraphNode and GraphEdge rows in small chunks to avoid WinError 10055
(Windows socket buffer exhaustion) that occurs when flushing thousands
of rows in one transaction.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict

import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.code_element import CodeElement, CodeElementType
from backend.models.graph_node import EdgeType, GraphEdge, GraphNode
from backend.parsers.base_parser import ParseResult

logger = logging.getLogger(__name__)

# Rows committed per chunk during graph persistence
_PERSIST_CHUNK = 100

_ETYPE_MAP = {
    "module":    CodeElementType.MODULE,
    "class":     CodeElementType.CLASS,
    "function":  CodeElementType.FUNCTION,
    "method":    CodeElementType.METHOD,
    "variable":  CodeElementType.VARIABLE,
    "import":    CodeElementType.IMPORT,
    "interface": CodeElementType.INTERFACE,
    "struct":    CodeElementType.STRUCT,
}


class GraphService:
    """Builds and analyses the code knowledge graph for a repository."""

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build_graph(self, parse_results: list[ParseResult]) -> nx.MultiDiGraph:
        """
        Construct a directed multigraph from ParseResult objects.

        Nodes  — modules, classes, functions, methods, structs, interfaces.
        Edges  — CONTAINS (structural), CALLS (resolved by name), IMPORTS.
        """
        graph = nx.MultiDiGraph()
        name_to_qns: dict[str, list[str]] = defaultdict(list)
        pending_calls:   list[tuple[str, str]] = []
        pending_imports: list[tuple[str, str]] = []

        for result in parse_results:
            if result.error:
                continue
            for el in result.elements:
                if el.element_type == "call":
                    if el.parent_qualified_name:
                        pending_calls.append(
                            (el.parent_qualified_name, el.target or el.name)
                        )
                    continue

                if el.element_type == "import":
                    if el.parent_qualified_name:
                        pending_imports.append(
                            (el.parent_qualified_name, el.target or el.name)
                        )
                    continue

                graph.add_node(
                    el.qualified_name,
                    label=el.name,
                    node_type=el.element_type,
                    file_path=el.file_path,
                    language=el.language,
                    start_line=el.start_line,
                    end_line=el.end_line,
                    signature=el.signature,
                    docstring=el.docstring,
                    source_code=el.source_code,
                )

                if el.element_type in (
                    "function", "method", "class", "interface", "struct"
                ):
                    name_to_qns[el.name].append(el.qualified_name)

                if (
                    el.parent_qualified_name
                    and el.parent_qualified_name != el.qualified_name
                ):
                    graph.add_edge(
                        el.parent_qualified_name,
                        el.qualified_name,
                        edge_type="contains",
                    )

        # Resolve CALLS edges (name-based best-effort)
        for caller, callee_name in pending_calls:
            for tgt in name_to_qns.get(callee_name, []):
                if tgt != caller and caller in graph and tgt in graph:
                    graph.add_edge(caller, tgt, edge_type="calls")

        # Resolve IMPORTS edges
        for mod, target in pending_imports:
            if mod not in graph:
                continue
            target_leaf = target.split(".")[-1]
            matched = False
            for cqn, data in graph.nodes(data=True):
                if data.get("node_type") == "module" and (
                    cqn == target or cqn == target_leaf
                ):
                    graph.add_edge(mod, cqn, edge_type="imports")
                    matched = True
                    break
            if not matched:
                ext = f"external::{target}"
                if ext not in graph:
                    graph.add_node(ext, label=target, node_type="external_dependency")
                graph.add_edge(mod, ext, edge_type="imports")

        return graph

    # ------------------------------------------------------------------
    # Persistence  (chunked to avoid WinError 10055)
    # ------------------------------------------------------------------

    async def persist_graph(
        self,
        db: AsyncSession,
        repository_id: uuid.UUID,
        graph: nx.MultiDiGraph,
        qn_to_element_id: dict[str, uuid.UUID],
    ) -> None:
        """
        Persist GraphNode + GraphEdge rows in small chunks.

        Only nodes that have a corresponding CodeElement (i.e. are in
        `qn_to_element_id`) are persisted — external dependency nodes
        are skipped.
        """
        qn_to_node_id: dict[str, uuid.UUID] = {}

        # Persist nodes in chunks
        node_items = [
            (qn, data)
            for qn, data in graph.nodes(data=True)
            if qn in qn_to_element_id
        ]

        for i in range(0, len(node_items), _PERSIST_CHUNK):
            chunk = node_items[i : i + _PERSIST_CHUNK]
            for qn, data in chunk:
                node = GraphNode(
                    repository_id=repository_id,
                    code_element_id=qn_to_element_id[qn],
                    label=data.get("label", qn),
                    node_type=data.get("node_type", "unknown"),
                )
                db.add(node)
            await db.flush()
            # Collect IDs after flush
            # Re-query would be safer but flush populates node.id in-place
            for qn, _ in chunk:
                # The node object is still in the session identity map
                pass
            await db.commit()

        # We need the node IDs — re-query them
        from sqlalchemy import select
        from backend.models.graph_node import GraphNode as GN
        stmt = (
            select(GN)
            .where(GN.repository_id == repository_id)
        )
        result = await db.execute(stmt)
        for node_row in result.scalars().all():
            # Map code_element_id back to qualified_name via qn_to_element_id
            pass

        # Simpler: build a reverse map from element_id → qn
        el_id_to_qn = {v: k for k, v in qn_to_element_id.items()}

        stmt2 = select(GN).where(GN.repository_id == repository_id)
        r2 = await db.execute(stmt2)
        for row in r2.scalars().all():
            qn = el_id_to_qn.get(row.code_element_id)
            if qn:
                qn_to_node_id[qn] = row.id

        # Persist edges in chunks
        edge_items = list(graph.edges(data=True))
        for i in range(0, len(edge_items), _PERSIST_CHUNK):
            chunk = edge_items[i : i + _PERSIST_CHUNK]
            for u, v, data in chunk:
                sid = qn_to_node_id.get(u)
                tid = qn_to_node_id.get(v)
                if sid is None or tid is None:
                    continue
                raw_type = data.get("edge_type", "references")
                try:
                    et = EdgeType(raw_type)
                except ValueError:
                    et = EdgeType.REFERENCES
                db.add(GraphEdge(source_id=sid, target_id=tid, edge_type=et))
            await db.commit()

        logger.info(
            "Persisted %d graph nodes and %d edges",
            len(qn_to_node_id), len(edge_items),
        )

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def compute_centrality(self, graph: nx.MultiDiGraph) -> dict[str, float]:
        """PageRank centrality for each node (falls back to degree centrality)."""
        if graph.number_of_nodes() == 0:
            return {}
        try:
            return nx.pagerank(graph)
        except Exception:
            return nx.degree_centrality(graph)

    def detect_unreferenced_nodes(self, graph: nx.MultiDiGraph) -> list[str]:
        """
        Return qualified names of function/method/class nodes with zero
        incoming CALLS/IMPORTS/INHERITS/IMPLEMENTS edges — dead-code candidates.
        """
        candidates: list[str] = []
        for qn, data in graph.nodes(data=True):
            if data.get("node_type") not in ("function", "method", "class"):
                continue
            label = data.get("label", "")
            if label in ("main", "__init__", "__main__") or label.startswith(
                ("test_", "Test")
            ):
                continue
            in_edges = [
                d for _, _, d in graph.in_edges(qn, data=True)
                if d.get("edge_type") in (
                    "calls", "imports", "inherits", "implements"
                )
            ]
            if not in_edges:
                candidates.append(qn)
        return candidates
