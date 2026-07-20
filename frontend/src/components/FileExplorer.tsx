import { useEffect, useState } from "react";
import { FolderOpen, Loader2, Search, Code2, Filter, ChevronLeft, ChevronRight, AlertTriangle } from "lucide-react";
import { api } from "../services/api";
import type { CodeElement } from "../types";

const TYPE_COLORS: Record<string, string> = {
  function: "#22d3ee", method: "#60a5fa", class: "#a78bfa",
  module: "#6c63ff", interface: "#f472b6", struct: "#c084fc",
  import: "#5c6478", variable: "#5c6478",
};

const LANG_COLORS: Record<string, string> = {
  python: "#3572A5", javascript: "#f7df1e", typescript: "#2b7489",
  java: "#b07219", go: "#00ADD8", rust: "#dea584",
};

function ElementRow({ el }: { el: CodeElement }) {
  const color = TYPE_COLORS[el.element_type] ?? "#5c6478";
  const langColor = LANG_COLORS[el.language] ?? "#5c6478";
  const filename = el.file_path.split(/[/\\]/).slice(-2).join("/");

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: "var(--radius-sm)", transition: "background 0.1s", cursor: "default" }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--bg3)"}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "transparent"}>
      <div style={{ width: 6, height: 6, borderRadius: "50%", background: color, flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text)", fontFamily: "monospace" }}>{el.name}</span>
          {el.is_dead_code && (
            <span style={{ fontSize: 9, padding: "1px 6px", borderRadius: 4, background: "var(--amber-bg)", color: "var(--amber)", fontWeight: 600, display: "flex", alignItems: "center", gap: 3 }}>
              <AlertTriangle size={8} /> dead
            </span>
          )}
        </div>
        <p style={{ fontSize: 10, color: "var(--text3)", fontFamily: "monospace", marginTop: 1 }} className="truncate">
          {filename}:{el.start_line}
        </p>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
        <span style={{ fontSize: 9, padding: "2px 7px", borderRadius: 4, background: `${color}18`, color, fontWeight: 600 }}>
          {el.element_type}
        </span>
        <span style={{ fontSize: 9, padding: "2px 7px", borderRadius: 4, background: `${langColor}18`, color: langColor, fontWeight: 600 }}>
          {el.language}
        </span>
      </div>
    </div>
  );
}

const TYPES = ["all","module","class","function","method","interface","struct","import"];
const PAGE = 100;

export function FileExplorer({ repositoryId }: { repositoryId: string }) {
  const [elements, setElements] = useState<CodeElement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [deadOnly, setDeadOnly] = useState(false);
  const [page, setPage] = useState(0);

  useEffect(() => {
    setLoading(true);
    api.listCodeElements(repositoryId, {
      element_type: typeFilter !== "all" ? typeFilter : undefined,
      dead_code_only: deadOnly || undefined,
      limit: PAGE, offset: page * PAGE,
    })
      .then(setElements)
      .catch(err => setError(err?.response?.data?.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  }, [repositoryId, typeFilter, deadOnly, page]);

  const filtered = elements.filter(el =>
    !search || el.name.toLowerCase().includes(search.toLowerCase()) ||
    el.file_path.toLowerCase().includes(search.toLowerCase())
  );

  const deadCount = elements.filter(e => e.is_dead_code).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", background: "var(--bg2)", display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--accent-bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <FolderOpen size={14} color="var(--accent2)" />
          </div>
          <div style={{ flex: 1 }}>
            <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text)" }}>Code Elements</p>
            <p style={{ fontSize: 11, color: "var(--text3)" }}>
              Page {page + 1} · {PAGE * page + 1}–{PAGE * page + elements.length} shown
              {deadCount > 0 && <span style={{ color: "var(--amber)", marginLeft: 8 }}>· {deadCount} dead</span>}
            </p>
          </div>
        </div>

        {/* Search */}
        <div style={{ position: "relative" }}>
          <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text3)" }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by name or file…"
            style={{ width: "100%", padding: "8px 10px 8px 30px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", color: "var(--text)", fontSize: 12, outline: "none" }} />
        </div>

        {/* Type filter */}
        <div style={{ display: "flex", gap: 4, overflowX: "auto", paddingBottom: 2 }}>
          {TYPES.map(t => (
            <button key={t} onClick={() => { setTypeFilter(t); setPage(0); }} style={{
              padding: "4px 10px", borderRadius: 6, border: "none", fontSize: 11, fontWeight: 500, cursor: "pointer", whiteSpace: "nowrap",
              background: typeFilter === t ? "var(--accent)" : "var(--bg4)",
              color: typeFilter === t ? "#fff" : "var(--text3)",
            }}>{t}</button>
          ))}
          <button onClick={() => { setDeadOnly(!deadOnly); setPage(0); }} style={{
            padding: "4px 10px", borderRadius: 6, border: "none", fontSize: 11, fontWeight: 500, cursor: "pointer", whiteSpace: "nowrap",
            background: deadOnly ? "var(--amber-bg)" : "var(--bg4)",
            color: deadOnly ? "var(--amber)" : "var(--text3)",
            marginLeft: "auto",
          }}>
            <AlertTriangle size={9} style={{ display: "inline", marginRight: 4 }} />dead only
          </button>
        </div>
      </div>

      {/* List */}
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 8px" }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 40, gap: 8, color: "var(--text3)" }}>
            <Loader2 size={14} className="animate-spin" /> Loading…
          </div>
        ) : error ? (
          <div style={{ padding: 16, color: "var(--red)", fontSize: 13 }}>{error}</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text3)", fontSize: 13 }}>No elements found</div>
        ) : (
          filtered.map(el => <ElementRow key={el.id} el={el} />)
        )}
      </div>

      {/* Pagination */}
      <div style={{ padding: "10px 16px", borderTop: "1px solid var(--border)", background: "var(--bg2)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} style={{ display: "flex", alignItems: "center", gap: 5, padding: "5px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "transparent", color: page === 0 ? "var(--text3)" : "var(--text2)", cursor: page === 0 ? "not-allowed" : "pointer", fontSize: 12 }}>
          <ChevronLeft size={13} /> Previous
        </button>
        <span style={{ fontSize: 11, color: "var(--text3)" }}>Page {page + 1}</span>
        <button onClick={() => setPage(p => p + 1)} disabled={elements.length < PAGE} style={{ display: "flex", alignItems: "center", gap: 5, padding: "5px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "transparent", color: elements.length < PAGE ? "var(--text3)" : "var(--text2)", cursor: elements.length < PAGE ? "not-allowed" : "pointer", fontSize: 12 }}>
          Next <ChevronRight size={13} />
        </button>
      </div>
    </div>
  );
}
