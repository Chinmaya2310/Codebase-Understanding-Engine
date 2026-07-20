"""Java parser."""
from __future__ import annotations
from typing import Optional
import tree_sitter_java as tsjava
from tree_sitter import Language, Node
from backend.parsers.base_parser import BaseParser, ParseResult, ParsedElement


class JavaParser(BaseParser):
    language_name = "java"
    file_extensions = (".java",)

    def _load_language(self) -> Language:
        return Language(tsjava.language())

    def _walk(self, node: Node, source: bytes, result: ParseResult, parent_qn: Optional[str]) -> None:
        for child in node.children:
            ct = child.type
            if ct in ("class_declaration", "interface_declaration", "enum_declaration"):
                name = self._field(child, "name", source) or "Anonymous"
                qn = f"{parent_qn}.{name}" if parent_qn else name
                s, e = self._line_range(child)
                etype = "interface" if ct == "interface_declaration" else "class"
                result.elements.append(ParsedElement(
                    element_type=etype, name=name, qualified_name=qn,
                    file_path=result.file_path, language=self.language_name,
                    start_line=s, end_line=e, source_code=self._text(child, source),
                    parent_qualified_name=parent_qn,
                ))
                self._walk(child, source, result, qn)
            elif ct == "method_declaration":
                name = self._field(child, "name", source) or "method"
                qn = f"{parent_qn}.{name}" if parent_qn else name
                s, e = self._line_range(child)
                result.elements.append(ParsedElement(
                    element_type="method", name=name, qualified_name=qn,
                    file_path=result.file_path, language=self.language_name,
                    start_line=s, end_line=e, source_code=self._text(child, source),
                    parent_qualified_name=parent_qn,
                ))
                self._walk(child, source, result, qn)
            elif ct == "import_declaration":
                s, e = self._line_range(child)
                module = self._text(child, source).replace("import", "").replace(";", "").strip()
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
