import { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, Loader2, FileCode, ChevronDown, ChevronRight, Bot, User, Sparkles } from "lucide-react";
import { api } from "../services/api";
import type { QAResponse, QASource } from "../types";

interface Message { role: "user"|"assistant"; content: string; sources?: QASource[]; }

const SUGGESTIONS = [
  "What is the overall architecture of this project?",
  "Where is authentication or security implemented?",
  "What are the main entry points of the application?",
  "Which functions handle database operations?",
  "Are there any potential performance bottlenecks?",
];

function SourceList({ sources }: { sources: QASource[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;
  return (
    <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
      <button onClick={() => setOpen(!open)} style={{ display: "flex", alignItems: "center", gap: 5, background: "none", border: "none", color: "var(--text3)", cursor: "pointer", fontSize: 11, padding: 0 }}>
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        {sources.length} source{sources.length !== 1 ? "s" : ""}
      </button>
      {open && (
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 5 }}>
          {sources.map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 6, fontSize: 11 }}>
              <FileCode size={11} style={{ marginTop: 2, flexShrink: 0, color: "var(--accent2)" }} />
              <div>
                <span style={{ color: "var(--accent2)", fontFamily: "monospace" }}>{s.qualified_name}</span>
                <span style={{ color: "var(--text3)" }}> — {s.file_path.split(/[/\\]/).slice(-2).join("/")}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function QuestionAnswer({ repositoryId }: { repositoryId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function send(question: string) {
    if (!question.trim() || loading) return;
    setMessages(p => [...p, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    try {
      const res: QAResponse = await api.askQuestion(repositoryId, question);
      setMessages(p => [...p, { role: "assistant", content: res.answer, sources: res.sources }]);
    } catch (err: any) {
      setMessages(p => [...p, { role: "assistant", content: `⚠️ ${err?.response?.data?.detail ?? "Failed to get answer. Make sure OPENAI_API_KEY is set in .env"}` }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10, background: "var(--bg2)" }}>
        <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--accent-bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Sparkles size={14} color="var(--accent2)" />
        </div>
        <div>
          <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text)" }}>Ask AI</p>
          <p style={{ fontSize: 11, color: "var(--text3)" }}>Powered by RAG — answers grounded in your codebase</p>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
        {messages.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 40 }} className="animate-fade">
            <div style={{ width: 56, height: 56, borderRadius: 16, background: "var(--accent-bg)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
              <MessageSquare size={24} color="var(--accent2)" />
            </div>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", marginBottom: 6 }}>Ask anything about the codebase</p>
            <p style={{ fontSize: 13, color: "var(--text3)", marginBottom: 24, textAlign: "center", maxWidth: 400 }}>
              I'll search the most relevant code and explain it in plain English
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", maxWidth: 480 }}>
              {SUGGESTIONS.map(q => (
                <button key={q} onClick={() => send(q)} style={{
                  padding: "10px 14px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)",
                  background: "var(--bg3)", color: "var(--text2)", fontSize: 13, cursor: "pointer",
                  textAlign: "left", transition: "all 0.15s",
                }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--accent)"; (e.currentTarget as HTMLElement).style.color = "var(--text)"; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; (e.currentTarget as HTMLElement).style.color = "var(--text2)"; }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {messages.map((msg, i) => (
              <div key={i} style={{ display: "flex", gap: 10, justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }} className="animate-fade">
                {msg.role === "assistant" && (
                  <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--accent-bg)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 2 }}>
                    <Bot size={14} color="var(--accent2)" />
                  </div>
                )}
                <div style={{
                  maxWidth: "80%", padding: "12px 14px", borderRadius: 12,
                  background: msg.role === "user" ? "var(--accent)" : "var(--bg3)",
                  border: msg.role === "assistant" ? "1px solid var(--border)" : "none",
                  color: "var(--text)", fontSize: 13, lineHeight: 1.7,
                }}>
                  <p style={{ whiteSpace: "pre-wrap" }}>{msg.content}</p>
                  {msg.sources && <SourceList sources={msg.sources} />}
                </div>
                {msg.role === "user" && (
                  <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--bg4)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 2 }}>
                    <User size={14} color="var(--text2)" />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div style={{ display: "flex", gap: 10 }}>
                <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--accent-bg)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Bot size={14} color="var(--accent2)" />
                </div>
                <div style={{ padding: "12px 16px", borderRadius: 12, background: "var(--bg3)", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8, color: "var(--text3)", fontSize: 13 }}>
                  <Loader2 size={13} className="animate-spin" /> Searching codebase…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)", background: "var(--bg2)" }}>
        <div style={{ display: "flex", gap: 10, alignItems: "flex-end", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "8px 8px 8px 14px" }}>
          <textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKey}
            placeholder="Ask a question… (Enter to send, Shift+Enter for new line)"
            rows={1} disabled={loading}
            style={{ flex: 1, background: "none", border: "none", color: "var(--text)", fontSize: 13, resize: "none", outline: "none", lineHeight: 1.6, maxHeight: 120, overflowY: "auto" }}
          />
          <button onClick={() => send(input)} disabled={loading || !input.trim()} style={{
            width: 34, height: 34, borderRadius: 8, border: "none", flexShrink: 0,
            background: loading || !input.trim() ? "var(--bg4)" : "var(--accent)",
            color: loading || !input.trim() ? "var(--text3)" : "#fff",
            cursor: loading || !input.trim() ? "not-allowed" : "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
