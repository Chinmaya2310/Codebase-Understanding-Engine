"""
Unit tests for TaintAnalysisService.

Uses synthetic NetworkX graphs — no database required.
"""
from __future__ import annotations

import networkx as nx
import pytest

from backend.services.taint_analysis_service import TaintAnalysisService
from backend.services.taint_patterns import SINKS, SOURCES


def _fn(graph: nx.MultiDiGraph, qn: str, code: str, lang: str = "python") -> None:
    """Add a function node with source_code to the graph."""
    graph.add_node(
        qn,
        node_type="function",
        label=qn.split(".")[-1],
        source_code=code,
        file_path=f"app/{qn.split('.')[0]}.py",
        start_line=1,
        language=lang,
    )


def _call(graph: nx.MultiDiGraph, caller: str, callee: str) -> None:
    graph.add_edge(caller, callee, edge_type="calls")


# ---------------------------------------------------------------------------
# Pattern module sanity
# ---------------------------------------------------------------------------

def test_patterns_loaded():
    assert "python" in SOURCES
    assert "python" in SINKS
    assert len(SOURCES["python"]) >= 5
    assert len(SINKS["python"]) >= 6


# ---------------------------------------------------------------------------
# find_source_functions
# ---------------------------------------------------------------------------

def test_find_source_functions_detects_request_args():
    g = nx.MultiDiGraph()
    _fn(g, "views.login", "data = request.args.get('user')")
    _fn(g, "views.static", "return render_template('index.html')")

    svc = TaintAnalysisService()
    sources = svc.find_source_functions(g, "python")
    assert "views.login" in sources
    assert "views.static" not in sources


def test_find_source_functions_detects_input():
    g = nx.MultiDiGraph()
    _fn(g, "cli.run", "name = input('Enter name: ')")
    svc = TaintAnalysisService()
    assert "cli.run" in svc.find_source_functions(g)


def test_find_source_functions_no_match():
    g = nx.MultiDiGraph()
    _fn(g, "utils.add", "return a + b")
    svc = TaintAnalysisService()
    assert svc.find_source_functions(g) == []


def test_find_source_functions_unknown_language():
    g = nx.MultiDiGraph()
    _fn(g, "foo.bar", "request.args.get('x')", lang="ruby")
    svc = TaintAnalysisService()
    # No patterns for ruby — must return empty list, not raise
    assert svc.find_source_functions(g, "ruby") == []


# ---------------------------------------------------------------------------
# find_sink_functions
# ---------------------------------------------------------------------------

def test_find_sink_functions_eval():
    g = nx.MultiDiGraph()
    _fn(g, "admin.run_code", "result = eval(user_input)")
    svc = TaintAnalysisService()
    sinks = dict(svc.find_sink_functions(g))
    assert "admin.run_code" in sinks
    assert sinks["admin.run_code"] == "Code Injection"


def test_find_sink_functions_sql():
    g = nx.MultiDiGraph()
    _fn(g, "db.query", "cursor.execute(f'SELECT * FROM users WHERE id={uid}')")
    svc = TaintAnalysisService()
    sinks = dict(svc.find_sink_functions(g))
    assert "db.query" in sinks
    assert sinks["db.query"] == "SQL Injection"


def test_find_sink_functions_subprocess_shell():
    g = nx.MultiDiGraph()
    _fn(g, "admin.ping", "subprocess.run(cmd, shell=True)")
    svc = TaintAnalysisService()
    sinks = dict(svc.find_sink_functions(g))
    assert "admin.ping" in sinks
    assert sinks["admin.ping"] == "Command Injection"


def test_find_sink_no_match():
    g = nx.MultiDiGraph()
    _fn(g, "utils.safe", "return str(x)")
    svc = TaintAnalysisService()
    assert svc.find_sink_functions(g) == []


# ---------------------------------------------------------------------------
# find_direct_findings
# ---------------------------------------------------------------------------

def test_direct_finding_detected():
    """Same function body has both source and sink — highest confidence."""
    g = nx.MultiDiGraph()
    _fn(g, "app.dangerous", "x = request.args.get('cmd'); eval(x)")

    svc = TaintAnalysisService()
    sources = svc.find_source_functions(g)
    sinks   = svc.find_sink_functions(g)
    direct  = svc.find_direct_findings(g, sources, sinks)

    assert len(direct) == 1
    f = direct[0]
    assert f["source_qn"] == "app.dangerous"
    assert f["sink_qn"] == "app.dangerous"
    assert f["confidence"] == "high"
    assert f["finding_type"] == "direct"
    assert f["vuln_class"] == "Code Injection"


def test_no_direct_finding_when_source_and_sink_separate():
    g = nx.MultiDiGraph()
    _fn(g, "views.get", "x = request.args.get('q')")
    _fn(g, "db.run", "cursor.execute(f'SELECT {q}')")
    _call(g, "views.get", "db.run")

    svc = TaintAnalysisService()
    sources = svc.find_source_functions(g)
    sinks   = svc.find_sink_functions(g)
    direct  = svc.find_direct_findings(g, sources, sinks)

    assert direct == []


# ---------------------------------------------------------------------------
# find_interprocedural_paths
# ---------------------------------------------------------------------------

def test_interprocedural_direct_hop_detected():
    """Source calls Sink (1 hop) → confidence high."""
    g = nx.MultiDiGraph()
    _fn(g, "views.search", "q = request.args.get('q'); db_query(q)")
    _fn(g, "db.execute", "cursor.execute(f'SELECT {q}')")
    _call(g, "views.search", "db.execute")

    svc = TaintAnalysisService()
    sources = svc.find_source_functions(g)
    sinks   = svc.find_sink_functions(g)
    paths   = svc.find_interprocedural_paths(g, sources, sinks)

    assert len(paths) == 1
    f = paths[0]
    assert f["source_qn"] == "views.search"
    assert f["sink_qn"]   == "db.execute"
    assert f["confidence"] == "high"
    assert f["path"] == ["views.search", "db.execute"]


def test_interprocedural_multi_hop_medium_confidence():
    """Source → A → B → Sink (3 hops) → confidence medium."""
    g = nx.MultiDiGraph()
    _fn(g, "handler.index", "data = request.form.get('data')")
    _fn(g, "logic.process", "return format_data(data)")
    _fn(g, "logic.format_data", "return transform(data)")
    _fn(g, "sink.run", "os.system(data)")
    _call(g, "handler.index",   "logic.process")
    _call(g, "logic.process",   "logic.format_data")
    _call(g, "logic.format_data", "sink.run")

    svc = TaintAnalysisService()
    sources = svc.find_source_functions(g)
    sinks   = svc.find_sink_functions(g)
    paths   = svc.find_interprocedural_paths(g, sources, sinks)

    assert any(
        f["source_qn"] == "handler.index" and f["sink_qn"] == "sink.run"
        for f in paths
    )
    match = next(
        f for f in paths
        if f["source_qn"] == "handler.index" and f["sink_qn"] == "sink.run"
    )
    assert match["confidence"] == "medium"


def test_no_interprocedural_path_when_no_edge():
    """Source and sink exist but there is no CALLS edge between them."""
    g = nx.MultiDiGraph()
    _fn(g, "views.index", "x = request.args.get('x')")
    _fn(g, "db.run",      "cursor.execute(f'SELECT {x}')")
    # No edge added

    svc = TaintAnalysisService()
    sources = svc.find_source_functions(g)
    sinks   = svc.find_sink_functions(g)
    paths   = svc.find_interprocedural_paths(g, sources, sinks)

    assert paths == []


def test_max_depth_respected():
    """Paths deeper than max_depth=2 are not reported."""
    g = nx.MultiDiGraph()
    _fn(g, "src.entry", "x = request.args.get('x')")
    _fn(g, "a.hop1",   "return b(x)")
    _fn(g, "b.hop2",   "return c(x)")
    _fn(g, "snk.deep", "eval(x)")
    _call(g, "src.entry", "a.hop1")
    _call(g, "a.hop1",   "b.hop2")
    _call(g, "b.hop2",   "snk.deep")

    svc = TaintAnalysisService()
    sources = svc.find_source_functions(g)
    sinks   = svc.find_sink_functions(g)
    paths   = svc.find_interprocedural_paths(g, sources, sinks, max_depth=2)

    # 3-hop path exceeds max_depth=2 — should not appear
    assert not any(
        f["source_qn"] == "src.entry" and f["sink_qn"] == "snk.deep"
        for f in paths
    )


# ---------------------------------------------------------------------------
# run() — end-to-end + deduplication
# ---------------------------------------------------------------------------

def test_run_deduplicates_same_pair():
    """If source→sink is reachable via two paths, run() keeps only one finding."""
    g = nx.MultiDiGraph()
    _fn(g, "views.index", "x = request.args.get('x')")
    _fn(g, "snk.run",     "eval(x)")
    # Two different paths to the same sink
    _fn(g, "mid.a",       "return snk_run(x)")
    _fn(g, "mid.b",       "return snk_run(x)")
    _call(g, "views.index", "mid.a")
    _call(g, "views.index", "mid.b")
    _call(g, "mid.a",       "snk.run")
    _call(g, "mid.b",       "snk.run")

    svc = TaintAnalysisService()
    findings = svc.run(g)

    pairs = [(f["source_qn"], f["sink_qn"]) for f in findings]
    assert pairs.count(("views.index", "snk.run")) == 1


def test_run_empty_when_no_sources():
    g = nx.MultiDiGraph()
    _fn(g, "db.run", "cursor.execute(f'SELECT {x}')")
    svc = TaintAnalysisService()
    assert svc.run(g) == []


def test_run_empty_when_no_sinks():
    g = nx.MultiDiGraph()
    _fn(g, "views.index", "x = request.args.get('x')")
    svc = TaintAnalysisService()
    assert svc.run(g) == []


def test_run_empty_graph():
    g = nx.MultiDiGraph()
    svc = TaintAnalysisService()
    assert svc.run(g) == []
