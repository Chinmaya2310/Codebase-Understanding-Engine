import { useEffect, useRef, useState } from "react";
import { Network, Loader2, ZoomIn, ZoomOut, Maximize2, Info } from "lucide-react";
import * as d3 from "d3";
import { api } from "../services/api";
import type { DiagramResult } from "../types";

type GNode = DiagramResult["code_graph"]["nodes"][0] & { x?: number; y?: number; vx?: number; vy?: number; fx?: number|null; fy?: number|null };
type GEdge = { source: string | GNode; target: string | GNode; type: string };

const TYPE_COLORS: Record<string, string> = {
  module: "#6c63ff", class: "#a78bfa", function: "#22d3ee",
  method: "#60a5fa", struct: "#c084fc", interface: "#f472b6",
  external_dependency: "#374151", unknown: "#4b5563",
};

const TYPE_SIZE: Record<string, number> = {
  module: 9, class: 7, function: 5, method: 5,
  struct: 6, interface: 6, external_dependency: 4, unknown: 4,
};

export function CodeGraph({ repositoryId }: { repositoryId: string }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<GNode | null>(null);
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const svgSelection = useRef<d3.Selection<SVGSVGElement, unknown, null, undefined> | null>(null);

  useEffect(() => {
    api.getDiagrams(repositoryId)
      .then(data => {
        setStats({ nodes: data.code_graph.nodes.length, edges: data.code_graph.edges.length });
        renderGraph(data.code_graph.nodes, data.code_graph.edges);
      })
      .catch(err => setError(err?.response?.data?.detail ?? "Failed to load graph"))
      .finally(() => setLoading(false));
  }, [repositoryId]);

  function renderGraph(rawNodes: DiagramResult["code_graph"]["nodes"], rawEdges: DiagramResult["code_graph"]["edges"]) {
    const container = svgRef.current?.parentElement;
    const width = container?.clientWidth ?? 900;
    const height = container?.clientHeight ?? 560;

    const svg = d3.select(svgRef.current!).attr("width", width).attr("height", height);
    svg.selectAll("*").remove();
    svgSelection.current = svg;

    const g = svg.append("g");
    const zoom = d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.05, 8]).on("zoom", e => g.attr("transform", e.transform));
    svg.call(zoom);
    zoomRef.current = zoom;

    const nodeMap = new Map<string, GNode>();
    rawNodes.forEach(n => nodeMap.set(n.id, { ...n }));
    const nodes: GNode[] = Array.from(nodeMap.values());
    const links: GEdge[] = rawEdges.filter(e => nodeMap.has(e.source as string) && nodeMap.has(e.target as string))
      .map(e => ({ source: e.source, target: e.target, type: e.type }));

    // Defs
    const defs = svg.append("defs");
    defs.append("marker").attr("id","arrow").attr("viewBox","0 -4 8 8").attr("refX",16).attr("refY",0).attr("markerWidth",5).attr("markerHeight",5).attr("orient","auto")
      .append("path").attr("d","M0,-4L8,0L0,4").attr("fill","rgba(255,255,255,0.1)");

    // Background grid
    const pattern = defs.append("pattern").attr("id","grid").attr("width",40).attr("height",40).attr("patternUnits","userSpaceOnUse");
    pattern.append("path").attr("d","M 40 0 L 0 0 0 40").attr("fill","none").attr("stroke","rgba(255,255,255,0.03)").attr("stroke-width",1);
    g.append("rect").attr("width", width * 4).attr("height", height * 4).attr("x", -width * 1.5).attr("y", -height * 1.5).attr("fill","url(#grid)");

    const sim = d3.forceSimulation<GNode>(nodes)
      .force("link", d3.forceLink<GNode, GEdge>(links).id(d => d.id).distance(70).strength(0.4))
      .force("charge", d3.forceManyBody().strength(-180))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(14));

    const link = g.append("g").selectAll("line").data(links).join("line")
      .attr("stroke", "rgba(255,255,255,0.06)").attr("stroke-width", 1)
      .attr("marker-end", "url(#arrow)");

    const node = g.append("g").selectAll<SVGGElement, GNode>("g").data(nodes).join("g")
      .attr("cursor", "pointer")
      .call(d3.drag<SVGGElement, GNode>()
        .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }))
      .on("click", (_, d) => setSelected(d));

    // Glow filter
    const filter = defs.append("filter").attr("id","glow");
    filter.append("feGaussianBlur").attr("stdDeviation","3").attr("result","coloredBlur");
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in","coloredBlur");
    feMerge.append("feMergeNode").attr("in","SourceGraphic");

    node.append("circle")
      .attr("r", d => TYPE_SIZE[d.type] ?? 5)
      .attr("fill", d => TYPE_COLORS[d.type] ?? "#4b5563")
      .attr("stroke", d => `${TYPE_COLORS[d.type] ?? "#4b5563"}60`)
      .attr("stroke-width", 3)
      .style("filter", "url(#glow)");

    node.append("text").attr("dx", d => (TYPE_SIZE[d.type] ?? 5) + 5).attr("dy", "0.35em")
      .attr("font-size", 9).attr("fill", "rgba(255,255,255,0.5)")
      .text(d => d.label.length > 18 ? d.label.slice(0, 16) + "…" : d.label);

    sim.on("tick", () => {
      link.attr("x1", d => (d.source as GNode).x ?? 0).attr("y1", d => (d.source as GNode).y ?? 0)
          .attr("x2", d => (d.target as GNode).x ?? 0).attr("y2", d => (d.target as GNode).y ?? 0);
      node.attr("transform", d => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });
  }

  function zoomIn() {
    if (zoomRef.current && svgSelection.current)
      svgSelection.current.transition().call(zoomRef.current.scaleBy, 1.5);
  }
  function zoomOut() {
    if (zoomRef.current && svgSelection.current)
      svgSelection.current.transition().call(zoomRef.current.scaleBy, 0.67);
  }
  function resetZoom() {
    if (zoomRef.current && svgSelection.current)
      svgSelection.current.transition().call(zoomRef.current.transform, d3.zoomIdentity);
  }

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text3)", gap: 10 }}>
      <Loader2 size={18} className="animate-spin" /> Building code graph…
    </div>
  );
  if (error) return <div style={{ padding: 20, color: "var(--red)", fontSize: 13 }}>{error}</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Toolbar */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 12, background: "var(--bg2)" }}>
        <Network size={15} color="var(--accent2)" />
        <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text)" }}>Code Graph</span>
        <span style={{ fontSize: 11, color: "var(--text3)" }}>{stats.nodes} nodes · {stats.edges} edges</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          {[{icon: ZoomIn, fn: zoomIn}, {icon: ZoomOut, fn: zoomOut}, {icon: Maximize2, fn: resetZoom}].map(({icon: Icon, fn}, i) => (
            <button key={i} onClick={fn} style={{ width: 28, height: 28, borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg3)", color: "var(--text2)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon size={13} />
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {Object.entries(TYPE_COLORS).filter(([k]) => !["external_dependency","unknown"].includes(k)).map(([type, color]) => (
            <span key={type} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: "var(--text3)" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: color, display: "inline-block" }} />{type}
            </span>
          ))}
        </div>
      </div>

      {/* Graph */}
      <div style={{ flex: 1, position: "relative", overflow: "hidden", background: "var(--bg)" }}>
        <svg ref={svgRef} style={{ width: "100%", height: "100%" }} />
        {selected && (
          <div style={{ position: "absolute", top: 12, right: 12, background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 14, maxWidth: 260, boxShadow: "var(--shadow)" }} className="animate-fade">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: TYPE_COLORS[selected.type] ?? "var(--text3)" }}>
                {selected.type}
              </span>
              <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", color: "var(--text3)", cursor: "pointer", fontSize: 16 }}>✕</button>
            </div>
            <p style={{ fontFamily: "monospace", fontSize: 13, fontWeight: 600, color: "var(--text)", marginBottom: 6 }}>{selected.label}</p>
            {selected.file_path && (
              <p style={{ fontSize: 11, color: "var(--text3)", wordBreak: "break-all" }}>
                {selected.file_path.split(/[/\\]/).slice(-3).join("/")}
              </p>
            )}
          </div>
        )}
        <div style={{ position: "absolute", bottom: 12, left: 12, fontSize: 10, color: "var(--text3)", background: "var(--bg2)", padding: "5px 10px", borderRadius: 6, border: "1px solid var(--border)" }}>
          <Info size={10} style={{ display: "inline", marginRight: 5 }} />Drag to move · Scroll to zoom · Click node to inspect
        </div>
      </div>
    </div>
  );
}
