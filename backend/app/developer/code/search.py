"""Bounded code search and secure file reading within approved repositories."""

import os
from pathlib import Path

from app.core.config import Settings, get_settings
from app.developer.git.safety import (
    PathSecurityError,
    redact_secrets,
    validate_file_path,
    validate_repo_path,
)
from app.developer.schemas import CodeFileContent, CodeSearchMatch, CodeSearchResult

# Directories always excluded from code search
IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
}

# Binary file extensions that should not be scanned as text
BINARY_EXTENSIONS = {
    ".exe", ".bin", ".dll", ".so", ".dylib", ".iso", ".zip", ".tar", ".gz",
    ".7z", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".mp3",
    ".mp4", ".wav", ".ogg", ".woff", ".woff2", ".ttf", ".eot", ".pyc", ".pyo",
}


def is_binary_file(file_path: Path, sample_size: int = 1024) -> bool:
    """Check if file is binary by extension or null-byte detection."""
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(sample_size)
            return b"\x00" in chunk
    except Exception:
        return True


def search_code_in_repository(
    repo_path: str,
    query: str,
    sub_path: str | None = None,
    settings: Settings | None = None,
) -> CodeSearchResult:
    """Search for string or pattern across text files in an approved repository.

    SECURITY:
    - Path validated against approved roots.
    - Ignored directories (.git, node_modules, etc.) bypassed.
    - Secret files bypassed.
    - Bounded to KAIRO_MAX_CODE_SEARCH_RESULTS (default 50).
    - Max file size bounded to KAIRO_MAX_CODE_SEARCH_FILE_SIZE (default 1MB).
    - Secret redaction applied to matching line content.
    """
    cfg = settings or get_settings()
    validated_repo = validate_repo_path(repo_path, cfg.get_approved_repo_roots())

    search_root = validated_repo
    if sub_path and sub_path.strip():
        search_root = validate_file_path(validated_repo, sub_path.strip())
        if not search_root.exists():
            raise PathSecurityError(f"Specified search path does not exist: {sub_path}")

    max_results = cfg.KAIRO_MAX_CODE_SEARCH_RESULTS
    max_file_size = cfg.KAIRO_MAX_CODE_SEARCH_FILE_SIZE
    matches: list[CodeSearchMatch] = []
    is_truncated = False

    clean_query = query.strip()
    if not clean_query:
        return CodeSearchResult(query="", total_matches=0, matches=[])

    # Case-insensitive search
    query_lower = clean_query.lower()

    if search_root.is_file():
        candidate_files = [search_root]
    else:
        candidate_files = []
        for root, dirs, files in os.walk(search_root):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES and not d.startswith(".")]
            for file_name in files:
                full_path = Path(root) / file_name
                candidate_files.append(full_path)

    for file_path in candidate_files:
        if len(matches) >= max_results:
            is_truncated = True
            break

        # Validate file safety (skips sensitive file patterns)
        try:
            rel_path = file_path.relative_to(validated_repo)
            validate_file_path(validated_repo, str(rel_path))
        except PathSecurityError:
            continue

        # Check file size
        try:
            if file_path.stat().st_size > max_file_size:
                continue
        except OSError:
            continue

        # Check binary
        if is_binary_file(file_path):
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line_no, line in enumerate(f, start=1):
                    if query_lower in line.lower():
                        clean_line = redact_secrets(line.strip())
                        matches.append(
                            CodeSearchMatch(
                                file_path=str(rel_path).replace("\\", "/"),
                                line_number=line_no,
                                line_content=clean_line[:300],  # Bound line width
                            )
                        )
                        if len(matches) >= max_results:
                            is_truncated = True
                            break
        except Exception:
            continue

    return CodeSearchResult(
        query=clean_query,
        total_matches=len(matches),
        matches=matches,
        is_truncated=is_truncated,
    )


def read_code_file(
    repo_path: str,
    file_path: str,
    max_lines: int = 1000,
    settings: Settings | None = None,
) -> CodeFileContent:
    """Safely read text file content from an approved repository.

    SECURITY:
    - Path traversal and symlink escapes rejected.
    - Prohibited sensitive credential files (.env, keys) rejected.
    - Device files rejected.
    - Binary files rejected.
    - File size bounded.
    - Output sanitized with secret redaction.
    """
    cfg = settings or get_settings()
    validated_repo = validate_repo_path(repo_path, cfg.get_approved_repo_roots())
    validated_target = validate_file_path(validated_repo, file_path)

    if not validated_target.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist in repository.")

    if not validated_target.is_file():
        raise PathSecurityError(f"Path '{file_path}' is not a regular file.")

    # Size check (max 1MB)
    stat = validated_target.stat()
    if stat.st_size > cfg.KAIRO_MAX_CODE_SEARCH_FILE_SIZE:
        raise PathSecurityError(
            f"File '{file_path}' exceeds size limit ({stat.st_size} bytes > {cfg.KAIRO_MAX_CODE_SEARCH_FILE_SIZE} bytes)."
        )

    # Binary check
    if is_binary_file(validated_target):
        raise PathSecurityError(f"File '{file_path}' is a binary file and cannot be displayed as text.")

    try:
        with open(validated_target, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as exc:
        raise RuntimeError(f"Failed to read file '{file_path}': {exc}") from exc

    total_lines = len(lines)
    is_truncated = False

    if total_lines > max_lines:
        lines = lines[:max_lines]
        is_truncated = True

    raw_content = "".join(lines)
    sanitized_content = redact_secrets(raw_content)

    rel_path_str = str(validated_target.relative_to(validated_repo)).replace("\\", "/")

    return CodeFileContent(
        repo_path=str(validated_repo),
        file_path=rel_path_str,
        content=sanitized_content,
        total_lines=total_lines,
        size_bytes=stat.st_size,
        is_truncated=is_truncated,
    )
