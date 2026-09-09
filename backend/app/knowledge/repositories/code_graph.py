"""Code dependency graph representing repository structure and symbol relationships."""

import logging
import os
from collections import defaultdict
from app.knowledge.repositories.code_intel import CodeIntelligence
from app.knowledge.schemas import CodeDependency, CodeSymbol

logger = logging.getLogger("kairo.knowledge.repositories.code_graph")


class CodeGraph:
    """In-memory semantic graph connecting files, modules, classes, and functions."""

    def __init__(self) -> None:
        self._intel = CodeIntelligence()
        self._symbols_by_name: dict[str, list[CodeSymbol]] = defaultdict(list)
        self._symbols_by_file: dict[str, list[CodeSymbol]] = defaultdict(list)
        self._dependencies_by_source: dict[str, list[CodeDependency]] = defaultdict(list)
        self._dependencies_by_target: dict[str, list[CodeDependency]] = defaultdict(list)
        self._indexed_files: set[str] = set()

    def index_code_file(self, file_path: str, code: str, language: str = "python") -> None:
        """Parse and index a single source file into the graph."""
        # Clear previous records for file
        self._remove_file(file_path)

        symbols = self._intel.extract_symbols(code, file_path, language)
        for sym in symbols:
            self._symbols_by_name[sym.name.lower()].append(sym)
            self._symbols_by_file[file_path].append(sym)

        deps = self._intel.extract_dependencies(code, file_path)
        for dep in deps:
            self._dependencies_by_source[file_path].append(dep)
            self._dependencies_by_target[dep.target_file].append(dep)

        self._indexed_files.add(file_path)

    def _remove_file(self, file_path: str) -> None:
        if file_path not in self._indexed_files:
            return
        old_syms = self._symbols_by_file.pop(file_path, [])
        for s in old_syms:
            entries = self._symbols_by_name.get(s.name.lower(), [])
            self._symbols_by_name[s.name.lower()] = [e for e in entries if e.file_path != file_path]

        old_deps = self._dependencies_by_source.pop(file_path, [])
        for d in old_deps:
            t_entries = self._dependencies_by_target.get(d.target_file, [])
            self._dependencies_by_target[d.target_file] = [e for e in t_entries if e.source_file != file_path]
        self._indexed_files.discard(file_path)

    def find_symbol(self, symbol_name: str) -> list[CodeSymbol]:
        """Exact or case-insensitive symbol lookup."""
        return self._symbols_by_name.get(symbol_name.lower(), [])

    def search_symbols(self, query: str, limit: int = 10) -> list[CodeSymbol]:
        """Fuzzy search across symbol names and signatures."""
        q = query.lower()
        results: list[tuple[int, CodeSymbol]] = []
        for name, syms in self._symbols_by_name.items():
            for sym in syms:
                score = 0
                if name == q:
                    score = 100
                elif name.endswith(f".{q}") or q in name:
                    score = 70
                elif sym.docstring and q in sym.docstring.lower():
                    score = 40
                if score > 0:
                    results.append((score, sym))

        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def get_file_symbols(self, file_path: str) -> list[CodeSymbol]:
        """List all symbols defined within a file."""
        return self._symbols_by_file.get(file_path, [])

    def get_dependencies(self, file_path: str) -> list[CodeDependency]:
        """List all external files/symbols imported by this file."""
        return self._dependencies_by_source.get(file_path, [])

    def get_dependents(self, file_path: str) -> list[CodeDependency]:
        """List all files that import or depend on this file."""
        return self._dependencies_by_target.get(file_path, [])

    def total_symbols(self) -> int:
        return sum(len(syms) for syms in self._symbols_by_file.values())

    def total_files(self) -> int:
        return len(self._indexed_files)
