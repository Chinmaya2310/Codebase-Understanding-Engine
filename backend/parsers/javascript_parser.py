"""JavaScript/TypeScript parser."""
from __future__ import annotations
from typing import Optional
import tree_sitter_javascript as tsjs
from tree_sitter import Language, Node
from backend.parsers.base_parser import BaseParser, ParseResult, ParsedElement


class JavaScriptParser(BaseParser):
    language_name = "javascript"
    file_extensions = (".js", ".jsx", ".mjs", ".cjs")

    def _load_language(self) -> Language:
        return Language(tsjs.language())

    def _walk(self, node: Node, source: bytes, result: ParseResult, parent_qn: Optional[str]) -> None:
        for child in node.children:
            ct = child.type
            if ct == "class_declaration":
                name = self._field(child, "name", source) or "AnonymousClass"
                qn = f"{parent_qn}.{name}" if parent_qn else name
                s, e = self._line_range(child)
                result.elements.append(ParsedElement(
                    element_type="class", name=name, qualified_name=qn,
                    file_path=result.file_path, language=self.language_name,
                    start_line=s, end_line=e, source_code=self._text(child, source),
                    parent_qualified_name=parent_qn,
                ))
                self._walk(child, source, result, qn)
            elif ct in ("function_declaration", "method_definition"):
                name = self._field(child, "name", source) or "anonymous"
                qn = f"{parent_qn}.{name}" if parent_qn else name
                s, e = self._line_range(child)
                etype = "method" if ct == "method_definition" else "function"
                result.elements.append(ParsedElement(
                    element_type=etype, name=name, qualified_name=qn,
                    file_path=result.file_path, language=self.language_name,
                    start_line=s, end_line=e, source_code=self._text(child, source),
                    parent_qualified_name=parent_qn,
                ))
                self._walk(child, source, result, qn)
            elif ct == "import_statement":
                src = child.child_by_field_name("source")
                module = self._text(src, source).strip("'\"") if src else ""
                if module:
                    s, e = self._line_range(child)
                    result.elements.append(ParsedElement(
                        element_type="import", name=module,
                        qualified_name=f"{parent_qn}::import::{module}",
                        file_path=result.file_path, language=self.language_name,
                        start_line=s, end_line=e, target=module, parent_qualified_name=parent_qn,
                    ))
            else:
                self._walk(child, source, result, parent_qn)

    def _field(self, node: Node, field: str, source: bytes):
        n = node.child_by_field_name(field)
        return self._text(n, source) if n else None


class TypeScriptParser(JavaScriptParser):
    language_name = "typescript"
    file_extensions = (".ts", ".tsx")
