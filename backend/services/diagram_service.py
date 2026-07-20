"""Diagram generation and architecture detection."""
from __future__ import annotations
import re
from collections import defaultdict
import networkx as nx

_LAYERS = {
    "presentation": ["controllers","views","components","pages","routes","api","handlers"],
    "business": ["services","domain","core","usecases","logic"],
    "data": ["models","repositories","db","database","entities","dao"],
}


class DiagramService:
    def generate_dependency_diagram(self, graph: nx.MultiDiGraph, max_nodes: int = 40) -> str:
        modules = [(qn, d) for qn, d in graph.nodes(data=True) if d.get("node_type") in ("module", "external_dependency")]
        degrees = dict(graph.degree())
        modules.sort(key=lambda x: degrees.get(x[0], 0), reverse=True)
        selected = {qn for qn, _ in modules[:max_nodes]}
        lines = ["graph LR"]
        seen = set()
        for u, v, d in graph.edges(data=True):
            if d.get("edge_type") != "imports" or u not in selected or v not in selected:
                continue
            k = (u, v)
            if k in seen: continue
            seen.add(k)
            lines.append(f'    {self._sid(u)}["{self._lbl(graph, u)}"] --> {self._sid(v)}["{self._lbl(graph, v)}"]')
        if len(lines) == 1:
            lines.append('    NoData["No module import relationships detected"]')
        return "\n".join(lines)

    def generate_architecture_diagram(self, graph: nx.MultiDiGraph, layers: dict) -> str:
        lines = ["graph TD"]
        for layer, modules in layers.items():
            if not modules: continue
            lines.append(f'    subgraph {self._sid(layer)} ["{layer.title()} Layer"]')
            for m in modules[:12]:
                lines.append(f'        {self._sid(m)}["{self._lbl(graph, m)}"]')
            lines.append("    end")
        order = [l for l in ["presentation", "business", "data"] if layers.get(l)]
        for i in range(len(order) - 1):
            lines.append(f"    {self._sid(order[i])} --> {self._sid(order[i+1])}")
        if len(lines) == 1:
            lines.append('    NoData["No clear architectural layers detected"]')
        return "\n".join(lines)

    def detect_architecture(self, graph: nx.MultiDiGraph) -> dict:
        layers: dict[str, list[str]] = defaultdict(list)
        ms_dirs: set[str] = set()
        for qn, data in graph.nodes(data=True):
            if data.get("node_type") != "module": continue
            fp = (data.get("file_path") or "").lower().replace("\\", "/")
            for layer, signals in _LAYERS.items():
                if any(f"/{s}/" in fp or fp.startswith(f"{s}/") for s in signals):
                    layers[layer].append(qn); break
            for sig in ["services/", "apps/", "packages/"]:
                m = re.search(rf"{re.escape(sig)}([^/]+)/", fp)
                if m: ms_dirs.add(m.group(1))
        lc = sum(1 for v in layers.values() if v)
        if len(ms_dirs) >= 3:
            pattern, conf = "microservices", min(0.5 + 0.1 * len(ms_dirs), 0.9)
        elif lc >= 3:
            pattern, conf = "mvc" if layers.get("presentation") and "controllers" in str(layers) else "layered", 0.5 + 0.15 * lc
        elif lc >= 1:
            pattern, conf = "layered", 0.4
        else:
            pattern, conf = "unclear", 0.1
        return {"pattern": pattern, "layers": dict(layers), "microservices_detected": sorted(ms_dirs), "confidence": round(min(conf, 0.95), 2)}

    def generate_code_graph_json(self, graph: nx.MultiDiGraph, max_nodes: int = 200) -> dict:
        degrees = dict(graph.degree())
        ranked = sorted(graph.nodes(data=True), key=lambda x: degrees.get(x[0], 0), reverse=True)
        selected = {qn for qn, _ in ranked[:max_nodes]}
        nodes = [{"id": qn, "label": d.get("label", qn), "type": d.get("node_type", "unknown"), "file_path": d.get("file_path")} for qn, d in ranked[:max_nodes]]
        edges = [{"source": u, "target": v, "type": d.get("edge_type", "references")} for u, v, d in graph.edges(data=True) if u in selected and v in selected]
        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _sid(s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", s)

    @staticmethod
    def _lbl(graph: nx.MultiDiGraph, qn: str) -> str:
        if qn not in graph: return qn
        return graph.nodes[qn].get("label", qn).replace('"', "'")
