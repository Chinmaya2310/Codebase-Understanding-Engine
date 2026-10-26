<div align="center">

<br/>

<img src="https://img.shields.io/badge/CUE-v2.0-6c63ff?style=for-the-badge&logoColor=white" />

# Codebase Understanding Engine

### AI-powered code intelligence — explore, analyze and query any GitHub repository

<br/>

[![Python](https://img.shields.io/badge/Python-3.12+-3572A5?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61dafb?style=flat-square&logo=react&logoColor=black)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178c6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3-ee4c2c?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+pgvector-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-22d399?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-6c63ff?style=flat-square)](#-contributing)

<br/>

> **Paste a GitHub URL. Understand the entire codebase in minutes.**

<br/>

[🚀 Quick Start](#-quick-start) &nbsp;&nbsp;·&nbsp;&nbsp;
[🐛 Report Bug](https://github.com/Chinmaya2310/Codebase-Understanding-Engine/issues) &nbsp;&nbsp;·&nbsp;&nbsp;
[💡 Request Feature](https://github.com/Chinmaya2310/Codebase-Understanding-Engine/issues)

<br/>

</div>

---

## 📸 Screenshots

<table>
<tr>
<td width="50%">

**Dashboard — Repository List**
```
┌─────────────────────────────────────┐
│ CUE v2.0   Repositories  [Refresh]  │
├─────────────────────────────────────┤
│  1          1,133       113,785     │
│  repos    files        lines        │
├─────────────────────────────────────┤
│ [🔗 https://github.com/...] [+Analyze]│
├─────────────────────────────────────┤
│ tiangolo/fastapi  ● Ready   [🗑]    │
│ ████████████████████████████ 100%   │
│ 📁 1,133 files  ⚡ 113,785 lines    │
└─────────────────────────────────────┘
```

</td>
<td width="50%">

**Analysis — Progress Stepper**
```
┌─────────────────────────────────────┐
│ ← tiangolo/fastapi  ● Embedding     │
├─────────────────────────────────────┤
│ ✓──────✓──────✓──────⟳──── 5 ── 6  │
│Clone  Parse  Graph  Embed  Analyze Done│
│ █████████████████████░░░░░ 65%      │
├─────────────────────────────────────┤
│       ⏱ Analysis in progress        │
│   This takes 3–10 mins for most     │
│           repos  65% complete       │
└─────────────────────────────────────┘
```

</td>
</tr>
<tr>
<td width="50%">

**Code Graph — D3.js Force-Directed**
```
┌─────────────────────────────────────┐
│ 📡 Code Graph  2,847 nodes · 8,421 │
│ [+] [-] [⤢]    ■function ■class    │
├─────────────────────────────────────┤
│                                     │
│    ●─────●                          │
│   /│\   /│\   Force-directed        │
│  ● ● ● ● ● ●  graph with           │
│   \│/   \│/   drag, zoom           │
│    ●─────●    & click inspect      │
│                                     │
└─────────────────────────────────────┘
```

</td>
<td width="50%">

**Ask AI — RAG-Powered Chat**
```
┌─────────────────────────────────────┐
│ ✨ Ask AI  Powered by RAG           │
├─────────────────────────────────────┤
│ 🤖 Ask anything about the codebase │
│                                     │
│ [Where is authentication handled?]  │
│ [What does this project do?]        │
│ [Which functions handle DB ops?]    │
├─────────────────────────────────────┤
│ 🤖 Authentication is handled in    │
│    security.py via OAuth2...        │
│    ▶ 3 sources                     │
├─────────────────────────────────────┤
│ [Ask a question...          ] [▶]  │
└─────────────────────────────────────┘
```

</td>
</tr>
</table>

---

## 🎯 What Does CUE Do?

CUE ingests any public GitHub repository and transforms it into an interactive knowledge base. In one click you get:

| Feature | What you see |
|---------|-------------|
| **🔍 Code Graph** | Interactive force-directed visualization of every function, class and module — drag nodes, zoom in, click to inspect |
| **🏗️ Architecture** | Auto-generated Mermaid.js diagrams revealing MVC, Layered, or Microservices patterns |
| **🛡️ Dead Code** | Functions and classes with zero detected callers, ranked by confidence |
| **🔐 Security** | Taint-flow findings from user-input sources to dangerous sinks, with call paths and an on-demand LLM explanation |
| **📁 Code Explorer** | Searchable, filterable, paginated browser of every parsed element |
| **💬 Ask AI** | Natural-language Q&A grounded in the actual code — "Where is auth?" gets you exact file:line answers |

---

## ⚙️ How It Works — The Full Pipeline

```
GitHub URL
    │
    ▼  git clone --depth 1
┌─────────────────┐
│  Repository     │  Shallow clone → size validation → file enumeration
│  Service        │
└────────┬────────┘
         │
    ▼  8 parallel threads
┌─────────────────┐
│  AST Parsers    │  tree-sitter → Python · JavaScript · TypeScript · Java · Go
│  (tree-sitter)  │  Extracts: modules, classes, functions, methods, imports, calls
└────────┬────────┘
         │
    ▼  NetworkX MultiDiGraph
┌─────────────────┐
│  Graph Builder  │  Nodes: code elements
│  (NetworkX)     │  Edges: CONTAINS · CALLS · IMPORTS
│                 │  Python calls resolved by receiver (Klass.m, self.m, module.f);
│                 │  JS/Java/Go calls matched by name
└────────┬────────┘
         │
    ▼  all-MiniLM-L6-v2 · batch=16 · chunks of 50
┌─────────────────┐
│  Embeddings     │  384-dim vectors per element → stored in pgvector
│  (sentence-     │  Enables cosine similarity search for RAG Q&A
│   transformers) │
└────────┬────────┘
         │
    ▼  graph_nodes / graph_edges tables
┌─────────────────┐
│  Persist graph  │
└────────┬────────┘
         │
    ▼  Analyses (run one after another)
┌─────────────────┐
│  Architecture   │  Directory-name signals → layered / MVC / microservices
│  Diagrams       │  Mermaid.js dependency + architecture diagrams, D3.js graph JSON
│  Dead code      │  Zero incoming CALLS/IMPORTS edges, entry-point names skipped
└────────┬────────┘
         │
    ▼  isolated: a failure here does not fail the run
┌─────────────────┐
│  Taint analysis │  Python sources → sinks, BFS over CALLS edges (≤ 6 hops)
└────────┬────────┘
         │
         ▼  PostgreSQL JSONB
    AnalysisResult rows → status = READY ✅

All 7 steps run in one FastAPI background task; the UI polls status/progress every 3 s.
```

---

## 🧠 Machine Learning

### Text Embeddings — sentence-transformers

Every code element (function, class, method) is converted to a 384-dimensional vector using `sentence-transformers/all-MiniLM-L6-v2`. The embedding captures both the element's name AND its docstring, signature, and source code.

```python
# What gets embedded:
"function: authenticate_user
 def authenticate_user(username: str, password: str) -> User
 Verify user credentials against the database.
 def authenticate_user(username, password):
     user = db.query(User).filter_by(username=username)..."
```

These vectors are stored in PostgreSQL using the **pgvector** extension. When a user asks a question, the question is embedded the same way and pgvector finds the 8 most semantically similar code elements using cosine distance (`<=>` operator) — this is the **retrieval** step of RAG.

### Graph Neural Network — CodeGNN (PyTorch, experimental)

> **Status: experimental — not yet wired into the analysis pipeline.** The model and training loop
> exist in `backend/ml/gnn/`, but the pipeline currently uses the raw sentence-transformer embeddings.

CUE includes a custom 2-layer **Graph Convolutional Network** built from scratch in PyTorch (no torch-geometric dependency). It refines text embeddings by incorporating graph structure:

```
Text embeddings (N × 384)   +   Adjacency matrix (N × N)
                    │
                    ▼
        D⁻¹/²(A+I)D⁻¹/²  (symmetric normalisation)
                    │
                    ▼
        GCNLayer: 384 → 256  (ReLU + dropout)
                    │
                    ▼
        GCNLayer: 256 → 128  (ReLU)
                    │
                    ▼
        L2 normalise → Structure-aware embeddings (N × 128)
```

After training (self-supervised, contrastive link-prediction — no labels needed), a function's embedding encodes not just its code, but also *who calls it* and *what it calls*.

### RAG Q&A — Retrieval-Augmented Generation

```
Question → embed → pgvector top-8 → LLM context → LLM → answer + citations
```

LLM selection: OpenAI (`gpt-4o-mini`) if `OPENAI_API_KEY` is set, otherwise Groq if `GROQ_API_KEY` is set, otherwise a local `distilgpt2` fallback.

The LLM is instructed to answer using **only** the retrieved code context, to reduce hallucination. Every answer includes source citations (file path + qualified name + element type).

---

## 🏗️ Architecture

```
┌─────────────────────── Browser ───────────────────────┐
│                                                       │
│   React 18 + TypeScript + Vite 5                      │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│   │Dashboard │ │ CodeGraph│ │  Ask AI  │  ...6 tabs  │
│   │(repos)   │ │ (D3.js)  │ │  (chat)  │             │
│   └──────────┘ └──────────┘ └──────────┘             │
│          Axios HTTP client → /api/*                   │
└───────────────────────┬───────────────────────────────┘
                        │ Vite dev proxy
┌───────────────────────▼───────────────────────────────┐
│                  FastAPI :8080                         │
│                                                       │
│  Routes → Services → Background Pipeline              │
│     │                      │                          │
│  Pydantic v2            7 steps:                      │
│  JWT scaffold           clone→parse→graph→embed       │
│  In-memory rate limit   →persist→analyze→taint        │
│                                                       │
│  ML Layer:                                            │
│  ┌─────────────────┐  ┌─────────────────────┐        │
│  │ sentence-trans  │  │  CodeGNN (PyTorch)  │        │
│  │ 384-dim embeds  │  │  experimental       │        │
│  └─────────────────┘  └─────────────────────┘        │
└───────────────────────┬───────────────────────────────┘
              ┌────────┴────────┐
              ▼                 ▼
        PostgreSQL 15        pgvector
        (5 tables)        (cosine search)
```

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Role |
|-----------|---------|------|
| Python | 3.12+ | Core language |
| FastAPI | 0.111+ | Async REST API |
| SQLAlchemy | 2.0+ | Async ORM |
| asyncpg | 0.29+ | PostgreSQL async driver |
| pgvector | 0.2.5+ | Vector similarity in PostgreSQL |
| PyTorch | 2.3+ | GCN model (CodeGNN, experimental) |
| sentence-transformers | 3.0+ | Code element embeddings |
| tree-sitter | 0.22+ | AST parsing (all languages) |
| NetworkX | 3.3+ | Graph construction & algorithms |
| OpenAI / Groq | 1.30+ / 0.9+ | LLM for Q&A and finding explanations (local distilgpt2 fallback) |
| Pydantic | 2.7+ | Validation & settings |

### Frontend
| Technology | Version | Role |
|-----------|---------|------|
| React | 18.3 | UI framework |
| TypeScript | 5.4 | Type safety |
| Vite | 5.4 | Build tool & dev server |
| D3.js | 7.9 | Force-directed code graph |
| Mermaid.js | 11.0 | Architecture diagrams |
| Axios | 1.7 | Typed HTTP client |
| React Router | 6.23 | Client-side routing |
| Lucide React | 0.383 | Icon system |

### Infrastructure
| Technology | Role |
|-----------|------|
| PostgreSQL 15 | Primary database |
| pgvector extension | 384-dim cosine similarity search |
| Docker | Local development containers |

---

## 📁 Project Structure

```
cue2/
├── .env                          ← Environment variables (never commit)
├── pytest.ini                    ← Test configuration
│
├── backend/
│   ├── api/
│   │   ├── main.py               ← FastAPI app factory
│   │   ├── schemas.py            ← Pydantic request/response models
│   │   └── routes/
│   │       ├── repositories.py   ← CRUD + pipeline trigger
│   │       ├── analysis.py       ← Architecture, dead code, elements
│   │       ├── diagrams.py       ← Mermaid + D3 graph data
│   │       └── questions.py      ← RAG Q&A endpoint
│   │
│   ├── core/
│   │   ├── config.py             ← Settings (pydantic-settings + .env)
│   │   └── security.py           ← JWT scaffold + in-memory rate limiter
│   │
│   ├── db/
│   │   └── database.py           ← Async engine (pool=5, Windows-safe)
│   │
│   ├── models/
│   │   ├── repository.py         ← Repository + RepositoryStatus enum
│   │   ├── code_element.py       ← CodeElement + Vector(384) column
│   │   ├── graph_node.py         ← GraphNode + GraphEdge + EdgeType
│   │   └── analysis.py           ← AnalysisResult (JSONB)
│   │
│   ├── parsers/
│   │   ├── base_parser.py        ← Abstract BaseParser + ParsedElement
│   │   ├── python_parser.py      ← Python tree-sitter walker
│   │   ├── javascript_parser.py  ← JS/TS tree-sitter walker
│   │   ├── java_parser.py        ← Java tree-sitter walker
│   │   └── go_parser.py          ← Go tree-sitter walker
│   │
│   ├── services/
│   │   ├── analysis_pipeline.py  ← 8-step orchestrator (chunked)
│   │   ├── repository_service.py ← git clone + file enumeration
│   │   ├── parser_service.py     ← 8-thread parse dispatch
│   │   ├── graph_service.py      ← NetworkX build + DB persistence
│   │   ├── embedding_service.py  ← sentence-transformers (batch=16)
│   │   ├── llm_service.py        ← OpenAI + fallback + retry
│   │   ├── question_answering_service.py ← RAG pipeline
│   │   ├── dead_code_service.py  ← Zero-incoming-reference detection
│   │   └── diagram_service.py    ← Mermaid + D3 + arch detection
│   │
│   ├── ml/
│   │   ├── gnn/                  ← experimental, not called by the pipeline
│   │   │   ├── layers.py         ← GCNLayer (D⁻¹/²(A+I)D⁻¹/²HW)
│   │   │   ├── model.py          ← CodeGNN (384→256→128)
│   │   │   ├── dataset.py        ← Graph → tensors converter
│   │   │   └── trainer.py        ← Contrastive link-prediction
│   │   └── embeddings/
│   │       └── encoder.py        ← Shared EmbeddingService singleton
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── RepositoryList.tsx    ← Dashboard with stats + add form
│   │   │   ├── CodeGraph.tsx         ← D3 force graph (zoom/drag/click)
│   │   │   ├── ArchitectureDiagram.tsx ← Mermaid + layer stats
│   │   │   ├── DeadCodePanel.tsx     ← Expandable findings list
│   │   │   ├── FileExplorer.tsx      ← Paginated element browser
│   │   │   └── QuestionAnswer.tsx    ← Chat UI + RAG citations
│   │   ├── pages/
│   │   │   └── RepositoryView.tsx    ← 6-step stepper + sidebar tabs
│   │   ├── hooks/useRepository.ts    ← Polling + list hooks
│   │   ├── services/api.ts           ← Typed Axios client
│   │   └── types/index.ts            ← Shared TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
│
└── tests/
    ├── test_taint_analysis.py                ← 19 tests (taint sources, sinks, interprocedural flows)
    └── test_call_resolution_and_sql_sink.py  ← 15 tests (receiver-aware call resolution, AST SQL sinks)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Git 2.30+
- Docker Desktop

### 1. Clone the repository

```bash
git clone https://github.com/Chinmaya2310/Codebase-Understanding-Engine.git
cd Codebase-Understanding-Engine
```

### 2. Start the database with Docker

```bash
# PostgreSQL with pgvector
docker run -d --name cue-postgres \
  -e POSTGRES_DB=codebase_engine \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5433:5432 \
  pgvector/pgvector:0.7.0-pg15
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/codebase_engine
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5433/codebase_engine
SECRET_KEY=your-secret-key-here  # python -c "import secrets; print(secrets.token_hex(32))"
OPENAI_API_KEY=sk-...            # optional — needed for Ask AI
CLONE_BASE_PATH=C:/tmp/cue_repos  # Windows: use forward slashes
```

### 4. Set up Python backend

```bash
# Create virtual environment
python -m venv backend/.venv

# Activate (Windows)
backend\.venv\Scripts\activate.bat
# Activate (macOS/Linux)
source backend/.venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start the backend
uvicorn backend.api.main:app --reload --port 8080
```

Visit `http://localhost:8080/docs` to verify the API is running.

### 5. Set up React frontend

```bash
cd frontend
npm install
npm run dev
```

### 6. Open the app

Navigate to **http://localhost:5174**

Paste any public GitHub URL and click **Analyze** 🎉

---

## 🌐 Deployment

There is no public deployment yet — CUE currently runs locally (see Quick Start).
A free-tier setup that fits the stack:

| Service | Hosts | Free limit |
|---------|-------|-----------|
| **Vercel** | React frontend | Unlimited |
| **Render.com** | FastAPI backend | 512 MB RAM |
| **Neon.tech** | PostgreSQL + pgvector | 512 MB storage |

---

## 📡 API Reference

Interactive API docs available at `/docs` (Swagger UI) and `/redoc`.

### Core Endpoints

```
POST   /api/repositories              Submit a GitHub URL for analysis
GET    /api/repositories              List all repositories
GET    /api/repositories/{id}         Get status + progress (poll for updates)
DELETE /api/repositories/{id}         Delete repository + all data
POST   /api/repositories/{id}/reanalyze  Re-run analysis
```

### Analysis Endpoints

```
GET    /api/repositories/{id}/architecture   Detected pattern + layers
GET    /api/repositories/{id}/dead-code      Dead code findings
GET    /api/repositories/{id}/diagrams       Mermaid + D3 graph data
GET    /api/repositories/{id}/elements       Paginated code elements
POST   /api/repositories/{id}/ask           RAG Q&A
```

### Example — Add a repository

```bash
curl -X POST http://localhost:8080/api/repositories \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/tiangolo/fastapi"}'
```

Response:
```json
{
  "id": "927cd802-04fd-4beb-b6b8-c3006c94dd09",
  "owner": "tiangolo",
  "name": "fastapi",
  "status": "pending",
  "progress": 0.0
}
```

### Example — Ask a question

```bash
curl -X POST http://localhost:8080/api/repositories/927cd802.../ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Where is authentication implemented?", "top_k": 8}'
```

Response:
```json
{
  "answer": "Authentication is implemented in fastapi/security.py via OAuth2PasswordBearer (line 34). The HTTPBearer class at line 89 handles token extraction...",
  "sources": [
    {
      "file_path": "fastapi/security/oauth2.py",
      "qualified_name": "security.OAuth2PasswordBearer",
      "element_type": "class"
    }
  ]
}
```

---

## 🧪 Testing

```bash
# Run all 34 tests
python -m pytest -v

# Run specific test files
python -m pytest tests/test_taint_analysis.py -v                # Taint analysis
python -m pytest tests/test_call_resolution_and_sql_sink.py -v  # Call resolution + SQL sinks

# Run with coverage
pip install pytest-cov
python -m pytest --cov=backend --cov-report=term-missing
```

**Test results:**
```
tests/test_taint_analysis.py               ................... 19 passed
tests/test_call_resolution_and_sql_sink.py ............... 15 passed
─────────────────────────────────────────────────
34 passed in 0.62s
```

No external services required — tests run on in-memory graphs, with no database or LLM.
Test coverage currently focuses on the security analysis; the parsers, dead-code detection and Q&A are not yet covered by automated tests.

---

## 🌍 Supported Languages

| Language | Extensions | Extracts |
|---------|-----------|---------|
| **Python** | `.py` | Modules, classes, functions, methods, imports, calls, docstrings |
| **JavaScript** | `.js` `.jsx` `.mjs` | Modules, classes, functions, methods, imports |
| **TypeScript** | `.ts` `.tsx` | Same as JavaScript |
| **Java** | `.java` | Classes, interfaces, methods, imports |
| **Go** | `.go` | Structs, interfaces, functions, methods, imports |

---

## 🗺️ Roadmap

- [ ] **Rust support** — tree-sitter-rust parser
- [ ] **C/C++ support** — tree-sitter-c / tree-sitter-cpp
- [ ] **GitHub OAuth** — analyze private repositories
- [ ] **Diff analysis** — analyze only changed files in a PR
- [ ] **Export** — download analysis as JSON / PDF report
- [ ] **Compare** — diff two repositories side by side
- [ ] **Webhooks** — auto-re-analyze on push
- [ ] **VS Code extension** — view CUE analysis inside the editor

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/rust-parser`
3. **Make** your changes with tests
4. **Run** the test suite: `python -m pytest -v`
5. **Push** and open a **Pull Request**

### Adding a New Language Parser

```python
# 1. Install the grammar
pip install tree-sitter-rust

# 2. Create backend/parsers/rust_parser.py
import tree_sitter_rust as tsrust
from tree_sitter import Language
from backend.parsers.base_parser import BaseParser, ParseResult
from tree_sitter import Node
from typing import Optional

class RustParser(BaseParser):
    language_name = "rust"
    file_extensions = (".rs",)

    def _load_language(self) -> Language:
        return Language(tsrust.language())

    def _walk(self, node: Node, source: bytes,
              result: ParseResult, parent_qn: Optional[str]) -> None:
        # Walk the AST and emit ParsedElement objects
        ...

# 3. Register in backend/services/parser_service.py
from backend.parsers.rust_parser import RustParser
self._parsers["rust"] = RustParser()

# 4. Add tests in tests/test_parsers.py
```

### Code Style

- Python: type hints on all public functions, docstrings on all classes
- TypeScript: strict interfaces for all props and API responses
- Tests: every new feature must have unit tests, no real API calls in tests

---

## 📊 Database Schema

```
repositories          code_elements              graph_nodes
─────────────         ─────────────              ───────────
id (UUID PK)    1──N  id (UUID PK)         1──N  id (UUID PK)
url                   repository_id (FK)         repository_id (FK)
owner                 element_type (enum)        code_element_id (FK)
name                  name                       label
status (enum)         qualified_name             node_type
progress              file_path            1──N  graph_edges
error_message         language                   ──────────
total_files           start_line                 id (UUID PK)
total_lines           end_line                   source_id (FK)
created_at            source_code                target_id (FK)
updated_at            docstring                  edge_type (enum)
                      signature
                      embedding (vector 384) ← pgvector
                      is_dead_code
```

---

## 🔐 Taint-Flow Security Analysis

CUE includes a **call-graph-level taint analysis** engine that traces paths from untrusted input sources to dangerous sinks, surfaced in the **Security** tab.

### How it works

1. After the call graph is built, the pipeline runs `TaintAnalysisService.run()`.
2. It matches every function's source code against **source patterns** (HTTP request params, `input()`, `sys.argv`, env vars, cookies) and **sink patterns** (eval/exec, `os.system`, `subprocess` with `shell=True`, `pickle.loads`, `yaml.load`, Jinja2 `render_template_string`) using regex. SQL injection is detected with an **AST check**: SQL built with `%`, f-strings, `.format()` or `+` is flagged, while parameterised `execute(q, params)` calls are not.
3. BFS over CALLS edges from each source function, up to 6 hops deep, finds reachable sinks.
4. Confidence: **high** if source calls sink directly (≤1 hop), **medium** for 2–3 hops, **low** for 4–6 hops.
5. Deduplication keeps the highest-confidence path per `(source, sink)` pair.

### Verified finding — DVPWA SQLi

**Target:** [dvpwa](https://github.com/anxolerd/dvpwa) — intentionally vulnerable Python/aiohttp web app.

**Finding:** `views.students` → `student.Student.create` — SQL Injection (high confidence)

```
Source: sqli/views.py:52  (views.students)
  data = await request.post()        ← aiohttp taint source
  await Student.create(conn, data['name'])

Sink:   sqli/dao/student.py:41  (student.Student.create)
  q = ("INSERT INTO students (name) "
       "VALUES ('%(name)s')" % {'name': name})   ← SQL built with %
  await cur.execute(q)               ← unparameterised SQL
```

This is the documented CVE-class vulnerability in DVPWA: a POST to `/students` with a crafted `name` value achieves SQL injection because the INSERT query is built via Python `%` string formatting before being passed to `execute()`.

**Precision on DVPWA — before and after the call-resolution fix:**

| | Findings | True positives | Precision |
|---|---|---|---|
| Name-based call resolution + regex SQL sink | 8 | 1 | 12.5% |
| Receiver-aware call resolution + AST SQL sink | **1** | **1** | **100%** |

The 7 false positives had two causes: calls were matched by method name only, so `Course.create(...)` was linked to `Student.create`; and the SQL regex flagged parameterised queries such as `Student.get`. Both cases are covered by regression tests in `tests/test_call_resolution_and_sql_sink.py`.

### Limitations

| Limitation | Details |
|---|---|
| **Python-only** | JS/Java/Go patterns not yet implemented — additive to add (new key in `SOURCES`/`SINKS` dicts) |
| **Call-graph level** | Does NOT track data flow through variables — a tainted value may not actually reach the sink at runtime |
| **Mostly regex-based** | Sources and non-SQL sinks are regex matches on raw source code — false positives possible |
| **SQL injection heuristic** | The AST check needs the SQL text and the dynamic string building in the same function — may miss queries composed across functions |
| **No sanitiser modelling** | If tainted data passes through a sanitiser/validator between source and sink, the finding is still reported |

### API endpoints

```
GET  /api/repositories/{id}/taint-analysis
     → { findings: [{ source_qn, sink_qn, vuln_class, confidence, path, ... }] }

POST /api/repositories/{id}/taint-analysis/explain
     Body: { source_qn, sink_qn, vuln_class, confidence, path }
     → { explanation: "..." }   (OpenAI GPT-4o-mini if OPENAI_API_KEY set; Groq qwen3.8-27b if GROQ_API_KEY set; distilgpt2 local fallback)
```

The LLM explanation backend uses **Groq (qwen/qwen3.8-27b)** by default via `GROQ_API_KEY` — free tier, no card required. Set `OPENAI_API_KEY` instead to override with GPT-4o-mini.

### Security tab screenshot

![Security tab showing 8 SQL Injection findings for DVPWA with AI explanation expanded](docs/security-tab-screenshot.png)

*Captured before the precision fix, when DVPWA showed 8 findings (7 false positives); the current version reports only the `views.students → Student.create` injection shown expanded here.*

### Running taint analysis

Analysis runs automatically as pipeline step 7 after ingestion. To re-trigger:

```bash
# Re-ingest repository (analysis runs on every ingestion)
curl -X POST http://localhost:8080/api/repositories \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/anxolerd/dvpwa"}'
```

The **Security** tab in the UI shows all findings with confidence filters, vulnerability class breakdown, call-path visualisation, and an on-demand AI explanation button.

---

## ⚠️ Known Limitations

| Limitation | Details |
|-----------|---------|
| **Public repos only** | No GitHub OAuth — private repos require token in URL |
| **Call resolution is not type-aware** | Python resolves calls by receiver (`Klass.m`, `self.m`, `module.f`), and calls on receivers of unknown type create no edge (possible missed edges); JS/Java/Go still match by name, so common names can create false edges |
| **Repo size limit** | Default 500 MB — configurable via `MAX_REPO_SIZE_MB` |
| **Rust/C not yet supported** | Parsers not yet implemented |
| **Auth is a scaffold** | JWTs are signature-checked, but there are no user accounts: `/api/auth/token` issues a token for any credentials, and with `DEBUG=true` requests without a token are allowed as `anonymous` |
| **Rate limiting is in-memory** | Per-IP counter that resets on restart; not shared across multiple instances |
| **Taint analysis is call-graph level** | Not data-flow sensitive — false positives expected (see Security Analysis section above) |

---

## 📄 Environment Variables

| Variable | Required | Default | Description |
|---------|---------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL async connection string |
| `DATABASE_URL_SYNC` | ✅ | — | PostgreSQL sync connection string |
| `SECRET_KEY` | ✅ | — | JWT signing secret (32 random bytes) |
| `OPENAI_API_KEY` | ❌ | — | Enables Ask AI + Explain via GPT-4o-mini (takes priority over Groq) |
| `GROQ_API_KEY` | ❌ | — | Enables Ask AI + Explain via Groq (qwen3.8-27b, free tier) |
| `CLONE_BASE_PATH` | ❌ | `/tmp/cue_repos` | Where repos are cloned |
| `MAX_REPO_SIZE_MB` | ❌ | `500` | Max repository size in MB |
| `EMBEDDING_MODEL_NAME` | ❌ | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `EMBEDDING_DIMENSION` | ❌ | `384` | Must match model output |
| `CORS_ORIGINS` | ❌ | `["http://localhost:5174"]` | Allowed frontend origins |
| `ENVIRONMENT` | ❌ | `development` | Set to `production` on server |
| `DEBUG` | ❌ | `true` | Set to `false` on server |

---

## 🙏 Acknowledgements

- [Tree-sitter](https://tree-sitter.github.io) — incremental parsing library used by GitHub
- [sentence-transformers](https://sbert.net) — semantic text embeddings
- [pgvector](https://github.com/pgvector/pgvector) — vector similarity search for PostgreSQL
- [NetworkX](https://networkx.org) — graph analysis algorithms
- [FastAPI](https://fastapi.tiangolo.com) — modern async Python web framework
- [D3.js](https://d3js.org) — data-driven document visualization
- [Mermaid.js](https://mermaid.js.org) — diagram-as-code rendering
- Kipf & Welling (2017) — [Semi-Supervised Classification with Graph Convolutional Networks](https://arxiv.org/abs/1609.02907)

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with Python · FastAPI · React · PyTorch · PostgreSQL**

⭐ **Star this repo** if it helped you understand a codebase faster!

[Report Bug](https://github.com/Chinmaya2310/Codebase-Understanding-Engine/issues) · [Request Feature](https://github.com/Chinmaya2310/Codebase-Understanding-Engine/issues)

</div>
