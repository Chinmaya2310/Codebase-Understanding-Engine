# Codebase Understanding Engine — Full System Context

Use this document with Claude.ai (paste into a Project as a knowledge source) to ask any question
about how this system works, why decisions were made, or how to extend it.

---

## What This Is

A web application that takes any public GitHub URL, clones it, parses the source code, builds a
knowledge graph, runs several analyses, and surfaces the results in a React UI. Think of it as
"read-only static analysis as a service." No code is executed from the target repo — everything
is parsed and analysed offline.

Core capabilities surfaced to users:
- **Code Graph** — interactive D3 force graph of all functions/classes and their relationships
- **Architecture** — auto-detected pattern (MVC / layered / microservices) + Mermaid diagrams
- **Dead Code** — functions/methods with zero incoming call edges
- **Security** — taint-flow analysis: paths from untrusted HTTP input to dangerous sinks
- **Elements** — paginated browser of every parsed code element with file/line metadata
- **Ask AI** — RAG question answering over the codebase using vector similarity + LLM

---

## Stack at a Glance

| Layer | Technology |
|---|---|
| Web framework | FastAPI (async, Python 3.13) |
| Database | PostgreSQL 17 + pgvector extension |
| ORM | SQLAlchemy 2.x (async) with asyncpg driver |
| Parsing | tree-sitter (Python, JS, TS, Java, Go grammars) |
| Graph | NetworkX MultiDiGraph (in-memory during pipeline) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` → 384-dim vectors |
| LLM | OpenAI GPT-4o-mini (if OPENAI_API_KEY) or Groq qwen3.8-27b (if GROQ_API_KEY) or distilgpt2 local fallback |
| GNN (experimental) | 2-layer PyTorch GCN (CodeGNN) — defined but not yet wired into the pipeline |
| Frontend | React 18 + TypeScript + Vite + axios + D3.js + Mermaid.js |
| Auth | JWT (python-jose) — a dev no-op: any call with no token still passes via the `get_current_user` dependency |
| Rate limiting | In-memory counter per user — not Redis-backed |

---

## Repository File Map

```
backend/
  api/
    main.py                  ← FastAPI app factory + lifespan (calls init_db)
    schemas.py               ← Pydantic request/response models
    routes/
      repositories.py        ← CRUD + trigger pipeline as BackgroundTask
      analysis.py            ← GET results + POST taint explain
      diagrams.py            ← GET Mermaid diagrams + code graph JSON
      questions.py           ← POST /ask (RAG Q&A)
  core/
    config.py                ← Pydantic Settings loaded from .env
    security.py              ← JWT create/verify, rate-limit dependency
  db/
    database.py              ← create_async_engine, AsyncSessionLocal, init_db()
  models/
    repository.py            ← Repository ORM model + RepositoryStatus enum
    code_element.py          ← CodeElement ORM model (stores source_code + pgvector embedding)
    graph_node.py            ← GraphNode + GraphEdge ORM models
    analysis.py              ← AnalysisResult ORM model + AnalysisType enum
  parsers/
    base_parser.py           ← BaseParser ABC, ParsedElement dataclass, ParseResult dataclass
    python_parser.py         ← tree-sitter Python: classes, functions, imports, calls
    javascript_parser.py     ← tree-sitter JS/TS
    java_parser.py           ← tree-sitter Java
    go_parser.py             ← tree-sitter Go
  services/
    repository_service.py    ← git clone, file enumeration, size validation
    parser_service.py        ← dispatches files to correct language parser
    graph_service.py         ← build NetworkX graph from ParseResults, persist to DB
    embedding_service.py     ← sentence-transformers encode, batched, returns plain lists
    diagram_service.py       ← architecture detection, Mermaid diagram generation
    dead_code_service.py     ← zero-in-degree node detection
    taint_patterns.py        ← regex patterns for sources and sinks, keyed by language
    taint_analysis_service.py← direct + interprocedural BFS taint detection
    llm_service.py           ← OpenAI / Groq / distilgpt2, priority order
    question_answering_service.py ← RAG answer + taint explain
    analysis_pipeline.py     ← orchestrates all 7 steps, runs as BackgroundTask
  ml/
    embeddings/encoder.py    ← thin wrapper around sentence-transformers (mostly unused in pipeline)
    gnn/
      layers.py              ← GCNLayer, normalise_adjacency
      model.py               ← CodeGNN (2-layer GCN, 384→256→128)
      dataset.py             ← PyTorch Geometric dataset builder
      trainer.py             ← training loop (not called from pipeline currently)

frontend/src/
  App.tsx                    ← BrowserRouter with two routes: "/" and "/repo/:id"
  main.tsx                   ← React root
  index.css                  ← CSS custom properties (--bg, --accent, --red, etc.)
  types/index.ts             ← TypeScript interfaces for all API shapes
  services/api.ts            ← axios client, all API calls as typed functions
  hooks/useRepository.ts     ← polls GET /repositories/:id every 3s until ready
  pages/RepositoryView.tsx   ← main page: header, progress stepper, sidebar tabs, content
  components/
    RepositoryList.tsx       ← home page: list + submit URL form
    CodeGraph.tsx            ← D3 force-directed graph (nodes = functions/classes, edges = calls)
    ArchitectureDiagram.tsx  ← renders Mermaid diagrams
    DeadCodePanel.tsx        ← lists dead code findings with filters
    SecurityFindingsPanel.tsx← taint findings with confidence filter + Explain button
    FileExplorer.tsx         ← paginated element browser
    QuestionAnswer.tsx       ← chat-style Q&A input + answer display

tests/
  test_taint_analysis.py     ← 19 unit tests for taint detection (no DB needed)
```

---

## Database Schema

Five tables, all with UUID primary keys:

### `repositories`
Tracks a submitted GitHub repo and its pipeline state.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| url | VARCHAR(512) | original GitHub URL |
| owner | VARCHAR(255) | parsed from URL |
| name | VARCHAR(255) | parsed from URL |
| default_branch | VARCHAR(255) | default "main" |
| local_path | VARCHAR(1024) | where it was cloned on disk |
| status | ENUM | pending→cloning→parsing→building_graph→embedding→analyzing→ready / failed |
| progress | FLOAT | 0.0–1.0, set at each pipeline step |
| error_message | TEXT | set on failure |
| total_files | INT | filled after parsing |
| total_lines | INT | filled after parsing |
| created_at / updated_at | TIMESTAMPTZ | |

### `code_elements`
One row per parsed code construct (function, class, method, module, etc.)

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| repository_id | UUID FK → repositories | cascade delete |
| element_type | ENUM | module/class/function/method/variable/import/interface/struct |
| name | VARCHAR(512) | short name (e.g. "create") |
| qualified_name | VARCHAR(1024) | dotted path (e.g. "student.Student.create") |
| file_path | VARCHAR(1024) | absolute path on the analysis server |
| language | VARCHAR(64) | python / javascript / java / go |
| start_line / end_line | INT | line numbers in the source file |
| source_code | TEXT | full raw source text of the element |
| docstring | TEXT | extracted docstring if any |
| signature | VARCHAR(2048) | e.g. "def create(conn, name)" |
| embedding | VECTOR(384) | pgvector column — sentence-transformers output |
| is_dead_code | BOOL | set true if dead-code analysis flags it |
| reference_count | INT | (not currently populated by pipeline) |

### `graph_nodes`
Mirror of code_elements in the graph layer — one node per code_element.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| repository_id | UUID FK | |
| code_element_id | UUID FK → code_elements | |
| label | VARCHAR(512) | short display name |
| node_type | VARCHAR(64) | same as element_type |

### `graph_edges`
Directed edges between graph_nodes.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| source_id | UUID FK → graph_nodes | |
| target_id | UUID FK → graph_nodes | |
| edge_type | ENUM | imports / calls / inherits / implements / contains / references |

### `analysis_results`
Key-value store for analysis outputs — one JSON blob per analysis type per repo.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| repository_id | UUID FK | |
| analysis_type | ENUM | architecture / dependencies / dead_code / qa / diagram / TAINT_ANALYSIS |
| result | JSON | the full output, shape varies by type |
| created_at | TIMESTAMPTZ | most-recent row is served by the API |

---

## The Analysis Pipeline (step by step)

Triggered as a FastAPI `BackgroundTask` when `POST /api/repositories` is called. Runs entirely
in a single `async with AsyncSessionLocal()` session. Any exception at the top level sets
status=FAILED. Step 7 (taint) is wrapped in its own try/except so it can fail without failing the
whole pipeline.

```
Step 1 — CLONE (progress 0.05)
  RepositoryService.clone()
  → git clone --depth 1 <url> /tmp/cue_repos/<repo_id>/
  → validates repo is under MAX_REPO_SIZE_MB (default 500 MB)

Step 2 — PARSE (progress 0.20)
  RepositoryService.enumerate_source_files()
  → walks directory tree, groups files by language extension
  → ignores: .git, node_modules, venv, __pycache__, dist, build, etc.

  ParserService.parse_files()
  → dispatches each file to PythonParser / JavaScriptParser / JavaParser / GoParser
  → each parser uses tree-sitter to walk the AST
  → emits ParsedElement objects: module, class, function, method, import, call
  → "call" elements capture the callee name and their parent qualified_name

Step 3 — BUILD GRAPH (progress 0.45)
  GraphService.build_graph()
  → creates NetworkX MultiDiGraph
  → nodes: all elements except "call" and "import" pseudo-elements
  → CONTAINS edges: parent_qualified_name → child qualified_name (structural)
  → CALLS edges: resolved by matching callee name to known qualified_names (~80% accuracy)
  → IMPORTS edges: module → target module (external deps get an "external::<name>" node)

Step 4 — EMBED (progress 0.55–0.65)
  EmbeddingService.embed_batch()
  → builds a text blob for each node: "function_type: name\nsignature\ndocstring[:300]\nsource_code[:600]"
  → encodes all in CPU batches of 16 using sentence-transformers all-MiniLM-L6-v2
  → persists CodeElement rows in chunks of 50 to avoid DB socket buffer issues

Step 5 — PERSIST GRAPH (progress 0.70)
  GraphService.persist_graph()
  → writes GraphNode + GraphEdge rows in chunks of 100

Step 6 — ANALYZE (progress 0.85)
  DiagramService — generates 3 things:
    1. dependency_diagram (Mermaid LR): top-40 modules by degree, IMPORTS edges
    2. architecture_diagram (Mermaid TD): layers detected by directory name heuristics
    3. code_graph_json: top-200 nodes + all edges between them (for D3 in the frontend)

  DiagramService.detect_architecture():
    → scans file paths for keywords: controllers/views/pages/routes → "presentation"
      services/domain/core → "business", models/db/dao → "data"
    → 3+ layers → "layered" or "mvc"; 3+ distinct service dirs → "microservices"

  DeadCodeService.find_dead_code():
    → finds function/method/class nodes with zero incoming calls/imports/inherits/implements edges
    → skips: __dunder__, test_*, main, setup, teardown, handle*, on_* (entry-point patterns)
    → marks matched CodeElement rows as is_dead_code=True in the DB

  Saves 3 AnalysisResult rows: ARCHITECTURE, DIAGRAM, DEAD_CODE

Step 7 — TAINT ANALYSIS (inside own try/except)
  TaintAnalysisService.run(graph, language="python"):
    → pattern matching phase: regex each function's source_code against SOURCES and SINKS
    → direct findings: source_function == sink_function (both patterns in same body)
    → interprocedural: BFS over CALLS edges from each source node, max_depth=6
      - finds sink nodes reachable via CALLS edges
      - confidence: high if 1 hop, medium if 2–3, low if 4–6
      - deduplicates on (source_qn, sink_qn), keeps highest confidence
    → saves 1 AnalysisResult row: TAINT_ANALYSIS

Step 8 — READY (progress 1.0)
```

---

## Taint Analysis Deep Dive

### Source patterns (what counts as "user-controlled input")
All defined in `backend/services/taint_patterns.py`, SOURCES["python"]:
- `request.(args|form|values|json|GET|POST|data)` — Flask-style HTTP params
- `request.(post|json|body|text)\(` — aiohttp/Starlette style (note: lowercase method *call*)
- `input\(` — interactive stdin
- `sys\.argv` — CLI arguments
- `os\.environ\.get` — environment variables
- `request.(headers|cookies)` — HTTP headers and cookies

### Sink patterns (what counts as "dangerous")
All in SINKS["python"]:
- `eval\(` → Code Injection
- `exec\(` → Code Injection
- `os\.system\(` → Command Injection
- `subprocess\.(call|run|Popen)\([^)]*shell\s*=\s*True` → Command Injection
- `\.execute\(\s*["']*.*%s|\.execute\(\s*f["']` → SQL Injection (f-string or %s in execute)
- `(INSERT|SELECT|UPDATE|DELETE).*['"]\s*%\s*[\w\{\(\[]` (re.DOTALL) → SQL Injection (% operator)
- `pickle\.loads\(` → Insecure Deserialization
- `yaml\.load\((?!.*Loader=yaml\.SafeLoader)` → Insecure Deserialization
- `render_template_string\(` → SSTI

### BFS algorithm
```python
for src_qn in source_functions:
    queue = deque([(src_qn, [src_qn], 0)])
    visited = {src_qn}
    while queue:
        current, path, hop_count = queue.popleft()
        for neighbor in graph.successors(current):  # follow CALLS edges
            if neighbor in visited: continue
            if hop_count + 1 > max_depth: continue
            if neighbor in sink_map:
                # found a path — record finding
                confidence = "high" if hop_count+1 <= 1 else "medium" if <= 3 else "low"
            visited.add(neighbor)
            queue.append((neighbor, path + [neighbor], hop_count + 1))
```

### Explain endpoint
`POST /api/repositories/{id}/taint-analysis/explain` — on-demand, never pre-generated.
1. Fetches `source_code` from CodeElement table for both source_qn and sink_qn
2. Builds a prompt with the actual code blocks + vulnerability class + call path
3. Calls LLMService.generate() → Groq / OpenAI / distilgpt2
4. Returns plain-text explanation to the frontend

---

## Parsing — How tree-sitter Works Here

tree-sitter is a C library with Python bindings. It parses source code into a concrete syntax tree
(CST) without needing a language runtime.

**PythonParser walk logic** (`backend/parsers/python_parser.py`):
- Starts at the file root, sets `parent_qn = module_stem` (filename without extension)
- Recurses into `class_definition` → emits class element, walks children with class as parent
- Recurses into `function_definition` → emits function or method (method if parent has a dot)
- `import_statement` / `import_from_statement` → emits import pseudo-elements
- `call` node → emits call pseudo-element with callee name + parent_qn
- All other node types → recursive walk with same parent_qn

**Qualified names** are built by concatenating parent + "." + name:
- `student.py` → module qn = `student`
- class `Student` inside → `student.Student`
- method `create` inside → `student.Student.create`

**Call resolution in GraphService** is name-only (not type-aware):
- Builds a `name_to_qns` dict mapping short name → list of qualified names
- For each recorded call `(caller, callee_name)`, looks up all qns with that name
- Adds CALLS edges for all matches → can produce false-positive edges for common names

---

## LLM Service — Priority and Fallback

`backend/services/llm_service.py`:

```
Priority 1: OpenAI (if OPENAI_API_KEY is set)
  → uses openai.AsyncOpenAI client
  → model: settings.openai_model (default "gpt-4o-mini")

Priority 2: Groq (if GROQ_API_KEY is set, OpenAI not set)
  → uses groq.AsyncGroq client (separate package, avoids httpx2 bug)
  → model: settings.groq_model (default "qwen/qwen3.8-27b")
  → Note: httpx2 compat bug prevents using openai client with Groq base_url

Priority 3: local distilgpt2
  → loaded via transformers.pipeline("text-generation", "distilgpt2")
  → cached with @lru_cache — only loads once per process
  → output is low quality (completes the prompt rather than answering it)
```

The `_make_client()` function is called in `LLMService.__init__()`, which runs once per request
(since `QuestionAnsweringService` instantiates `LLMService()` fresh each call).

---

## API Routes Reference

All routes are under `/api/`. Auto-generated docs at `http://localhost:8080/docs`.

### Repositories
| Method | Path | Description |
|---|---|---|
| POST | `/api/repositories` | Submit URL → creates DB row → triggers pipeline as BackgroundTask |
| GET | `/api/repositories` | List all repos (most recent first) |
| GET | `/api/repositories/{id}` | Get one repo (used for status polling) |
| DELETE | `/api/repositories/{id}` | Delete repo + cascade (also rm -rf local clone) |
| POST | `/api/repositories/{id}/reanalyze` | Reset to PENDING, trigger pipeline again |

### Analysis Results (all under `/api/repositories/{id}/`)
| Method | Path | Returns |
|---|---|---|
| GET | `/architecture` | `{pattern, layers, microservices_detected, confidence}` |
| GET | `/dead-code` | `{findings: [{qualified_name, node_type, file_path, start_line, end_line, reason, confidence}]}` |
| GET | `/taint-analysis` | `{findings: [{finding_type, source_qn, source_file, source_line, sink_qn, sink_file, sink_line, path, vuln_class, confidence}]}` |
| POST | `/taint-analysis/explain` | Body: `{source_qn, sink_qn, vuln_class, confidence, path}` → `{explanation: string}` |
| GET | `/elements` | Paginated CodeElement list (query params: element_type, dead_code_only, limit, offset) |
| GET | `/diagrams` | `{dependency_diagram: mermaid_string, architecture_diagram: mermaid_string, code_graph: {nodes, edges}}` |
| POST | `/ask` | Body: `{question, top_k}` → `{answer, sources}` |

### System
| Method | Path | Description |
|---|---|---|
| GET | `/health` | `{status: "ok", app, version}` |
| POST | `/api/auth/token` | Dev stub — returns a JWT for any username/password |

---

## Frontend Architecture

**Routing** (`App.tsx`):
- `/` → `RepositoryList` — shows all repos, form to submit a new URL
- `/repo/:id` → `RepositoryView` — the main analysis UI

**State management**: no global store. Each component fetches its own data via `api.ts`.

**Polling** (`hooks/useRepository.ts`):
- `useRepositoryPolling(id)` sets an interval that calls `api.getRepository(id)` every 3 seconds
- Stops polling when status is `ready` or `failed`
- Used by `RepositoryView` to animate the progress stepper

**Tab system** (`RepositoryView.tsx`):
- Tabs: graph | architecture | deadcode | security | elements | qa
- Only rendered when `status === "ready"` — during processing, shows animated progress stepper
- Each tab is a separate component, mounted/unmounted on tab switch (no lazy loading)

**CSS variables** (`index.css`):
All colours are custom properties: `--bg`, `--bg2`, `--bg3`, `--bg4`, `--text`, `--text2`,
`--text3`, `--border`, `--accent`, `--accent2`, `--accent-bg`, `--red`, `--red-bg`, `--green`,
`--green-bg`, `--amber`, `--amber-bg`, `--blue`, `--blue-bg`. Dark theme only.

**D3 Code Graph** (`CodeGraph.tsx`):
- Fetches `api.getDiagrams(id)` → uses `code_graph.nodes` and `code_graph.edges`
- Force simulation: link force + charge repulsion + collision + centering
- Node colour by type: function=blue, class=green, method=purple, module=orange, etc.
- Click a node → shows a detail panel with file path and type

**SecurityFindingsPanel** (`SecurityFindingsPanel.tsx`):
- Fetches `api.getTaintAnalysis(id)` on mount
- Renders 4 stat boxes: total findings, high confidence, medium confidence, vuln class count
- Filters: confidence (all/high/medium/low) + vuln class selector
- Each finding is a `FindingCard`: collapsed by default, click to expand
  - Expanded: call path (source→hop→sink), source file:line, sink file:line, Explain button
  - Explain button: calls `api.explainTaintFinding()`, shows spinner, caches result in component state

---

## Key Design Decisions and Why

**NetworkX in-memory graph, not persisted as a graph DB**
The graph is built and used entirely during the pipeline. After analysis, results are stored as
JSON blobs in `analysis_results`. Graph nodes/edges are also written to `graph_nodes`/`graph_edges`
tables, but these are not queried for analysis — they exist for potential future use (the API
doesn't currently expose graph traversal queries).

**Name-based call resolution (not type-aware)**
A full type-inference call graph would require either a full language server per language or a
much more complex multi-pass analysis. The current approach (match callee name → all known qualified
names with that name) works well enough for most codebases but produces false edges for common
names like `get`, `create`, `update`.

**Regex-based taint sources/sinks (not AST-level)**
The taint engine runs regex against the raw `source_code` string stored for each function body.
This is much simpler than AST-level data flow, but means:
- Can't distinguish `request.args` in a comment from a real call
- Can't track data through assignments across function boundaries
- The cross-line SQL injection pattern (`sql_percent_format`) requires `re.DOTALL` and a SQL keyword
  to reduce false positives

**Chunked DB writes throughout the pipeline**
The original code was written to support Windows (WinError 10055 = socket buffer exhaustion).
Writes happen in chunks of 50 (embeddings) and 100 (graph nodes/edges) with individual commits.
This is slower than a single bulk insert but safer on constrained environments.

**pgvector for semantic search**
`code_elements.embedding` is a `VECTOR(384)` column. The `POST /ask` endpoint does:
```sql
ORDER BY embedding <-> query_vector  -- cosine distance operator
LIMIT top_k
```
This is the retrieval step of the RAG pipeline. The LLM then gets the top-k matching code
elements as context.

**AnalysisResult as a JSON blob store**
Rather than separate tables for each analysis type, all results land in `analysis_results` with
a `result` JSONB column. This means no migrations are needed to add a new analysis type — just add
an enum value and write a new JSON shape. The tradeoff is no queryability within the result.

**Groq via native `groq` package, not openai client**
The `openai` library in this environment uses `httpx2` internally. `httpx2` has a decompression
bug (`Decompressor.decompress() got an unexpected keyword argument 'output_buffer_limit'`) that
causes all Groq API calls through the openai client to fail silently with `APIConnectionError` and
fall through to distilgpt2. The `groq` Python package uses its own HTTP stack and works correctly.

**CodeGNN is defined but not wired into the pipeline**
`backend/ml/gnn/` contains a working 2-layer GCN (384→256→128) with a PyTorch training loop.
It would take the sentence-transformer embeddings as node features and the call graph adjacency
as input, producing structure-aware embeddings that encode graph neighbourhood. It is not called
from `analysis_pipeline.py` — integrating it would replace the raw sentence-transformer embeddings
with GNN-refined ones for both the vector search and dead-code detection steps.

---

## Configuration (`.env`)

```
DATABASE_URL=postgresql+asyncpg://user@localhost:5432/codebase_engine
DATABASE_URL_SYNC=postgresql://user@localhost:5432/codebase_engine
REDIS_URL=redis://localhost:6379/0          # defined but Redis is not actually used yet
SECRET_KEY=...                              # JWT signing key
OPENAI_API_KEY=                             # leave empty to use Groq
GROQ_API_KEY=...                            # free tier key, no card required
CLONE_BASE_PATH=/tmp/cue_repos
DEBUG=true
```

Settings are loaded by `backend/core/config.py` via pydantic-settings. `get_settings()` is
`@lru_cache()` — calling it a second time returns the same instance. This means `.env` changes
only take effect after restarting the server.

---

## How to Run Locally

```bash
# Prerequisites: PostgreSQL 17 + pgvector extension, Python 3.11+, Node 18+

# Backend
pip install -r requirements.txt
uvicorn backend.api.main:app --port 8080
# First boot takes ~20s: loads distilgpt2 + sentence-transformers at startup

# Frontend (separate terminal, from frontend/ directory)
npm install
npm run dev
# Runs on http://localhost:5174/

# Database migrations
# There are no Alembic migrations — init_db() runs create_all() on startup
# and adds the TAINT_ANALYSIS enum value idempotently via a DO $$ block
```

---

## How to Add a New Analysis

1. Add a new value to `AnalysisType` enum in `backend/models/analysis.py`
2. Add the migration to `init_db()` in `backend/db/database.py` if it's a new PG enum value
3. Write a new service in `backend/services/` that takes the NetworkX graph and returns a dict
4. Add a step in `run_analysis_pipeline()` in `backend/services/analysis_pipeline.py` (wrap in
   its own try/except if it should be non-fatal like taint analysis)
5. Add a Pydantic response schema in `backend/api/schemas.py`
6. Add a GET route in `backend/api/routes/analysis.py`
7. Add a call in `frontend/src/services/api.ts`
8. Add a TypeScript type in `frontend/src/types/index.ts`
9. Create a new panel component in `frontend/src/components/`
10. Add a tab entry in the `TABS` array in `frontend/src/pages/RepositoryView.tsx`

---

## How to Add a New Language Parser

1. Install the tree-sitter grammar: `pip install tree-sitter-<lang>`
2. Create `backend/parsers/<lang>_parser.py` extending `BaseParser`
3. Implement `_load_language()` and `_walk()` following the Python parser as a template
4. Register the file extensions in `backend/services/repository_service.py`'s `LANGUAGE_EXTENSIONS`
5. Add the parser to `ParserService.parse_files()` in `backend/services/parser_service.py`
6. If you want taint analysis for the new language, add `SOURCES["<lang>"]` and `SINKS["<lang>"]`
   entries in `backend/services/taint_patterns.py`

---

## Known Limitations

| Issue | Detail |
|---|---|
| Call resolution is name-only | ~80% accuracy; common names produce false CALLS edges |
| Taint is call-graph level | Not data-flow sensitive — false positives expected |
| SQL injection regex is heuristic | Requires a SQL keyword in the same expression |
| No sanitiser modelling in taint | A validator between source and sink is ignored |
| Taint analysis is Python-only | JS/Java/Go patterns not yet defined |
| GNN not wired in | CodeGNN is defined and tested but not called from the pipeline |
| Redis not used | REDIS_URL is configured but nothing currently uses Redis |
| Rate limiting is in-memory | Resets on server restart; not suitable for multi-instance deploy |
| No real auth | JWT verification passes with any token for dev convenience |
| No incremental analysis | Reanalyze always reclones and reprocesses from scratch |
