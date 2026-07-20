"""Go parser."""
from __future__ import annotations
from typing import Optional
import tree_sitter_go as tsgo
from tree_sitter import Language, Node
from backend.parsers.base_parser import BaseParser, ParseResult, ParsedElement


class GoParser(BaseParser):
    language_name = "go"
    file_extensions = (".go",)

    def _load_language(self) -> Language:
        return Language(tsgo.language())

    def _walk(self, node: Node, source: bytes, result: ParseResult, parent_qn: Optional[str]) -> None:
        for child in node.children:
            ct = child.type
            if ct == "type_declaration":
                for spec in child.children:
                    if spec.type == "type_spec":
                        nn = spec.child_by_field_name("name")
                        tn = spec.child_by_field_name("type")
                        if nn:
                            name = self._text(nn, source)
                            qn = f"{parent_qn}.{name}" if parent_qn else name
                            s, e = self._line_range(child)
                            etype = "struct" if tn and tn.type == "struct_type" else "interface"
                            result.elements.append(ParsedElement(
                                element_type=etype, name=name, qualified_name=qn,
                                file_path=result.file_path, language=self.language_name,
                                start_line=s, end_line=e, source_code=self._text(child, source),
                                parent_qualified_name=parent_qn,
                            ))
            elif ct in ("function_declaration", "method_declaration"):
                nn = child.child_by_field_name("name")
                name = self._text(nn, source) if nn else "func"
                qn = f"{parent_qn}.{name}" if parent_qn else name
                s, e = self._line_range(child)
                etype = "method" if ct == "method_declaration" else "function"
                result.elements.append(ParsedElement(
                    element_type=etype, name=name, qualified_name=qn,
                    file_path=result.file_path, language=self.language_name,
                    start_line=s, end_line=e, source_code=self._text(child, source),
                    parent_qualified_name=parent_qn,
                ))
                self._walk(child, source, result, qn)
            elif ct == "import_declaration":
                s, e = self._line_range(child)
                for pn in self._find_all(child, "interpreted_string_literal"):
                    module = self._text(pn, source).strip('"')
                    result.elements.append(ParsedElement(
                        element_type="import", name=module,
                        qualified_name=f"{parent_qn}::import::{module}",
                        file_path=result.file_path, language=self.language_name,
                        start_line=s, end_line=e, target=module, parent_qualified_name=parent_qn,
                    ))
            else:
                self._walk(child, source, result, parent_qn)

    def _find_all(self, node: Node, type_name: str) -> list[Node]:
        found = []
        for c in node.children:
            if c.type == type_name:
                found.append(c)
            found.extend(self._find_all(c, type_name))
        return found
