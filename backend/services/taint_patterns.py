"""
Taint-source and taint-sink regex patterns, keyed by language.

Only Python patterns are shipped in this pass.  Adding JS / Java / Go is
additive: define a new key with the same list-of-tuples shape; the service
reads via SOURCES[language] and SINKS[language], so existing code is
untouched.

Source pattern shape:  (compiled_regex, short_label)
Sink pattern shape:    (compiled_regex, short_label, vulnerability_class)
"""
from __future__ import annotations

import re

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

    # SQL Injection — %-formatted or f-string query strings interpolated directly
    # into cursor.execute().  Heuristic: false positives acceptable (noted limitation).
    (
        re.compile(r"\.execute\s*\(\s*[\"\']*.*%s|\.execute\s*\(\s*f['\"]"),
        "sql_execute",
        "SQL Injection",
    ),
    # SQL Injection — Python % string-formatting operator applied to a SQL string.
    # Pattern: closing quote followed by `% {dict}` or `% (tuple)` or `% var`.
    # Detects e.g. `"INSERT INTO t VALUES ('%s')" % user_input`.
    # Uses re.DOTALL so the SQL keyword and the `%` operator can span multiple lines
    # in a parenthesised multi-line string expression.
    # NOTE: the pattern requires a SQL keyword to reduce false positives;
    # pure Python string formatting unrelated to SQL will not match.
    (
        re.compile(
            r"(INSERT|SELECT|UPDATE|DELETE).*['\"]\s*%\s*[\w\{\(\[]",
            re.DOTALL,
        ),
        "sql_percent_format",
        "SQL Injection",
    ),

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
