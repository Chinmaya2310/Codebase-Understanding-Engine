"""Dead code detection via graph reachability."""
from __future__ import annotations
import re
import networkx as nx

_ENTRYPOINTS = [
    re.compile(r"^__\w+__$"), re.compile(r"^test_"), re.compile(r"^Test"),
    re.compile(r"^main$"), re.compile(r"^setup$"), re.compile(r"^teardown$"),
    re.compile(r"^handle"), re.compile(r"^on_"),
]


class DeadCodeService:
    def find_dead_code(self, graph: nx.MultiDiGraph) -> list[dict]:
        findings = []
        for qn, data in graph.nodes(data=True):
            if data.get("node_type") not in ("function", "method", "class"):
                continue
            label = data.get("label", "")
            if any(p.match(label) for p in _ENTRYPOINTS):
                continue
            in_edges = [d for _, _, d in graph.in_edges(qn, data=True)
                        if d.get("edge_type") in ("calls", "imports", "inherits", "implements")]
            if in_edges:
                continue
            confidence = "high"
            for _, _, d in graph.in_edges(qn, data=True):
                if d.get("edge_type") != "contains":
                    confidence = "medium"
                    break
            findings.append({
                "qualified_name": qn, "node_type": data.get("node_type"),
                "file_path": data.get("file_path"), "start_line": data.get("start_line"),
                "end_line": data.get("end_line"),
                "reason": f"No references found to this {data.get('node_type')}.",
                "confidence": confidence,
            })
        return findings
