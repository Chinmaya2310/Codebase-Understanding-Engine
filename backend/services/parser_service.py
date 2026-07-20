"""Parser orchestration."""
from __future__ import annotations
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.parsers.base_parser import BaseParser, ParseResult
from backend.parsers.python_parser import PythonParser
from backend.parsers.javascript_parser import JavaScriptParser, TypeScriptParser
from backend.parsers.java_parser import JavaParser
from backend.parsers.go_parser import GoParser

logger = logging.getLogger(__name__)


class ParserService:
    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {
            "python": PythonParser(),
            "javascript": JavaScriptParser(),
            "typescript": TypeScriptParser(),
            "java": JavaParser(),
            "go": GoParser(),
        }

    def parse_files(self, files_by_language: dict[str, list[str]]) -> list[ParseResult]:
        results: list[ParseResult] = []
        tasks: list[tuple[BaseParser, str]] = []
        for lang, files in files_by_language.items():
            parser = self._parsers.get(lang)
            if parser is None:
                continue
            for fp in files:
                tasks.append((parser, fp))
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(p.parse_file, fp): fp for p, fp in tasks}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    fp = futures[future]
                    results.append(ParseResult(file_path=fp, language="unknown", error=str(e)))
        return results

    @staticmethod
    def summarize(results) -> dict[str, int]:
        tf = tl = te = err = 0
        for r in results:
            tf += 1; tl += r.line_count; te += len(r.elements)
            if r.error: err += 1
        return {"total_files": tf, "total_lines": tl, "total_elements": te, "errors": err}
