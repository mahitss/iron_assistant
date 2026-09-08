"""Unit and integration tests for code search, secure file reading, and static analysis."""

from pathlib import Path

import pytest

from app.core.config import Settings
from app.developer.code.analysis import CodeAnalysisService
from app.developer.code.search import read_code_file, search_code_in_repository
from app.developer.git.safety import PathSecurityError, redact_secrets


@pytest.fixture
def sample_project(tmp_path: Path):
    """Create a structured mock project with source files, ignored folders, and secrets."""
    proj = tmp_path / "mock_project"
    proj.mkdir()

    # Source code
    src = proj / "src"
    src.mkdir()
    (src / "main.py").write_text(
        "import os\n\n# TODO: Add caching\ndef run():\n    token = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345'\n    return 42\n",
        encoding="utf-8",
    )
    (src / "utils.js").write_text(
        "// FIXME: handle null\nfunction add(a, b) {\n    return a + b;\n}\n",
        encoding="utf-8",
    )

    # Broken syntax python file
    (src / "broken.py").write_text("def syntax_error(:\n", encoding="utf-8")

    # Ignored directory: node_modules
    nm = proj / "node_modules" / "some_pkg"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text("// Should not be searched\nconst x = 'secret_in_nm';\n", encoding="utf-8")

    # Ignored directory: .git
    git_dir = proj / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\n\trepositoryformatversion = 0\n", encoding="utf-8")

    # Sensitive file: .env
    (proj / ".env").write_text("OPENAI_API_KEY=sk-1234567890abcdef1234567890abcdef\n", encoding="utf-8")

    # Binary file
    (src / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

    return proj


@pytest.fixture
def developer_settings(tmp_path: Path):
    return Settings(
        KAIRO_DEVELOPER_ENABLED=True,
        KAIRO_REPOSITORY_ROOTS=str(tmp_path),
        KAIRO_MAX_CODE_SEARCH_RESULTS=10,
        KAIRO_MAX_CODE_SEARCH_FILE_SIZE=50000,
    )


def test_code_search_finds_matches_and_skips_ignored(sample_project: Path, developer_settings: Settings):
    """Verify code search finds code in src and skips node_modules and .git."""
    res = search_code_in_repository(
        repo_path=str(sample_project),
        query="add",
        settings=developer_settings,
    )
    assert res.total_matches >= 1
    # Check that src/utils.js was found
    found_files = [m.file_path for m in res.matches]
    assert any("utils.js" in f for f in found_files)
    # Check that node_modules was NOT searched
    assert not any("node_modules" in f for f in found_files)


def test_code_search_redacts_secrets_in_matches(sample_project: Path, developer_settings: Settings):
    """Verify tokens matching patterns are redacted in search lines."""
    res = search_code_in_repository(
        repo_path=str(sample_project),
        query="token",
        settings=developer_settings,
    )
    assert res.total_matches >= 1
    content = res.matches[0].line_content
    assert "[REDACTED_GITHUB_TOKEN]" in content
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345" not in content


def test_read_code_file_valid(sample_project: Path, developer_settings: Settings):
    """Verify safe reading of regular code file."""
    res = read_code_file(
        repo_path=str(sample_project),
        file_path="src/utils.js",
        settings=developer_settings,
    )
    assert res.file_path == "src/utils.js"
    assert "function add(a, b)" in res.content
    assert res.total_lines >= 4


def test_read_code_file_rejects_sensitive_files(sample_project: Path, developer_settings: Settings):
    """Verify reading .env or private keys is rejected."""
    with pytest.raises(PathSecurityError):
        read_code_file(
            repo_path=str(sample_project),
            file_path=".env",
            settings=developer_settings,
        )


def test_read_code_file_rejects_path_traversal(sample_project: Path, developer_settings: Settings):
    """Verify path traversal (../../) is rejected."""
    with pytest.raises(PathSecurityError):
        read_code_file(
            repo_path=str(sample_project),
            file_path="../../some_file.txt",
            settings=developer_settings,
        )


def test_read_code_file_rejects_binary(sample_project: Path, developer_settings: Settings):
    """Verify binary files are rejected from text reading."""
    with pytest.raises(PathSecurityError):
        read_code_file(
            repo_path=str(sample_project),
            file_path="src/image.png",
            settings=developer_settings,
        )


def test_secret_redaction_patterns():
    """Verify secret redaction function masks API keys, tokens, and private keys."""
    text = (
        "Key: sk-1234567890abcdef1234567890\n"
        "GH: ghp_1234567890abcdef1234567890\n"
        "AWS: AKIA1234567890ABCDEF\n"
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummytoken\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----\n"
    )
    sanitized = redact_secrets(text)
    assert "[REDACTED_API_KEY]" in sanitized
    assert "[REDACTED_GITHUB_TOKEN]" in sanitized
    assert "[REDACTED_AWS_KEY]" in sanitized
    assert "[REDACTED_TOKEN]" in sanitized
    assert "[REDACTED_PRIVATE_KEY]" in sanitized


def test_deterministic_code_analysis(sample_project: Path, developer_settings: Settings):
    """Verify deterministic static analysis extracts languages, line counts, TODOs, and syntax errors."""
    service = CodeAnalysisService(settings=developer_settings)
    analysis = service.analyze_repository(str(sample_project))

    assert analysis.total_files >= 3
    assert ".py" in analysis.languages
    assert ".js" in analysis.languages

    # Check TODO / FIXME detection
    todo_markers = [t.marker for t in analysis.todo_items]
    assert "TODO" in todo_markers
    assert "FIXME" in todo_markers

    # Check syntax validation detected broken.py
    assert analysis.syntax_valid is False
    assert any("broken.py" in err for err in analysis.syntax_errors)
