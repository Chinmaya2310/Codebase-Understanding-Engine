"""Base parser class shared by all language parsers."""
from __future__ import annotations
import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from tree_sitter import Language, Node, Parser


@dataclass
class ParsedElement:
    element_type: str
    name: str
    qualified_name: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    source_code: str = ""
    docstring: Optional[str] = None
    signature: Optional[str] = None
    target: Optional[str] = None
    parent_qualified_name: Optional[str] = None


@dataclass
class ParseResult:
    file_path: str
    language: str
    elements: list[ParsedElement] = field(default_factory=list)
    line_count: int = 0
    error: Optional[str] = None


class BaseParser(abc.ABC):
    language_name: str = "unknown"
    file_extensions: tuple[str, ...] = ()

    def __init__(self) -> None:
        self._parser = Parser()
        self._ts_language = self._load_language()
        self._parser.language = self._ts_language

    @abc.abstractmethod
    def _load_language(self) -> Language: ...

    @abc.abstractmethod
    def _walk(self, node: Node, source: bytes, result: ParseResult, parent_qn: Optional[str]) -> None: ...

    def supports(self, file_path: str) -> bool:
        return file_path.endswith(self.file_extensions)

    def parse_file(self, file_path: str) -> ParseResult:
        path = Path(file_path)
        result = ParseResult(file_path=file_path, language=self.language_name)
        try:
            source_bytes = path.read_bytes()
        except OSError as e:
            result.error = f"Cannot read file: {e}"
            return result
        try:
            result.line_count = source_bytes.count(b"\n") + 1
            tree = self._parser.parse(source_bytes)
            module_qn = path.stem
            result.elements.append(ParsedElement(
                element_type="module", name=path.name, qualified_name=module_qn,
                file_path=file_path, language=self.language_name,
                start_line=1, end_line=result.line_count,
            ))
            self._walk(tree.root_node, source_bytes, result, parent_qn=module_qn)
        except Exception as e:
            result.error = f"Parse error: {e}"
        return result

    @staticmethod
    def _text(node: Node, source: bytes) -> str:
        return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def _line_range(node: Node) -> tuple[int, int]:
        return node.start_point[0] + 1, node.end_point[0] + 1
