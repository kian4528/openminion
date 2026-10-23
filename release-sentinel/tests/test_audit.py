from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from release_sentinel.audit import inspect_repository


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def test_inspects_repository_without_reading_file_contents(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("sample project", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_sample.py").write_text("def test_sample(): pass\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial", "-q")
    (tmp_path / ".env.local").write_text("PRIVATE=do-not-read", encoding="utf-8")

    evidence = inspect_repository(tmp_path)

    assert evidence.is_git_repository is True
    assert evidence.working_tree_state == "dirty"
    assert "pyproject.toml" in evidence.manifest_files
    assert "tests/test_sample.py" in evidence.test_indicators
    assert evidence.documentation_present is True
    assert ".env.local" in evidence.sensitive_named_changes
    assert "PRIVATE=do-not-read" not in evidence.to_json()


def test_non_git_directory_is_supported(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")

    evidence = inspect_repository(tmp_path)

    assert evidence.is_git_repository is False
    assert evidence.working_tree_state == "not-a-git-repository"
    assert evidence.documentation_present is True


def test_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        inspect_repository(tmp_path / "missing")


def test_scanner_does_not_emit_file_contents(tmp_path: Path) -> None:
    secret_value = "EXAMPLE_SECRET_VALUE_123"
    (tmp_path / ".env").write_text(secret_value, encoding="utf-8")
    _git(tmp_path, "init", "-q")

    report = inspect_repository(tmp_path).to_json()

    assert secret_value not in report
    assert ".env" in report
