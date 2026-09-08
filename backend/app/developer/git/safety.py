"""Path security, symlink validation, and secret redaction for developer tools."""

import re
from pathlib import Path

# Sensitive file patterns that must never be read by Kairo
PROHIBITED_FILE_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"^id_rsa(\.pub)?$", re.IGNORECASE),
    re.compile(r"^id_ed25519(\.pub)?$", re.IGNORECASE),
    re.compile(r"^id_dsa(\.pub)?$", re.IGNORECASE),
    re.compile(r"^id_ecdsa(\.pub)?$", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
    re.compile(r".*\.pfx$", re.IGNORECASE),
    re.compile(r".*\.p12$", re.IGNORECASE),
    re.compile(r"^credentials(\.json)?$", re.IGNORECASE),
    re.compile(r"^service_account.*\.json$", re.IGNORECASE),
    re.compile(r"^\.git-credentials$", re.IGNORECASE),
    re.compile(r"^\.netrc$", re.IGNORECASE),
    re.compile(r".*token.*\.json$", re.IGNORECASE),
]

# Windows reserved device filenames
WINDOWS_DEVICE_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# Regex patterns for detecting and redacting secrets from diffs and files
SECRET_PATTERNS = [
    # Private Key blocks
    (re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    # GitHub personal access tokens
    (re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"), "[REDACTED_GITHUB_TOKEN]"),
    # OpenAI / OpenRouter style API keys
    (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"), "[REDACTED_API_KEY]"),
    # Generic Bearer tokens
    (re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}"), "Bearer [REDACTED_TOKEN]"),
    # AWS Access Key IDs
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # Password in URL credentials
    (re.compile(r"(https?://[^:\s]+:)([^@\s]+)(@)"), r"\1[REDACTED_PWD]\3"),
    # Secret assignment patterns like password = "...", api_key = "..."
    (re.compile(r'(?i)(api[_-]?key|secret|password|passwd|auth[_-]?token)\s*[:=]\s*["\']([^"\']{8,})["\']'), r'\1="[REDACTED_SECRET]"'),
]


class PathSecurityError(ValueError):
    """Raised when a path validation fails security constraints."""


def validate_repo_path(repo_path: str | Path, approved_roots: list[str]) -> Path:
    """Validate that repo_path is an existing directory inside approved_roots.

    Prevents:
    - Path traversal (`../../`)
    - Symlink escapes pointing outside approved roots
    - Access to unapproved roots
    - Null byte injections
    """
    if not repo_path or not str(repo_path).strip():
        raise PathSecurityError("Repository path cannot be empty.")

    raw_path_str = str(repo_path).strip()
    if "\x00" in raw_path_str:
        raise PathSecurityError("Null bytes in repository path are strictly forbidden.")

    # Canonicalize
    try:
        resolved_repo = Path(raw_path_str).resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise PathSecurityError(f"Repository path does not exist: {raw_path_str}") from exc

    if not resolved_repo.is_dir():
        raise PathSecurityError(f"Repository path is not a directory: {resolved_repo}")

    if not approved_roots:
        raise PathSecurityError("No repository roots configured (KAIRO_REPOSITORY_ROOTS). Access denied.")

    # Check against approved roots
    canonical_roots = [Path(root).resolve(strict=False) for root in approved_roots if root.strip()]
    is_approved = any(
        resolved_repo == root or root in resolved_repo.parents
        for root in canonical_roots
    )

    if not is_approved:
        raise PathSecurityError(
            f"Repository '{resolved_repo}' is not located inside any approved root: {canonical_roots}"
        )

    return resolved_repo


def validate_file_path(repo_path: Path, relative_file_path: str) -> Path:
    """Validate that relative_file_path stays strictly within repo_path and is not prohibited.

    Prevents:
    - Path traversal (`../../`)
    - Symlink escapes outside repo
    - Device files (CON, NUL, /dev)
    - Sensitive credential files (.env, keys)
    """
    if not relative_file_path or not relative_file_path.strip():
        raise PathSecurityError("File path cannot be empty.")

    if "\x00" in relative_file_path:
        raise PathSecurityError("Null bytes in file path are strictly forbidden.")

    target_path = (repo_path / relative_file_path).resolve(strict=False)

    # Check boundaries
    try:
        target_path.relative_to(repo_path)
    except ValueError as exc:
        raise PathSecurityError(f"Path traversal detected: '{relative_file_path}' escapes repository boundary.") from exc

    # Check device names
    base_name = target_path.stem.upper()
    if base_name in WINDOWS_DEVICE_NAMES:
        raise PathSecurityError(f"Access to device file '{base_name}' is strictly prohibited.")

    # Check sensitive files
    file_name = target_path.name
    for pattern in PROHIBITED_FILE_PATTERNS:
        if pattern.match(file_name):
            raise PathSecurityError(f"Access to sensitive file '{file_name}' is strictly prohibited.")

    return target_path


def redact_secrets(content: str) -> str:
    """Redact obvious secret patterns from text before returning to the model."""
    if not content:
        return content

    sanitized = content
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized
