"""Deterministic static analysis for repositories."""

import ast
import os
import re
from pathlib import Path

from app.core.config import Settings, get_settings
from app.developer.code.search import IGNORED_DIRECTORIES, is_binary_file
from app.developer.git.safety import validate_repo_path
from app.developer.schemas import CodeAnalysisResult, TodoItem

TODO_REGEX = re.compile(r"\b(TODO|FIXME|HACK|BUG|OPTIMIZE|XXX)\b\s*[:\-]?\s*(.*)", re.IGNORECASE)


class CodeAnalysisService:
    """Provides deterministic, grounded code analysis without LLM inference."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze_repository(
        self,
        repo_path: str,
        max_depth: int = 3,
        max_files_to_scan: int = 500,
    ) -> CodeAnalysisResult:
        """Run deterministic analysis on an approved repository.

        Grounded facts:
        - Extension/language distribution
        - Total lines
        - Detected TODO/FIXME comments
        - Python syntax errors via AST parsing
        - Bounded directory structure summary
        """
        validated_repo = validate_repo_path(repo_path, self.settings.get_approved_repo_roots())

        languages: dict[str, int] = {}
        total_files = 0
        total_lines = 0
        todo_items: list[TodoItem] = []
        syntax_errors: list[str] = []
        structure_lines: list[str] = []

        # Directory structure summary (bounded to max_depth)
        for root, dirs, files in os.walk(validated_repo):
            rel_path = Path(root).relative_to(validated_repo)
            depth = len(rel_path.parts)
            if depth >= max_depth:
                dirs[:] = []  # stop descending
                continue

            dirs[:] = sorted([d for d in dirs if d not in IGNORED_DIRECTORIES and not d.startswith(".")])

            indent = "  " * depth
            folder_name = rel_path.name or validated_repo.name
            structure_lines.append(f"{indent}{folder_name}/")

            for f_name in sorted(files):
                if f_name.startswith("."):
                    continue
                file_path = Path(root) / f_name
                ext = file_path.suffix.lower() or "no_extension"
                languages[ext] = languages.get(ext, 0) + 1
                total_files += 1

                if total_files <= max_files_to_scan and not is_binary_file(file_path):
                    self._scan_file_lines_and_todos(
                        file_path=file_path,
                        rel_path=str(file_path.relative_to(validated_repo)).replace("\\", "/"),
                        todo_items=todo_items,
                        syntax_errors=syntax_errors,
                        counter={"total_lines": total_lines},
                    )
                    total_lines = self._get_total_lines_safe(file_path, total_lines)

                if depth < max_depth - 1 and len(structure_lines) < 60:
                    structure_lines.append(f"{indent}  {f_name}")

        return CodeAnalysisResult(
            repo_path=str(validated_repo),
            languages=languages,
            total_files=total_files,
            total_lines=total_lines,
            todo_items=todo_items[:100],  # Bound TODO results
            syntax_valid=(len(syntax_errors) == 0),
            syntax_errors=syntax_errors[:20],
            directory_structure=structure_lines[:60],
        )

    def _get_total_lines_safe(self, file_path: Path, current_total: int) -> int:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return current_total + sum(1 for _ in f)
        except Exception:
            return current_total

    def _scan_file_lines_and_todos(
        self,
        file_path: Path,
        rel_path: str,
        todo_items: list[TodoItem],
        syntax_errors: list[str],
        counter: dict[str, int],
    ) -> None:
        """Inspect a file for TODOs and Python syntax validity."""
        # AST syntax check for Python files
        if file_path.suffix.lower() == ".py":
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                ast.parse(content, filename=str(file_path))
            except SyntaxError as syn_err:
                syntax_errors.append(f"{rel_path}:{syn_err.lineno}: SyntaxError: {syn_err.msg}")
            except Exception:
                pass

        # Scan for TODO markers
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line_idx, line in enumerate(f, start=1):
                    match = TODO_REGEX.search(line)
                    if match:
                        marker = match.group(1).upper()
                        text = match.group(2).strip()[:150]
                        todo_items.append(
                            TodoItem(
                                marker=marker,
                                file_path=rel_path,
                                line_number=line_idx,
                                text=text,
                            )
                        )
                        if len(todo_items) >= 100:
                            break
        except Exception:
            pass
