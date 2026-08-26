import { useEffect, useState } from "react";
import {
  ShieldAlert, Loader2, AlertTriangle, ChevronDown, ChevronUp,
  Zap, ArrowRight, Info,
} from "lucide-react";
import { api } from "../services/api";
import type { TaintFinding } from "../types";

// Vulnerability class → colour mapping
const VULN_COLORS: Record<string, { fg: string; bg: string }> = {
  "Code Injection":             { fg: "var(--red)",   bg: "var(--red-bg)" },
  "Command Injection":          { fg: "var(--red)",   bg: "var(--red-bg)" },
  "SQL Injection":              { fg: "var(--amber)", bg: "var(--amber-bg)" },
  "Insecure Deserialization":   { fg: "var(--red)",   bg: "var(--red-bg)" },
  "SSTI":                       { fg: "var(--amber)", bg: "var(--amber-bg)" },
};

function vuln(cls: string) {
  return VULN_COLORS[cls] ?? { fg: "var(--blue)", bg: "var(--blue-bg)" };
}

function shortQn(qn: string) {
  return qn.split(".").slice(-2).join(".");
}

function Pill({ label, color, bg }: { label: string; color: string; bg: string }) {
  return (
    <span style={{
      fontSize: 10, padding: "2px 7px", borderRadius: 10, fontWeight: 600,
      color, background: bg,
    }}>{label}</span>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Single finding card
// ──────────────────────────────────────────────────────────────────────────────
function FindingCard({
  f, repositoryId,
}: { f: TaintFinding; repositoryId: string }) {
  const [open, setOpen] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [explainError, setExplainError] = useState<string | null>(null);

  const vc = vuln(f.vuln_class);
  const isHigh = f.confidence === "high";

  async function handleExplain() {
    setExplaining(true);
    setExplainError(null);
    try {
      const { explanation: text } = await api.explainTaintFinding(repositoryId, {
        source_qn: f.source_qn,
        sink_qn: f.sink_qn,
        vuln_class: f.vuln_class,
        confidence: f.confidence,
        path: f.path,
      });
      setExplanation(text);
    } catch {
      setExplainError("Failed to generate explanation — check that an LLM backend is configured.");
    } finally {
      setExplaining(false);
    }
  }

  return (
    <div style={{
      background: "var(--bg3)",
      border: `1px solid ${isHigh ? "rgba(248,113,113,0.2)" : "rgba(251,191,36,0.15)"}`,
      borderRadius: "var(--radius)", overflow: "hidden",
    }}>
      {/* Header row — always visible */}
      <div
        onClick={() => setOpen(!open)}
        style={{ padding: "12px 14px", cursor: "pointer", display: "flex", alignItems: "flex-start", gap: 10 }}
      >
        <div style={{
          width: 24, height: 24, borderRadius: 6, flexShrink: 0, marginTop: 1,
          background: vc.bg, display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <AlertTriangle size={12} color={vc.fg} />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 700, color: "var(--text)" }}>
              {shortQn(f.source_qn)}
            </span>
            <ArrowRight size={11} color="var(--text3)" />
            <span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 700, color: vc.fg }}>
              {shortQn(f.sink_qn)}
            </span>
            <Pill label={f.vuln_class} color={vc.fg} bg={vc.bg} />
            <Pill
              label={f.confidence}
              color={isHigh ? "var(--red)" : f.confidence === "medium" ? "var(--amber)" : "var(--text3)"}
              bg={isHigh ? "var(--red-bg)" : f.confidence === "medium" ? "var(--amber-bg)" : "var(--bg4)"}
            />
            {f.finding_type === "direct" && (
              <Pill label="direct" color="var(--blue)" bg="var(--blue-bg)" />
            )}
          </div>
          <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 3, fontFamily: "monospace" }}>
            {f.source_file ? f.source_file.split(/[/\\]/).slice(-3).join("/") : "—"}
            {f.source_line ? `:${f.source_line}` : ""}
          </p>
        </div>

        {open
          ? <ChevronUp size={13} color="var(--text3)" style={{ flexShrink: 0 }} />
          : <ChevronDown size={13} color="var(--text3)" style={{ flexShrink: 0 }} />}
      </div>

      {/* Expanded detail */}
      {open && (
        <div style={{ padding: "0 14px 14px 48px", borderTop: "1px solid var(--border)" }}>
          {/* Call path */}
          <div style={{ marginTop: 12 }}>
            <p style={{ fontSize: 11, color: "var(--text3)", fontWeight: 600, marginBottom: 6 }}>
              Call path ({f.path.length - 1} hop{f.path.length - 1 !== 1 ? "s" : ""})
            </p>
            <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 4 }}>
              {f.path.map((qn, i) => (
                <span key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{
                    fontFamily: "monospace", fontSize: 11,
                    color: i === 0 ? "var(--green)" : i === f.path.length - 1 ? vc.fg : "var(--text2)",
                    background: "var(--bg4)", padding: "2px 6px", borderRadius: 4,
                  }}>
                    {shortQn(qn)}
                  </span>
                  {i < f.path.length - 1 && <ArrowRight size={10} color="var(--text3)" />}
                </span>
              ))}
            </div>
          </div>

          {/* File locations */}
          <div style={{ marginTop: 10, display: "flex", gap: 16, flexWrap: "wrap" }}>
            {f.source_file && (
              <div>
                <p style={{ fontSize: 10, color: "var(--text3)", fontWeight: 600, marginBottom: 2 }}>SOURCE</p>
                <p style={{ fontSize: 11, color: "var(--green)", fontFamily: "monospace" }}>
                  {f.source_file.split(/[/\\]/).slice(-3).join("/")}:{f.source_line}
                </p>
              </div>
            )}
            {f.sink_file && (
              <div>
                <p style={{ fontSize: 10, color: "var(--text3)", fontWeight: 600, marginBottom: 2 }}>SINK</p>
                <p style={{ fontSize: 11, fontFamily: "monospace", color: vc.fg }}>
                  {f.sink_file.split(/[/\\]/).slice(-3).join("/")}:{f.sink_line}
                </p>
              </div>
            )}
          </div>

          {/* Explain button + output */}
          <div style={{ marginTop: 14 }}>
            {!explanation && (
              <button
                onClick={handleExplain}
                disabled={explaining}
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "6px 12px", borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border)", background: "transparent",
                  color: explaining ? "var(--text3)" : "var(--text2)",
                  cursor: explaining ? "not-allowed" : "pointer", fontSize: 12,
                }}
              >
                {explaining
                  ? <><Loader2 size={12} className="animate-spin" /> Generating…</>
                  : <><Zap size={12} /> Explain this finding</>}
              </button>
            )}
            {explainError && (
              <p style={{ fontSize: 12, color: "var(--red)", marginTop: 8 }}>{explainError}</p>
            )}
            {explanation && (
              <div style={{
                marginTop: 10, padding: "12px 14px", background: "var(--bg4)",
                borderRadius: "var(--radius-sm)", border: "1px solid var(--border)",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                  <Info size={12} color="var(--accent2)" />
                  <span style={{ fontSize: 11, fontWeight: 600, color: "var(--accent2)" }}>AI Security Analysis</span>
                </div>
                <p style={{ fontSize: 12, color: "var(--text2)", lineHeight: 1.65, whiteSpace: "pre-wrap" }}>
                  {explanation}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Panel
// ──────────────────────────────────────────────────────────────────────────────
export function SecurityFindingsPanel({ repositoryId }: { repositoryId: string }) {
  const [findings, setFindings] = useState<TaintFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confFilter, setConfFilter] = useState<"all" | "high" | "medium" | "low">("all");
  const [vulnFilter, setVulnFilter] = useState<string>("all");

  useEffect(() => {
    api.getTaintAnalysis(repositoryId)
      .then(d => setFindings(d.findings))
      .catch(err => setError(err?.response?.data?.detail ?? "Failed to load security findings"))
      .finally(() => setLoading(false));
  }, [repositoryId]);

  const vulnClasses = Array.from(new Set(findings.map(f => f.vuln_class)));
  const visible = findings.filter(f =>
    (confFilter === "all" || f.confidence === confFilter) &&
    (vulnFilter === "all" || f.vuln_class === vulnFilter)
  );

  const byConf = (c: string) => findings.filter(f => f.confidence === c).length;
  const byVuln = findings.reduce((a, f) => { a[f.vuln_class] = (a[f.vuln_class] || 0) + 1; return a; }, {} as Record<string, number>);

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", gap: 10, color: "var(--text3)" }}>
      <Loader2 size={18} className="animate-spin" /> Scanning for vulnerabilities…
    </div>
  );

  if (error) return (
    <div style={{ padding: 20, color: "var(--red)", fontSize: 13 }}>{error}</div>
  );

  return (
    <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ width: 34, height: 34, borderRadius: 10, background: "var(--red-bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <ShieldAlert size={16} color="var(--red)" />
        </div>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text)" }}>Security Findings</h2>
          <p style={{ fontSize: 12, color: "var(--text3)" }}>
            Taint-flow analysis — call-graph paths from untrusted sources to dangerous sinks
          </p>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
        {[
          { label: "total findings", value: findings.length, color: "var(--text2)", bg: "var(--bg3)" },
          { label: "high confidence", value: byConf("high"), color: "var(--red)", bg: "var(--red-bg)" },
          { label: "medium confidence", value: byConf("medium"), color: "var(--amber)", bg: "var(--amber-bg)" },
          { label: "vuln classes", value: vulnClasses.length, color: "var(--blue)", bg: "var(--blue-bg)" },
        ].map(({ label, value, color, bg }) => (
          <div key={label} style={{ background: bg, border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "14px 16px" }}>
            <p style={{ fontSize: 26, fontWeight: 700, color, lineHeight: 1 }}>{value}</p>
            <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 3 }}>{label}</p>
          </div>
        ))}
      </div>

      {/* Vuln class breakdown */}
      {vulnClasses.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {Object.entries(byVuln).map(([cls, count]) => {
            const vc = vuln(cls);
            return (
              <div key={cls} style={{ padding: "5px 10px", borderRadius: 8, background: vc.bg, border: `1px solid ${vc.fg}30`, fontSize: 12 }}>
                <span style={{ color: vc.fg, fontWeight: 600 }}>{cls}</span>
                <span style={{ color: "var(--text3)", marginLeft: 6 }}>{count}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 2, background: "var(--bg3)", padding: 3, borderRadius: "var(--radius-sm)" }}>
          {(["all", "high", "medium", "low"] as const).map(c => (
            <button key={c} onClick={() => setConfFilter(c)} style={{
              padding: "5px 11px", borderRadius: 6, border: "none", fontSize: 11, fontWeight: 500, cursor: "pointer",
              background: confFilter === c ? "var(--bg4)" : "transparent",
              color: confFilter === c ? "var(--text)" : "var(--text3)",
            }}>{c}</button>
          ))}
        </div>
        {vulnClasses.length > 0 && (
          <div style={{ display: "flex", gap: 2, background: "var(--bg3)", padding: 3, borderRadius: "var(--radius-sm)" }}>
            {["all", ...vulnClasses].map(v => (
              <button key={v} onClick={() => setVulnFilter(v)} style={{
                padding: "5px 11px", borderRadius: 6, border: "none", fontSize: 11, fontWeight: 500, cursor: "pointer",
                background: vulnFilter === v ? "var(--bg4)" : "transparent",
                color: vulnFilter === v ? "var(--text)" : "var(--text3)",
              }}>{v === "all" ? "all types" : v}</button>
            ))}
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div style={{ padding: "10px 14px", borderRadius: "var(--radius-sm)", background: "var(--bg3)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text3)", display: "flex", gap: 8 }}>
        <Info size={13} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>
          Call-graph level analysis — finds reachable paths from sources to sinks via CALLS edges.
          False positives are possible (tainted value may not flow to the sink at runtime).
          SQL injection sink detection uses a heuristic regex and may produce false positives.
        </span>
      </div>

      {/* Findings list */}
      {visible.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text3)" }}>
          <ShieldAlert size={36} style={{ margin: "0 auto 12px", opacity: 0.2 }} />
          <p style={{ fontSize: 14, color: "var(--text2)", marginBottom: 4 }}>
            {findings.length === 0 ? "No taint-flow paths detected" : "No findings match this filter"}
          </p>
          {findings.length === 0 && (
            <p style={{ fontSize: 12 }}>
              This may mean the repo has no Python source/sink patterns, or the call graph has no paths between them.
            </p>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {visible.map((f, i) => (
            <FindingCard key={i} f={f} repositoryId={repositoryId} />
          ))}
        </div>
      )}
    </div>
  );
}
