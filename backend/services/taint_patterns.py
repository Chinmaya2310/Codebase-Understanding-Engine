"""
Taint-source and taint-sink regex patterns, keyed by language.

Only Python patterns are shipped in this pass.  Adding JS / Java / Go is
additive: define a new key with the same list-of-tuples shape; the service
reads via SOURCES[language] and SINKS[language], so existing code is
untouched.

Source pattern shape:  (compiled_regex, short_label)
Sink pattern shape:    (matcher, short_label, vulnerability_class), where matcher
                       is a compiled regex or any object with ``search(code)``.
"""
from __future__ import annotations

import ast
import re
import textwrap


class _PythonSqlInjectionSink:
    """
    Sink matcher with the same ``search(code)`` interface as a compiled regex.

    A regex cannot tell the ``%s`` placeholder of a parameterised query
    (safe) from the ``%`` formatting operator (unsafe), so this parses the
    function body and looks for a *dynamic* string — one built at runtime via
    ``%``, an f-string with interpolation, ``.format()`` or ``+`` with a
    non-literal operand — that is either passed straight to
    ``execute``/``executemany``/``executescript``/``raw``, or contains SQL.
    """

    _EXEC_METHODS = {"execute", "executemany", "executescript", "raw"}
    _SQL = re.compile(
        r"\bselect\b.+\bfrom\b|\binsert\s+into\b|\bupdate\b.+\bset\b|\bdelete\s+from\b",
        re.IGNORECASE | re.DOTALL,
    )
    # Used only when the snippet cannot be parsed as Python.
    _FALLBACK = re.compile(
        r"\.execute\s*\(\s*f['\"]"
        r"|(INSERT|SELECT|UPDATE|DELETE)[^'\"]*['\"]\s*\)?\s*%\s*[\w\{\(\[]",
        re.DOTALL,
    )

    def search(self, code: str) -> bool:
        try:
            tree = ast.parse(textwrap.dedent(code))
        except SyntaxError:
            return bool(self._FALLBACK.search(code))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and self._is_exec_call(node):
                if node.args and self._literal_text(node.args[0]) is None and self._is_dynamic(node.args[0]):
                    return True
            elif self._is_dynamic(node) and self._SQL.search(self._template_text(node)):
                return True
        return False

    def _is_exec_call(self, node: ast.Call) -> bool:
        return isinstance(node.func, ast.Attribute) and node.func.attr in self._EXEC_METHODS

    def _is_dynamic(self, node: ast.AST) -> bool:
        if isinstance(node, ast.JoinedStr):
            return any(isinstance(v, ast.FormattedValue) for v in node.values)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            return self._literal_text(node.left) is not None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = self._literal_text(node.left), self._literal_text(node.right)
            has_literal = left is not None or right is not None or self._is_dynamic(node.left)
            has_runtime = left is None or right is None
            return has_literal and has_runtime
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "format"):
            return self._literal_text(node.func.value) is not None
        return False

    def _literal_text(self, node: ast.AST) -> str | None:
        """Text of a string literal, including implicit/explicit literal concatenation."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = self._literal_text(node.left), self._literal_text(node.right)
            if left is not None and right is not None:
                return left + right
        return None

    def _template_text(self, node: ast.AST) -> str:
        """The literal parts of a dynamic string, used to check for SQL keywords."""
        parts = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                parts.append(sub.value)
        return " ".join(parts)

# ---------------------------------------------------------------------------
# Python sources — functions that introduce untrusted / attacker-controlled data
# ---------------------------------------------------------------------------

_PYTHON_SOURCES: list[tuple[re.Pattern, str]] = [
    # Flask / Django request object parameters (GET, POST, JSON body, form, …)
    (re.compile(r"request\.(args|form|values|json|GET|POST|data)"), "http_request_params"),
    # aiohttp / Starlette style: await request.post() / request.json()
    # (lowercase method call, distinct from Flask's request.POST attribute)
    (re.compile(r"request\.(?:post|json|body|text)\s*\("), "aiohttp_request_post"),
    # Interactive stdin — trivially attacker-controlled in server contexts
    (re.compile(r"\binput\s*\("), "stdin_input"),
    # Command-line arguments — controlled by the process invoker
    (re.compile(r"sys\.argv"), "argv"),
    # Environment variables — controllable by the OS environment (e.g. Docker secrets leak)
    (re.compile(r"os\.environ\.get"), "env_var"),
    # HTTP request headers and cookies — frequently forged by attackers
    (re.compile(r"request\.(headers|cookies)"), "http_headers_cookies"),
]

# ---------------------------------------------------------------------------
# Python sinks — functions where tainted input reaching them is dangerous
# ---------------------------------------------------------------------------

_PYTHON_SINKS: list[tuple[re.Pattern, str, str]] = [
    # Code Injection — eval() executes arbitrary Python from a string
    (re.compile(r"\beval\s*\("), "eval", "Code Injection"),

    # Code Injection — exec() executes arbitrary Python statements
    (re.compile(r"\bexec\s*\("), "exec", "Code Injection"),

    # Command Injection — os.system() passes the argument directly to /bin/sh
    (re.compile(r"os\.system\s*\("), "os_system", "Command Injection"),

    # Command Injection — subprocess with shell=True: the command string is passed
    # to the shell; if it contains user input the attacker gains shell access
    (
        re.compile(r"subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True"),
        "subprocess_shell",
        "Command Injection",
    ),

    # SQL Injection — query text assembled from runtime values (%-operator,
    # f-string, .format(), concatenation).  AST-based so that parameterised
    # queries — execute("... WHERE id = %s", (id,)) — are NOT flagged.
    (_PythonSqlInjectionSink(), "sql_dynamic_query", "SQL Injection"),

    # Insecure Deserialization — pickle.loads on untrusted bytes executes arbitrary code
    (re.compile(r"pickle\.loads\s*\("), "pickle_loads", "Insecure Deserialization"),

    # Insecure Deserialization — yaml.load without SafeLoader can construct arbitrary objects
    (
        re.compile(r"yaml\.load\s*\((?!.*Loader=yaml\.SafeLoader)"),
        "yaml_load",
        "Insecure Deserialization",
    ),

    # Server-Side Template Injection (SSTI) — render_template_string with user-supplied
    # content lets the attacker execute Jinja2 expressions on the server
    (re.compile(r"render_template_string\s*\("), "render_template_string", "SSTI"),
]

# ---------------------------------------------------------------------------
# Public dictionaries — keyed by language string (lower-case)
# ---------------------------------------------------------------------------

SOURCES: dict[str, list[tuple[re.Pattern, str]]] = {
    "python": _PYTHON_SOURCES,
    # "javascript": _JS_SOURCES,   # TODO: add in next pass
    # "java":       _JAVA_SOURCES,
    # "go":         _GO_SOURCES,
}

SINKS: dict[str, list[tuple[re.Pattern, str, str]]] = {
    "python": _PYTHON_SINKS,
    # "javascript": _JS_SINKS,
    # "java":       _JAVA_SINKS,
    # "go":         _GO_SINKS,
}
