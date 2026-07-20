"""Python AST parser using tree-sitter."""
from __future__ import annotations
from typing import Optional
import tree_sitter_python as tspython
from tree_sitter import Language, Node
from backend.parsers.base_parser import BaseParser, ParseResult, ParsedElement


class PythonParser(BaseParser):
    language_name = "python"
    file_extensions = (".py",)

    def _load_language(self) -> Language:
        return Language(tspython.language())

    def _walk(self, node: Node, source: bytes, result: ParseResult, parent_qn: Optional[str]) -> None:
        for child in node.children:
            ct = child.type
            if ct == "class_definition":
                name = self._child_text(child, "name", source)
                qn = f"{parent_qn}.{name}" if parent_qn else name
                s, e = self._line_range(child)
                result.elements.append(ParsedElement(
                    element_type="class", name=name, qualified_name=qn,
                    file_path=result.file_path, language=self.language_name,
                    start_line=s, end_line=e, source_code=self._text(child, source),
                    docstring=self._docstring(child, source), parent_qualified_name=parent_qn,
                ))
                self._walk(child, source, result, qn)
            elif ct == "function_definition":
                name = self._child_text(child, "name", source)
                qn = f"{parent_qn}.{name}" if parent_qn else name
                s, e = self._line_range(child)
                is_method = parent_qn is not None and "." in (parent_qn or "")
                result.elements.append(ParsedElement(
                    element_type="method" if is_method else "function",
                    name=name, qualified_name=qn,
                    file_path=result.file_path, language=self.language_name,
                    start_line=s, end_line=e, source_code=self._text(child, source),
                    docstring=self._docstring(child, source),
                    signature=self._signature(child, source), parent_qualified_name=parent_qn,
                ))
                self._walk(child, source, result, qn)
            elif ct in ("import_statement", "import_from_statement"):
                s, e = self._line_range(child)
                for t in self._import_targets(child, source):
                    result.elements.append(ParsedElement(
                        element_type="import", name=t,
                        qualified_name=f"{parent_qn}::import::{t}",
                        file_path=result.file_path, language=self.language_name,
                        start_line=s, end_line=e, target=t, parent_qualified_name=parent_qn,
                    ))
            elif ct == "call":
                callee = self._call_name(child, source)
                if callee:
                    s, e = self._line_range(child)
                    result.elements.append(ParsedElement(
                        element_type="call", name=callee,
                        qualified_name=f"{parent_qn}::call::{callee}::{s}",
                        file_path=result.file_path, language=self.language_name,
                        start_line=s, end_line=e, target=callee, parent_qualified_name=parent_qn,
                    ))
                self._walk(child, source, result, parent_qn)
            else:
                self._walk(child, source, result, parent_qn)

    def _child_text(self, node: Node, field: str, source: bytes) -> str:
        n = node.child_by_field_name(field)
        return self._text(n, source) if n else ""

    def _signature(self, node: Node, source: bytes) -> str:
        name = self._child_text(node, "name", source)
        params = node.child_by_field_name("parameters")
        return f"def {name}{self._text(params, source) if params else '()'}"

    def _docstring(self, node: Node, source: bytes):
        body = node.child_by_field_name("body")
        if body and body.children:
            first = body.children[0]
            if first.type == "expression_statement" and first.children:
                expr = first.children[0]
                if expr.type == "string":
                    return self._text(expr, source).strip("\"'").strip()
        return None

    def _import_targets(self, node: Node, source: bytes) -> list[str]:
        targets = []
        if node.type == "import_statement":
            for c in node.children:
                if c.type == "dotted_name":
                    targets.append(self._text(c, source))
        elif node.type == "import_from_statement":
            mod = node.child_by_field_name("module_name")
            mod_text = self._text(mod, source) if mod else ""
            for c in node.children:
                if c.type == "dotted_name" and c != mod:
                    targets.append(f"{mod_text}.{self._text(c, source)}" if mod_text else self._text(c, source))
            if not targets and mod_text:
                targets.append(mod_text)
        return targets

    def _call_name(self, node: Node, source: bytes):
        fn = node.child_by_field_name("function")
        if not fn:
            return None
        if fn.type == "identifier":
            return self._text(fn, source)
        if fn.type == "attribute":
            attr = fn.child_by_field_name("attribute")
            return self._text(attr, source) if attr else None
        return None
