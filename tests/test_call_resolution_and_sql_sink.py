"""
Regression tests for the two causes of taint false positives found on DVPWA:
  1. calls resolved by method name only (Course.create -> Student.create)
  2. parameterised queries (execute("... %s", params)) treated as SQL sinks
"""
import textwrap

import pytest

from backend.parsers.python_parser import PythonParser
from backend.services.graph_service import GraphService
from backend.services.taint_analysis_service import TaintAnalysisService
from backend.services.taint_patterns import SINKS

SQL_SINK = next(m for m, label, _ in SINKS["python"] if label == "sql_dynamic_query")


def _graph(tmp_path, files: dict[str, str]):
    parser = PythonParser()
    results = []
    for name, code in files.items():
        path = tmp_path / name
        path.write_text(textwrap.dedent(code))
        results.append(parser.parse_file(str(path)))
    return GraphService().build_graph(results)


def _calls(graph, caller):
    return sorted(t for _, t, d in graph.out_edges(caller, data=True) if d["edge_type"] == "calls")


# ── call resolution ──────────────────────────────────────────────────────────

DAO = """
class Student:
    async def get(conn, id_): ...
    async def create(conn, name): ...

class Course:
    async def get(conn, id_): ...
    async def create(conn, title): ...
"""


def test_class_receiver_resolves_to_that_class(tmp_path):
    g = _graph(tmp_path, {"dao.py": DAO, "views.py": """
        from dao import Course
        async def courses(request):
            await Course.create(conn, title)
    """})
    assert _calls(g, "views.courses") == ["dao.Course.create"]


def test_unknown_receiver_is_not_resolved(tmp_path):
    g = _graph(tmp_path, {"dao.py": DAO, "views.py": """
        async def index(request):
            last = session.get('last_visited')
            name = data.get('name')
    """})
    assert _calls(g, "views.index") == []


def test_self_call_resolves_within_enclosing_class(tmp_path):
    g = _graph(tmp_path, {"svc.py": """
        class A:
            def run(self):
                self.helper()
            def helper(self): ...
        class B:
            def helper(self): ...
    """})
    assert _calls(g, "svc.A.run") == ["svc.A.helper"]


def test_bare_call_prefers_same_module(tmp_path):
    g = _graph(tmp_path, {
        "a.py": "def util(): ...\ndef main():\n    util()\n",
        "b.py": "def util(): ...\n",
    })
    assert _calls(g, "a.main") == ["a.util"]


def test_module_receiver_resolves_to_module_function(tmp_path):
    g = _graph(tmp_path, {
        "helpers.py": "def slugify(s): ...\n",
        "app.py": "import helpers\ndef handler():\n    helpers.slugify('x')\n",
    })
    assert _calls(g, "app.handler") == ["helpers.slugify"]


# ── SQL sink ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("code", [
    # DVPWA Student.create: % operator on the query string
    """
    q = ("INSERT INTO students (name) "
         "VALUES ('%(name)s')" % {'name': name})
    cur.execute(q)
    """,
    "cursor.execute(f'SELECT * FROM users WHERE id={uid}')",
    "cursor.execute('SELECT * FROM t WHERE a = {}'.format(a))",
    "cursor.execute('SELECT * FROM t WHERE a = ' + a)",
    "query = 'DELETE FROM users WHERE id = %s' % uid",
])
def test_dynamic_sql_is_sink(code):
    assert SQL_SINK.search(textwrap.dedent(code))


@pytest.mark.parametrize("code", [
    # DVPWA Student.get: parameterised, safe
    """
    await cur.execute(
        'SELECT id, name FROM students WHERE id = %s',
        (id_,),
    )
    """,
    # DVPWA Student.get_many: literal-only building, params passed separately
    """
    q = 'SELECT id, name FROM students'
    q += ' LIMIT + %(limit)s '
    await cur.execute(q, params)
    """,
    "cursor.execute('SELECT * FROM t WHERE a = %(a)s', {'a': a})",
    "msg = 'Hello %s' % name",
])
def test_parameterised_or_non_sql_is_not_sink(code):
    assert not SQL_SINK.search(textwrap.dedent(code))


# ── end to end: the DVPWA false positives are gone ───────────────────────────

def test_end_to_end_only_real_injection_reported(tmp_path):
    g = _graph(tmp_path, {
        "student.py": """
            class Student:
                async def get(conn, id_):
                    async with conn.cursor() as cur:
                        await cur.execute('SELECT id, name FROM students WHERE id = %s', (id_,))
                async def create(conn, name):
                    q = ("INSERT INTO students (name) "
                         "VALUES ('%(name)s')" % {'name': name})
                    async with conn.cursor() as cur:
                        await cur.execute(q)
        """,
        "course.py": """
            class Course:
                async def create(conn, title):
                    async with conn.cursor() as cur:
                        await cur.execute('INSERT INTO courses (title) VALUES (%(title)s)', {'title': title})
        """,
        "views.py": """
            from student import Student
            from course import Course
            async def students(request):
                data = await request.post()
                await Student.create(conn, data['name'])
            async def courses(request):
                data = await request.post()
                await Course.create(conn, data['title'])
            async def evaluate(request):
                data = await request.post()
                student = await Student.get(conn, data['id'])
        """,
    })
    findings = TaintAnalysisService().run(g)
    assert [(f["source_qn"], f["sink_qn"]) for f in findings] == [
        ("views.students", "student.Student.create"),
    ]
