import { useEffect, useState } from "react";
import { ShieldOff, Loader2, AlertTriangle, Filter, ChevronDown, ChevronUp, TrendingDown } from "lucide-react";
import { api } from "../services/api";
import type { DeadCodeFinding } from "../types";

function FindingCard({ f }: { f: DeadCodeFinding }) {
  const [open, setOpen] = useState(false);
  const isHigh = f.confidence === "high";
  return (
    <div style={{ background: "var(--bg3)", border: `1px solid ${isHigh ? "rgba(248,113,113,0.2)" : "rgba(251,191,36,0.15)"}`, borderRadius: "var(--radius)", overflow: "hidden" }}>
      <div onClick={() => setOpen(!open)} style={{ padding: "12px 14px", cursor: "pointer", display: "flex", alignItems: "flex-start", gap: 10 }}>
        <div style={{ width: 24, height: 24, borderRadius: 6, background: isHigh ? "var(--red-bg)" : "var(--amber-bg)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
          <AlertTriangle size={12} color={isHigh ? "var(--red)" : "var(--amber)"} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "monospace", fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
              {f.qualified_name.split(".").pop()}
            </span>
            <span style={{ fontSize: 10, padding: "2px 7px", borderRadius: 4, background: "var(--bg4)", color: "var(--text3)", fontWeight: 500 }}>
              {f.node_type}
            </span>
            <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 10, fontWeight: 600, background: isHigh ? "var(--red-bg)" : "var(--amber-bg)", color: isHigh ? "var(--red)" : "var(--amber)" }}>
              {f.confidence}
            </span>
          </div>
          <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 3, fontFamily: "monospace" }} className="truncate">
            {f.file_path ? f.file_path.split(/[/\\]/).slice(-3).join("/") : "—"}
            {f.start_line ? `:${f.start_line}` : ""}
          </p>
        </div>
        {open ? <ChevronUp size={13} color="var(--text3)" style={{ flexShrink: 0 }} /> : <ChevronDown size={13} color="var(--text3)" style={{ flexShrink: 0 }} />}
      </div>
      {open && (
        <div style={{ padding: "0 14px 12px 48px", borderTop: "1px solid var(--border)" }}>
          <p style={{ fontSize: 12, color: "var(--text2)", marginTop: 10, lineHeight: 1.6 }}>{f.reason}</p>
          {f.file_path && (
            <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 6, fontFamily: "monospace" }}>{f.file_path}</p>
          )}
        </div>
      )}
    </div>
  );
}

export function DeadCodePanel({ repositoryId }: { repositoryId: string }) {
  const [findings, setFindings] = useState<DeadCodeFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all"|"high"|"medium">("all");
  const [typeFilter, setTypeFilter] = useState<"all"|"function"|"method"|"class">("all");

  useEffect(() => {
    api.getDeadCode(repositoryId)
      .then(d => setFindings(d.findings))
      .catch(err => setError(err?.response?.data?.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  }, [repositoryId]);

  const visible = findings.filter(f =>
    (filter === "all" || f.confidence === filter) &&
    (typeFilter === "all" || f.node_type === typeFilter)
  );
  const high = findings.filter(f => f.confidence === "high").length;
  const med = findings.filter(f => f.confidence === "medium").length;
  const byType = findings.reduce((a, f) => { a[f.node_type] = (a[f.node_type] || 0) + 1; return a; }, {} as Record<string, number>);

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", gap: 10, color: "var(--text3)" }}>
      <Loader2 size={18} className="animate-spin" /> Scanning for dead code…
    </div>
  );
  if (error) return <div style={{ padding: 20, color: "var(--red)", fontSize: 13 }}>{error}</div>;

  return (
    <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ width: 34, height: 34, borderRadius: 10, background: "rgba(251,191,36,0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <ShieldOff size={16} color="var(--amber)" />
        </div>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text)" }}>Dead Code Detection</h2>
          <p style={{ fontSize: 12, color: "var(--text3)" }}>Functions and classes with no detected references</p>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
        {[
          { label: "total", value: findings.length, color: "var(--text2)", bg: "var(--bg3)" },
          { label: "high confidence", value: high, color: "var(--red)", bg: "var(--red-bg)" },
          { label: "medium confidence", value: med, color: "var(--amber)", bg: "var(--amber-bg)" },
          { label: "types affected", value: Object.keys(byType).length, color: "var(--blue)", bg: "var(--blue-bg)" },
        ].map(({ label, value, color, bg }) => (
          <div key={label} style={{ background: bg, border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "14px 16px" }}>
            <p style={{ fontSize: 26, fontWeight: 700, color, lineHeight: 1 }}>{value}</p>
            <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 3 }}>{label}</p>
          </div>
        ))}
      </div>

      {/* Breakdown by type */}
      {Object.keys(byType).length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {Object.entries(byType).map(([type, count]) => (
            <div key={type} style={{ padding: "6px 12px", borderRadius: 8, background: "var(--bg3)", border: "1px solid var(--border)", fontSize: 12 }}>
              <span style={{ color: "var(--text2)", fontWeight: 500 }}>{type}</span>
              <span style={{ color: "var(--text3)", marginLeft: 6 }}>{count}</span>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 2, background: "var(--bg3)", padding: 3, borderRadius: "var(--radius-sm)" }}>
          {(["all","high","medium"] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: "5px 12px", borderRadius: 6, border: "none", fontSize: 11, fontWeight: 500, cursor: "pointer",
              background: filter === f ? "var(--bg4)" : "transparent",
              color: filter === f ? "var(--text)" : "var(--text3)",
            }}>{f}</button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 2, background: "var(--bg3)", padding: 3, borderRadius: "var(--radius-sm)" }}>
          {(["all","function","method","class"] as const).map(t => (
            <button key={t} onClick={() => setTypeFilter(t)} style={{
              padding: "5px 12px", borderRadius: 6, border: "none", fontSize: 11, fontWeight: 500, cursor: "pointer",
              background: typeFilter === t ? "var(--bg4)" : "transparent",
              color: typeFilter === t ? "var(--text)" : "var(--text3)",
            }}>{t}</button>
          ))}
        </div>
      </div>

      {/* Findings */}
      {visible.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text3)" }}>
          <TrendingDown size={36} style={{ margin: "0 auto 12px", opacity: 0.2 }} />
          <p style={{ fontSize: 14, color: "var(--text2)", marginBottom: 4 }}>
            {findings.length === 0 ? "No dead code detected — great job!" : "No findings match this filter"}
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {visible.map((f, i) => <FindingCard key={i} f={f} />)}
        </div>
      )}
    </div>
  );
}
