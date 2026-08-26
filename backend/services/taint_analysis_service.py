"""
Call-graph-level interprocedural taint-flow analysis.

Design decision — what we are and are NOT doing:
  We are doing: call-graph reachability.  If function A's source code contains
  a taint-source pattern and a CALLS edge (any number of hops) leads to
  function B whose source code contains a taint-sink pattern, that is a
  finding.

  We are NOT doing: statement-level, flow-sensitive, or points-to analysis.
  That is a deliberate, defensible tradeoff — the same one made by scalable
  real-world SAST tools (Semgrep, Bandit) for any repo larger than ~10k LOC.
  Full data-flow analysis requires an SSA representation and alias analysis
  that is O(n³) in the worst case and out of scope here.

Confidence levels:
  "high"   — same function body contains both source and sink (direct), or
              the source directly calls the sink (1 hop).
  "medium" — 2–3 hops.
  "low"    — 4–6 hops.

Max depth is capped at DEFAULT_MAX_DEPTH to keep BFS O(n) on large repos.
"""
from __future__ import annotations

import logging
from collections import deque

import networkx as nx

from backend.services.taint_patterns import SINKS, SOURCES

logger = logging.getLogger(__name__)

DEFAULT_MAX_DEPTH = 6

_CONF_RANK = {"high": 0, "medium": 1, "low": 2}


class TaintAnalysisService:

    # ------------------------------------------------------------------
    # Pattern scanning helpers
    # ------------------------------------------------------------------

    def find_source_functions(
        self, graph: nx.MultiDiGraph, language: str = "python"
    ) -> list[str]:
        """
        Return qualified names of function/method nodes whose source_code
        matches at least one source pattern for the given language.
        """
        patterns = SOURCES.get(language, [])
        if not patterns:
            return []
        sources: list[str] = []
        for qn, data in graph.nodes(data=True):
            if data.get("node_type") not in ("function", "method"):
                continue
            code = data.get("source_code") or ""
            if any(pat.search(code) for pat, _ in patterns):
                sources.append(qn)
        return sources

    def find_sink_functions(
        self, graph: nx.MultiDiGraph, language: str = "python"
    ) -> list[tuple[str, str]]:
        """
        Return (qualified_name, vuln_class) tuples for function/method nodes
        whose source_code matches at least one sink pattern.
        First matching sink pattern wins; a function is counted once.
        """
        patterns = SINKS.get(language, [])
        if not patterns:
            return []
        sinks: list[tuple[str, str]] = []
        for qn, data in graph.nodes(data=True):
            if data.get("node_type") not in ("function", "method"):
                continue
            code = data.get("source_code") or ""
            for pat, _label, vuln_class in patterns:
                if pat.search(code):
                    sinks.append((qn, vuln_class))
                    break
        return sinks

    # ------------------------------------------------------------------
    # Finding detection
    # ------------------------------------------------------------------

    def find_direct_findings(
        self,
        graph: nx.MultiDiGraph,
        sources: list[str],
        sinks: list[tuple[str, str]],
    ) -> list[dict]:
        """
        Direct (intra-function) findings: the same function body contains
        both a taint source pattern and a taint sink pattern.

        These have the highest confidence because there is no ambiguity
        about whether the tainted value actually reaches the sink — both
        patterns are present in the identical code block.
        """
        sink_map: dict[str, str] = dict(sinks)
        findings: list[dict] = []
        for qn in sources:
            if qn not in sink_map:
                continue
            data = graph.nodes[qn]
            findings.append({
                "finding_type": "direct",
                "source_qn": qn,
                "source_file": data.get("file_path"),
                "source_line": data.get("start_line"),
                "sink_qn": qn,
                "sink_file": data.get("file_path"),
                "sink_line": data.get("start_line"),
                "path": [qn],
                "vuln_class": sink_map[qn],
                "confidence": "high",
            })
        return findings

    def find_interprocedural_paths(
        self,
        graph: nx.MultiDiGraph,
        sources: list[str],
        sinks: list[tuple[str, str]],
        max_depth: int = DEFAULT_MAX_DEPTH,
    ) -> list[dict]:
        """
        BFS over CALLS edges from each source function.

        For each source, we explore the call graph forward (caller → callee)
        up to max_depth hops.  When we reach a sink we record the full path.

        We do NOT continue BFS through a sink node — if a sink also calls
        other sinks, those will be found when that intermediate node is itself
        a source.

        visited is per-source to allow the same intermediate node to appear
        in multiple source-paths (different entry points can converge).
        """
        sink_map: dict[str, str] = dict(sinks)
        findings: list[dict] = []

        for src_qn in sources:
            if src_qn not in graph:
                continue

            queue: deque[tuple[str, list[str]]] = deque([(src_qn, [src_qn])])
            visited: set[str] = {src_qn}

            while queue:
                current, path = queue.popleft()
                depth = len(path) - 1

                for _, neighbor, edata in graph.out_edges(current, data=True):
                    if edata.get("edge_type") != "calls":
                        continue
                    if neighbor in visited:
                        continue

                    new_path = path + [neighbor]
                    hop_count = len(new_path) - 1

                    if neighbor in sink_map:
                        # Skip self-loops (same function) — already a direct finding
                        if neighbor == src_qn:
                            continue
                        # Respect the depth cap even for sinks
                        if hop_count > max_depth:
                            continue
                        if hop_count == 1:
                            confidence = "high"
                        elif hop_count <= 3:
                            confidence = "medium"
                        else:
                            confidence = "low"
                        src_data  = graph.nodes.get(src_qn, {})
                        sink_data = graph.nodes.get(neighbor, {})
                        findings.append({
                            "finding_type": "interprocedural",
                            "source_qn": src_qn,
                            "source_file": src_data.get("file_path"),
                            "source_line": src_data.get("start_line"),
                            "sink_qn": neighbor,
                            "sink_file": sink_data.get("file_path"),
                            "sink_line": sink_data.get("start_line"),
                            "path": new_path,
                            "vuln_class": sink_map[neighbor],
                            "confidence": confidence,
                        })
                        # Don't explore beyond a confirmed sink
                    elif depth < max_depth:
                        visited.add(neighbor)
                        queue.append((neighbor, new_path))

        return findings

    # ------------------------------------------------------------------
    # Top-level entry point
    # ------------------------------------------------------------------

    def run(
        self, graph: nx.MultiDiGraph, language: str = "python"
    ) -> list[dict]:
        """
        Run the complete taint analysis and return deduplicated findings,
        sorted by confidence (high → low).

        Deduplication rule: if the same (source_qn, sink_qn) pair is found
        via multiple paths, we keep only the highest-confidence finding
        (shortest / most direct path wins).
        """
        sources = self.find_source_functions(graph, language)
        sinks   = self.find_sink_functions(graph, language)
        logger.info(
            "Taint[%s]: %d source functions, %d sink functions",
            language, len(sources), len(sinks),
        )
        if not sources or not sinks:
            return []

        direct = self.find_direct_findings(graph, sources, sinks)
        interp = self.find_interprocedural_paths(graph, sources, sinks)

        # Deduplicate on (source_qn, sink_qn) — keep highest confidence
        seen: dict[tuple[str, str], dict] = {}
        for f in direct + interp:
            key = (f["source_qn"], f["sink_qn"])
            existing = seen.get(key)
            if existing is None or _CONF_RANK[f["confidence"]] < _CONF_RANK[existing["confidence"]]:
                seen[key] = f

        findings = sorted(seen.values(), key=lambda f: _CONF_RANK[f["confidence"]])
        logger.info("Taint[%s]: %d unique findings after dedup", language, len(findings))
        return findings
