import { useEffect, useRef, useState } from "react";
import { Layers, Loader2, GitBranch, AlertCircle, CheckCircle } from "lucide-react";
import { api } from "../services/api";
import type { ArchitectureResult, DiagramResult } from "../types";

function MermaidDiagram({ definition, id }: { definition: string; id: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ref.current || !definition) return;
    setError(false);
    const el = ref.current;
    el.innerHTML = "";

    const tryRender = () => {
      const mermaid = (window as any).mermaid;
      if (!mermaid) { setTimeout(tryRender, 300); return; }
      try {
        mermaid.initialize({ startOnLoad: false, theme: "dark", darkMode: true,
          themeVariables: { primaryColor: "#6c63ff", primaryTextColor: "#e8eaf0", primaryBorderColor: "#2a2e38",
            lineColor: "#5c6478", background: "#111318", mainBkg: "#1a1d24",
            nodeBorder: "#363b47", clusterBkg: "#1a1d24", titleColor: "#e8eaf0",
            edgeLabelBackground: "#111318", tertiaryColor: "#22262f" }
        });
        const uniqueId = `mermaid-${id}-${Date.now()}`;
        mermaid.render(uniqueId, definition).then(({ svg }: { svg: string }) => {
          el.innerHTML = svg;
          const svgEl = el.querySelector("svg");
          if (svgEl) {
            svgEl.style.maxWidth = "100%";
            svgEl.style.height = "auto";
          }
        }).catch(() => { setError(true); el.innerHTML = `<pre style="font-size:11px;color:#9ba3b4;white-space:pre-wrap;overflow:auto">${definition}</pre>`; });
      } catch { setError(true); }
    };

    tryRender();
  }, [definition, id]);

  return <div ref={ref} style={{ padding: 16, minHeight: 120 }} />;
}

function PatternBadge({ pattern, confidence }: { pattern: string; confidence: number }) {
  const colors: Record<string, { bg: string; color: string }> = {
    mvc:          { bg: "rgba(96,165,250,0.1)",  color: "#60a5fa" },
    layered:      { bg: "rgba(108,99,255,0.12)", color: "#6c63ff" },
    microservices:{ bg: "rgba(167,139,250,0.1)", color: "#a78bfa" },
    unclear:      { bg: "rgba(91,101,120,0.15)", color: "#9ba3b4" },
  };
  const c = colors[pattern] ?? colors.unclear;
  return (
    <span style={{ padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 600, background: c.bg, color: c.color, display: "inline-flex", alignItems: "center", gap: 5 }}>
      <CheckCircle size={11} />
      {pattern.charAt(0).toUpperCase() + pattern.slice(1)}
      <span style={{ opacity: 0.6, fontWeight: 400 }}>({Math.round(confidence * 100)}%)</span>
    </span>
  );
}

const LAYER_COLORS: Record<string, string> = {
  presentation: "#60a5fa", business: "#34d399", data: "#fbbf24",
};

export function ArchitectureDiagram({ repositoryId }: { repositoryId: string }) {
  const [arch, setArch] = useState<ArchitectureResult | null>(null);
  const [diagrams, setDiagrams] = useState<DiagramResult | null>(null);
  const [tab, setTab] = useState<"arch" | "dep">("arch");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load Mermaid script
    if (!(window as any).mermaid) {
      const s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js";
      s.async = true;
      document.head.appendChild(s);
    }

    Promise.all([api.getArchitecture(repositoryId), api.getDiagrams(repositoryId)])
      .then(([a, d]) => { setArch(a); setDiagrams(d); })
      .catch(err => setError(err?.response?.data?.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  }, [repositoryId]);

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", gap: 10, color: "var(--text3)" }}>
      <Loader2 size={18} className="animate-spin" /> Loading architecture…
    </div>
  );
  if (error) return <div style={{ padding: 20, color: "var(--red)", fontSize: 13 }}>{error}</div>;

  const currentDiagram = tab === "arch" ? diagrams?.architecture_diagram : diagrams?.dependency_diagram;
  const layers = arch?.layers ?? {};
  const totalLayerModules = Object.values(layers).reduce((a, v) => a + v.length, 0);

  return (
    <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div style={{ width: 34, height: 34, borderRadius: 10, background: "var(--accent-bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Layers size={16} color="var(--accent2)" />
        </div>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text)" }}>Architecture Analysis</h2>
          <p style={{ fontSize: 12, color: "var(--text3)" }}>Detected from directory structure and import patterns</p>
        </div>
        {arch && <PatternBadge pattern={arch.pattern} confidence={arch.confidence} />}
      </div>

      {/* Layer stats */}
      {Object.keys(layers).length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10 }}>
          {Object.entries(layers).map(([layer, modules]) => {
            const color = LAYER_COLORS[layer] ?? "var(--accent2)";
            return (
              <div key={layer} style={{ background: "var(--bg3)", border: `1px solid ${color}30`, borderRadius: "var(--radius)", padding: "14px 16px", borderLeft: `3px solid ${color}` }}>
                <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color, marginBottom: 6 }}>{layer}</p>
                <p style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", lineHeight: 1 }}>{modules.length}</p>
                <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 3 }}>modules</p>
              </div>
            );
          })}
          {arch?.microservices_detected && arch.microservices_detected.length > 0 && (
            <div style={{ background: "var(--bg3)", border: "1px solid var(--purple)30", borderRadius: "var(--radius)", padding: "14px 16px", borderLeft: "3px solid var(--purple)" }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--purple)", marginBottom: 6 }}>services</p>
              <p style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", lineHeight: 1 }}>{arch.microservices_detected.length}</p>
              <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 3 }}>detected</p>
            </div>
          )}
        </div>
      )}

      {/* Tab switcher */}
      <div style={{ display: "flex", gap: 2, background: "var(--bg3)", padding: 4, borderRadius: "var(--radius-sm)", width: "fit-content" }}>
        {(["arch", "dep"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "6px 16px", borderRadius: 7, border: "none", fontSize: 12, fontWeight: 500, cursor: "pointer",
            background: tab === t ? "var(--bg4)" : "transparent",
            color: tab === t ? "var(--text)" : "var(--text3)",
            transition: "all 0.15s",
          }}>
            {t === "arch" ? "Architecture" : "Dependencies"}
          </button>
        ))}
      </div>

      {/* Diagram */}
      <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", overflow: "hidden", minHeight: 200 }}>
        {currentDiagram ? (
          <MermaidDiagram key={`${tab}-${repositoryId}`} definition={currentDiagram} id={`${tab}-${repositoryId}`} />
        ) : (
          <div style={{ padding: 24, textAlign: "center", color: "var(--text3)", fontSize: 13 }}>No diagram available</div>
        )}
      </div>

      {/* Microservices list */}
      {arch?.microservices_detected && arch.microservices_detected.length > 0 && (
        <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "16px" }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text2)", marginBottom: 10 }}>Detected Services</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {arch.microservices_detected.map(s => (
              <span key={s} style={{ padding: "3px 10px", borderRadius: 20, background: "rgba(167,139,250,0.1)", color: "var(--purple)", fontSize: 12, fontFamily: "monospace" }}>{s}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
