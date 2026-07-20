import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GitBranch, Plus, RefreshCw, Trash2, AlertCircle, CheckCircle, Loader2, Clock, Search, Code2, Layers, Zap } from "lucide-react";
import { api } from "../services/api";
import { useRepositories } from "../hooks/useRepository";
import type { Repository } from "../types";

const STATUS_MAP: Record<Repository["status"], { label: string; color: string; bg: string }> = {
  pending:        { label: "Pending",        color: "#9ba3b4", bg: "rgba(155,163,180,0.1)" },
  cloning:        { label: "Cloning…",       color: "#60a5fa", bg: "rgba(96,165,250,0.1)" },
  parsing:        { label: "Parsing ASTs…",  color: "#60a5fa", bg: "rgba(96,165,250,0.1)" },
  building_graph: { label: "Building graph", color: "#a78bfa", bg: "rgba(167,139,250,0.1)" },
  embedding:      { label: "Embedding…",     color: "#a78bfa", bg: "rgba(167,139,250,0.1)" },
  analyzing:      { label: "Analyzing…",     color: "#6c63ff", bg: "rgba(108,99,255,0.12)" },
  ready:          { label: "Ready",          color: "#34d399", bg: "rgba(52,211,153,0.1)" },
  failed:         { label: "Failed",         color: "#f87171", bg: "rgba(248,113,113,0.1)" },
};

function StatusBadge({ status }: { status: Repository["status"] }) {
  const s = STATUS_MAP[status];
  const isSpinning = !["ready", "failed", "pending"].includes(status);
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, fontWeight: 600,
      letterSpacing: "0.03em", padding: "3px 10px", borderRadius: 20,
      color: s.color, background: s.bg,
    }}>
      {status === "ready" ? <CheckCircle size={11} /> :
       status === "failed" ? <AlertCircle size={11} /> :
       status === "pending" ? <Clock size={11} /> :
       <Loader2 size={11} className={isSpinning ? "animate-spin" : ""} />}
      {s.label}
    </span>
  );
}

function ProgressBar({ value }: { value: number }) {
  if (value <= 0 || value >= 1) return null;
  return (
    <div style={{ height: 3, background: "var(--bg4)", borderRadius: 4, marginTop: 8, overflow: "hidden" }}>
      <div style={{
        height: "100%", borderRadius: 4,
        background: "linear-gradient(90deg, var(--accent), var(--purple))",
        width: `${Math.round(value * 100)}%`,
        transition: "width 0.6s ease",
        boxShadow: "0 0 8px var(--accent)",
      }} />
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }: any) {
  return (
    <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "16px 20px", display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{ width: 36, height: 36, borderRadius: 10, background: `${color}18`, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Icon size={18} color={color} />
      </div>
      <div>
        <p style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", lineHeight: 1 }}>{value}</p>
        <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 2 }}>{label}</p>
      </div>
    </div>
  );
}

export function RepositoryList() {
  const navigate = useNavigate();
  const { repos, loading, error, refetch } = useRepositories();
  const [url, setUrl] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setAdding(true); setAddError(null);
    try {
      const repo = await api.createRepository(url.trim());
      setUrl("");
      await refetch();
      navigate(`/repo/${repo.id}`);
    } catch (err: any) {
      setAddError(err?.response?.data?.detail ?? "Failed to add repository");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("Delete this repository and all its analysis data?")) return;
    await api.deleteRepository(id).catch(() => {});
    await refetch();
  }

  const filtered = repos.filter(r =>
    !search || `${r.owner}/${r.name}`.toLowerCase().includes(search.toLowerCase())
  );
  const readyCount = repos.filter(r => r.status === "ready").length;
  const totalFiles = repos.reduce((a, r) => a + r.total_files, 0);
  const totalLines = repos.reduce((a, r) => a + r.total_lines, 0);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex" }}>
      {/* Sidebar */}
      <div style={{ width: 260, background: "var(--bg2)", borderRight: "1px solid var(--border)", padding: "24px 16px", display: "flex", flexDirection: "column", gap: 8, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", marginBottom: 16 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Code2 size={16} color="#fff" />
          </div>
          <div>
            <p style={{ fontWeight: 700, fontSize: 13, color: "var(--text)" }}>CUE</p>
            <p style={{ fontSize: 10, color: "var(--text3)" }}>v2.0</p>
          </div>
        </div>

        <p style={{ fontSize: 10, fontWeight: 600, color: "var(--text3)", letterSpacing: "0.08em", textTransform: "uppercase", padding: "0 12px", marginBottom: 4 }}>Navigation</p>
        <div style={{ padding: "8px 12px", borderRadius: "var(--radius-sm)", background: "var(--accent-bg)", color: "var(--accent2)", fontWeight: 500, fontSize: 13, display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <GitBranch size={15} /> Repositories
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "auto" }}>
        {/* Header */}
        <div style={{ borderBottom: "1px solid var(--border)", padding: "20px 32px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--bg2)" }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text)" }}>Repositories</h1>
            <p style={{ color: "var(--text3)", fontSize: 13, marginTop: 2 }}>Analyze any public GitHub repository with AI</p>
          </div>
          <button onClick={refetch} style={{ padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", background: "transparent", color: "var(--text2)", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        <div style={{ padding: "24px 32px", flex: 1 }}>
          {/* Stats */}
          {repos.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24 }}>
              <StatCard icon={GitBranch} label="repositories" value={repos.length} color="var(--accent)" />
              <StatCard icon={Layers} label="files analyzed" value={totalFiles.toLocaleString()} color="var(--green)" />
              <StatCard icon={Zap} label="lines of code" value={totalLines.toLocaleString()} color="var(--amber)" />
            </div>
          )}

          {/* Add form */}
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: 20, marginBottom: 24 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", marginBottom: 12 }}>Analyze a new repository</p>
            <form onSubmit={handleAdd} style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1, position: "relative" }}>
                <GitBranch size={15} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text3)" }} />
                <input
                  type="url" value={url}
                  onChange={e => setUrl(e.target.value)}
                  placeholder="https://github.com/owner/repository"
                  disabled={adding}
                  style={{
                    width: "100%", padding: "10px 12px 10px 36px",
                    background: "var(--bg3)", border: "1px solid var(--border)",
                    borderRadius: "var(--radius-sm)", color: "var(--text)", fontSize: 13,
                    outline: "none", transition: "border-color 0.2s",
                  }}
                  onFocus={e => e.target.style.borderColor = "var(--accent)"}
                  onBlur={e => e.target.style.borderColor = "var(--border)"}
                />
              </div>
              <button type="submit" disabled={adding || !url.trim()} style={{
                padding: "10px 20px", borderRadius: "var(--radius-sm)", border: "none",
                background: adding || !url.trim() ? "var(--bg4)" : "var(--accent)",
                color: adding || !url.trim() ? "var(--text3)" : "#fff",
                fontWeight: 600, fontSize: 13, cursor: adding || !url.trim() ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", gap: 7, transition: "all 0.2s",
              }}>
                {adding ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                {adding ? "Analyzing…" : "Analyze"}
              </button>
            </form>
            {addError && <p style={{ color: "var(--red)", fontSize: 12, marginTop: 8 }}>{addError}</p>}
          </div>

          {/* Search */}
          {repos.length > 3 && (
            <div style={{ position: "relative", marginBottom: 16 }}>
              <Search size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text3)" }} />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search repositories…"
                style={{ width: "100%", padding: "9px 12px 9px 34px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", color: "var(--text)", fontSize: 13, outline: "none" }} />
            </div>
          )}

          {/* List */}
          {loading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[1,2,3].map(i => <div key={i} className="skeleton" style={{ height: 80 }} />)}
            </div>
          ) : error ? (
            <div style={{ color: "var(--red)", fontSize: 13 }}>{error}</div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text3)" }}>
              <GitBranch size={40} style={{ margin: "0 auto 12px", opacity: 0.2 }} />
              <p style={{ fontSize: 15, color: "var(--text2)", marginBottom: 6 }}>No repositories yet</p>
              <p style={{ fontSize: 13 }}>Paste a GitHub URL above to get started</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {filtered.map(repo => (
                <div key={repo.id} onClick={() => navigate(`/repo/${repo.id}`)}
                  style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "16px 20px", cursor: "pointer", transition: "all 0.15s", position: "relative" }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border2)"; (e.currentTarget as HTMLElement).style.background = "var(--bg3)"; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; (e.currentTarget as HTMLElement).style.background = "var(--bg2)"; }}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                        <span style={{ fontWeight: 600, fontSize: 14, color: "var(--text)" }}>
                          <span style={{ color: "var(--text2)" }}>{repo.owner}/</span>{repo.name}
                        </span>
                        <StatusBadge status={repo.status} />
                      </div>
                      <p style={{ color: "var(--text3)", fontSize: 12, marginTop: 3 }} className="truncate">{repo.url}</p>
                      <ProgressBar value={repo.progress} />
                      {repo.status === "ready" && (
                        <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
                          <span style={{ fontSize: 11, color: "var(--text3)" }}>📁 {repo.total_files.toLocaleString()} files</span>
                          <span style={{ fontSize: 11, color: "var(--text3)" }}>📄 {repo.total_lines.toLocaleString()} lines</span>
                        </div>
                      )}
                      {repo.error_message && <p style={{ color: "var(--red)", fontSize: 11, marginTop: 6 }} className="truncate">{repo.error_message}</p>}
                    </div>
                    <button onClick={e => handleDelete(repo.id, e)} style={{ padding: 6, borderRadius: "var(--radius-sm)", border: "none", background: "transparent", color: "var(--text3)", cursor: "pointer", flexShrink: 0 }}
                      onMouseEnter={e => (e.currentTarget.style.color = "var(--red)")}
                      onMouseLeave={e => (e.currentTarget.style.color = "var(--text3)")}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
