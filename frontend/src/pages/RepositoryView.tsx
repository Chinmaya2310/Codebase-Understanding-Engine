import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, GitBranch, Network, Layers, ShieldOff, FolderOpen, MessageSquare, RotateCcw, Loader2, AlertCircle, CheckCircle, Clock, FileCode2, Zap } from "lucide-react";
import { useRepositoryPolling } from "../hooks/useRepository";
import { api } from "../services/api";
import { CodeGraph } from "../components/CodeGraph";
import { ArchitectureDiagram } from "../components/ArchitectureDiagram";
import { DeadCodePanel } from "../components/DeadCodePanel";
import { FileExplorer } from "../components/FileExplorer";
import { QuestionAnswer } from "../components/QuestionAnswer";
import type { Repository } from "../types";

type Tab = "graph"|"architecture"|"deadcode"|"elements"|"qa";

const TABS: { id: Tab; label: string; icon: typeof Network; desc: string }[] = [
  { id: "graph",        label: "Code Graph",    icon: Network,       desc: "Interactive relationship graph" },
  { id: "architecture", label: "Architecture",  icon: Layers,        desc: "Patterns & diagrams" },
  { id: "deadcode",     label: "Dead Code",      icon: ShieldOff,     desc: "Unreferenced elements" },
  { id: "elements",     label: "Elements",       icon: FolderOpen,    desc: "Browse all code" },
  { id: "qa",           label: "Ask AI",         icon: MessageSquare, desc: "Natural language Q&A" },
];

const STATUS_STEPS = ["cloning","parsing","building_graph","embedding","analyzing","ready"] as const;

function ProgressStepper({ status, progress }: { status: Repository["status"]; progress: number }) {
  const currentIndex = STATUS_STEPS.indexOf(status as any);
  const labels: Record<string, string> = {
    cloning: "Clone", parsing: "Parse", building_graph: "Graph",
    embedding: "Embed", analyzing: "Analyze", ready: "Done"
  };
  return (
    <div style={{ padding: "16px 32px", background: "var(--bg2)", borderBottom: "1px solid var(--border)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 10 }}>
        {STATUS_STEPS.map((step, i) => {
          const done = currentIndex > i || status === "ready";
          const active = STATUS_STEPS[currentIndex] === step && status !== "ready";
          return (
            <div key={step} style={{ display: "flex", alignItems: "center", flex: i < STATUS_STEPS.length - 1 ? 1 : "none" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700,
                  background: done ? "var(--green)" : active ? "var(--accent)" : "var(--bg4)",
                  color: done || active ? "#fff" : "var(--text3)",
                  border: active ? "2px solid var(--accent2)" : "none",
                  boxShadow: active ? "0 0 12px var(--accent)" : "none",
                  transition: "all 0.3s",
                }}>
                  {done ? <CheckCircle size={13} /> : active ? <Loader2 size={13} className="animate-spin" /> : i + 1}
                </div>
                <span style={{ fontSize: 9, color: done ? "var(--green)" : active ? "var(--accent2)" : "var(--text3)", fontWeight: 500 }}>
                  {labels[step]}
                </span>
              </div>
              {i < STATUS_STEPS.length - 1 && (
                <div style={{ flex: 1, height: 2, margin: "0 4px", marginBottom: 16, borderRadius: 2, background: done ? "var(--green)" : "var(--bg4)", transition: "background 0.5s" }} />
              )}
            </div>
          );
        })}
      </div>
      <div style={{ height: 4, background: "var(--bg4)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", borderRadius: 4, background: "linear-gradient(90deg, var(--accent), var(--green))", width: `${Math.round(progress * 100)}%`, transition: "width 0.8s ease", boxShadow: "0 0 10px var(--accent)" }} />
      </div>
    </div>
  );
}

export function RepositoryView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { repo, error } = useRepositoryPolling(id ?? null);
  const [activeTab, setActiveTab] = useState<Tab>("graph");
  const [reanalyzing, setReanalyzing] = useState(false);

  if (!id) return null;

  if (!repo && !error) return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", alignItems: "center", justifyContent: "center", gap: 10, color: "var(--text3)" }}>
      <Loader2 size={20} className="animate-spin" /> Loading repository…
    </div>
  );

  if (error) return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", alignItems: "center", justifyContent: "center", gap: 10, color: "var(--red)" }}>
      <AlertCircle size={18} /> {error}
    </div>
  );

  const isReady = repo!.status === "ready";
  const isFailed = repo!.status === "failed";
  const isWorking = !isReady && !isFailed;

  async function handleReanalyze() {
    if (!id || reanalyzing) return;
    setReanalyzing(true);
    await api.reanalyzeRepository(id).catch(() => {});
    setReanalyzing(false);
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
      {/* Top bar */}
      <header style={{ borderBottom: "1px solid var(--border)", padding: "0 24px", display: "flex", alignItems: "center", gap: 12, background: "var(--bg2)", height: 56, flexShrink: 0 }}>
        <button onClick={() => navigate("/")} style={{ width: 30, height: 30, borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text2)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <ArrowLeft size={14} />
        </button>

        <div style={{ width: 1, height: 20, background: "var(--border)" }} />

        <GitBranch size={14} color="var(--accent2)" />
        <div style={{ minWidth: 0 }}>
          <span style={{ fontWeight: 600, fontSize: 14, color: "var(--text)" }}>
            <span style={{ color: "var(--text3)" }}>{repo!.owner}/</span>{repo!.name}
          </span>
        </div>

        {/* Status pill */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", borderRadius: 20, background: isReady ? "var(--green-bg)" : isFailed ? "var(--red-bg)" : "var(--accent-bg)" }}>
          {isReady ? <CheckCircle size={11} color="var(--green)" /> :
           isFailed ? <AlertCircle size={11} color="var(--red)" /> :
           <Loader2 size={11} color="var(--accent2)" className="animate-spin" />}
          <span style={{ fontSize: 11, fontWeight: 600, color: isReady ? "var(--green)" : isFailed ? "var(--red)" : "var(--accent2)" }}>
            {isReady ? "Ready" : isFailed ? "Failed" : repo!.status.replace("_", " ")}
          </span>
        </div>

        {/* Stats */}
        {isReady && (
          <div style={{ display: "flex", gap: 16, marginLeft: 8 }}>
            <span style={{ fontSize: 11, color: "var(--text3)", display: "flex", alignItems: "center", gap: 4 }}>
              <FileCode2 size={11} /> {repo!.total_files.toLocaleString()} files
            </span>
            <span style={{ fontSize: 11, color: "var(--text3)", display: "flex", alignItems: "center", gap: 4 }}>
              <Zap size={11} /> {repo!.total_lines.toLocaleString()} lines
            </span>
          </div>
        )}

        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <button onClick={handleReanalyze} disabled={reanalyzing || isWorking} style={{ display: "flex", alignItems: "center", gap: 5, padding: "6px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", background: "transparent", color: reanalyzing || isWorking ? "var(--text3)" : "var(--text2)", cursor: reanalyzing || isWorking ? "not-allowed" : "pointer", fontSize: 12 }}>
            <RotateCcw size={12} className={reanalyzing ? "animate-spin" : ""} /> Re-analyze
          </button>
        </div>
      </header>

      {/* Progress stepper */}
      {isWorking && <ProgressStepper status={repo!.status} progress={repo!.progress} />}

      {/* Error banner */}
      {isFailed && (
        <div style={{ margin: "16px 24px 0", background: "var(--red-bg)", border: "1px solid rgba(248,113,113,0.3)", borderRadius: "var(--radius)", padding: "12px 16px", display: "flex", alignItems: "flex-start", gap: 10 }}>
          <AlertCircle size={15} color="var(--red)" style={{ flexShrink: 0, marginTop: 1 }} />
          <div>
            <p style={{ color: "var(--red)", fontWeight: 600, fontSize: 13 }}>Analysis failed</p>
            <p style={{ color: "rgba(248,113,113,0.7)", fontSize: 12, marginTop: 2 }}>{repo!.error_message ?? "Unknown error"}</p>
          </div>
        </div>
      )}

      {/* Waiting state */}
      {isWorking && (
        <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, color: "var(--text3)", padding: 40 }}>
          <div style={{ width: 64, height: 64, borderRadius: 20, background: "var(--accent-bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Clock size={28} color="var(--accent2)" className="animate-pulse" />
          </div>
          <div style={{ textAlign: "center" }}>
            <p style={{ fontSize: 16, fontWeight: 600, color: "var(--text2)", marginBottom: 6 }}>Analysis in progress</p>
            <p style={{ fontSize: 13 }}>This takes 3–10 minutes for most repositories</p>
            <p style={{ fontSize: 12, marginTop: 4 }}>{Math.round(repo!.progress * 100)}% complete</p>
          </div>
        </div>
      )}

      {/* Ready: tab bar + content */}
      {isReady && (
        <>
          {/* Sidebar + content layout */}
          <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
            {/* Sidebar tabs */}
            <div style={{ width: 200, background: "var(--bg2)", borderRight: "1px solid var(--border)", padding: "12px 8px", display: "flex", flexDirection: "column", gap: 2, flexShrink: 0 }}>
              {TABS.map(tab => {
                const Icon = tab.icon;
                const active = activeTab === tab.id;
                return (
                  <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                    padding: "10px 12px", borderRadius: "var(--radius-sm)", border: "none", cursor: "pointer",
                    background: active ? "var(--accent-bg)" : "transparent",
                    color: active ? "var(--accent2)" : "var(--text3)",
                    textAlign: "left", display: "flex", alignItems: "center", gap: 10,
                    transition: "all 0.15s",
                    borderLeft: active ? "2px solid var(--accent)" : "2px solid transparent",
                  }}
                    onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "var(--bg3)"; }}
                    onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "transparent"; }}>
                    <Icon size={15} />
                    <div>
                      <p style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.2 }}>{tab.label}</p>
                      <p style={{ fontSize: 10, opacity: 0.6, marginTop: 1, lineHeight: 1 }}>{tab.desc}</p>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Tab content */}
            <main style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
              {activeTab === "graph"        && <CodeGraph repositoryId={id} />}
              {activeTab === "architecture" && <ArchitectureDiagram repositoryId={id} />}
              {activeTab === "deadcode"     && <DeadCodePanel repositoryId={id} />}
              {activeTab === "elements"     && <FileExplorer repositoryId={id} />}
              {activeTab === "qa"           && <QuestionAnswer repositoryId={id} />}
            </main>
          </div>
        </>
      )}
    </div>
  );
}
