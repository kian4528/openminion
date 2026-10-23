from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

MAX_FILE_BYTES = 1_000_000
MANIFEST_NAMES = (
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
)
TEST_MARKERS = (
    "tests",
    "test",
    "spec",
    "pytest.ini",
    "tox.ini",
    "jest.config.js",
    "vitest.config.ts",
)
CI_MARKERS = (".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml")
SENSITIVE_PATH_PARTS = ("secret", "credential", "token", "private_key", ".env")


@dataclass(frozen=True)
class RepositoryEvidence:
    root: str
    is_git_repository: bool
    branch: str | None
    working_tree_state: str
    changed_paths: list[str]
    untracked_paths: list[str]
    manifest_files: list[str]
    test_indicators: list[str]
    ci_indicators: list[str]
    documentation_present: bool
    license_present: bool
    lockfiles: list[str]
    sensitive_named_changes: list[str]
    git_error: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def _run_git(root: Path, *args: str) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)


def inspect_repository(path: str | Path) -> RepositoryEvidence:
    root = Path(path).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Repository path is not a directory: {root}")

    git_code, top_level, git_error = _run_git(root, "rev-parse", "--show-toplevel")
    is_git = git_code == 0 and bool(top_level)
    if is_git:
        actual_root = Path(top_level).resolve()
        if actual_root != root:
            root = actual_root
        _, branch, _ = _run_git(root, "branch", "--show-current")
        _, status, status_error = _run_git(root, "status", "--porcelain=v1", "-uall")
        changed: list[str] = []
        untracked: list[str] = []
        for line in status.splitlines():
            if len(line) < 4:
                continue
            status_code = line[:2]
            file_path = line[3:]
            if " -> " in file_path:
                file_path = file_path.split(" -> ", 1)[1]
            normalized = file_path.replace("\\", "/")
            if status_code == "??":
                untracked.append(normalized)
            else:
                changed.append(normalized)
        git_error = status_error or git_error or None
        working_state = "clean" if not status else "dirty"
    else:
        branch = None
        changed = []
        untracked = []
        working_state = "not-a-git-repository"
        git_error = git_error or "Git metadata was not available."

    all_files: list[str] = []
    for item in root.rglob("*"):
        if not item.is_file():
            continue
        try:
            relative = item.relative_to(root).as_posix()
        except ValueError:
            continue
        parts = Path(relative).parts
        if any(part in {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox"} for part in parts):
            continue
        try:
            if item.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        all_files.append(relative)

    manifests = sorted(file for file in all_files if Path(file).name in MANIFEST_NAMES)
    test_indicators = sorted(
        file for file in all_files
        if any(part.lower() in {marker.lower() for marker in TEST_MARKERS} for part in Path(file).parts)
        or Path(file).name.lower() in {marker.lower() for marker in TEST_MARKERS}
    )
    ci_indicators = sorted(file for file in all_files if any(
        file == marker or file.startswith(marker.rstrip("/") + "/")
        for marker in CI_MARKERS
    ))
    lock_names = {"uv.lock", "poetry.lock", "pdm.lock", "Pipfile.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.lock", "go.sum"}
    lockfiles = sorted(file for file in all_files if Path(file).name in lock_names)
    docs_present = any(Path(file).name.lower() in {"readme", "readme.md", "readme.rst", "readme.txt"} for file in all_files)
    license_present = any(Path(file).name.lower().startswith(("license", "copying")) for file in all_files)
    changed_paths = sorted(set(changed))
    untracked_paths = sorted(set(untracked))
    sensitive_changes = sorted(
        path for path in changed_paths + untracked_paths
        if any(part in path.lower() for part in SENSITIVE_PATH_PARTS)
    )

    return RepositoryEvidence(
        root=str(root),
        is_git_repository=is_git,
        branch=branch or None,
        working_tree_state=working_state,
        changed_paths=changed_paths[:250],
        untracked_paths=untracked_paths[:250],
        manifest_files=manifests[:100],
        test_indicators=test_indicators[:100],
        ci_indicators=ci_indicators[:100],
        documentation_present=docs_present,
        license_present=license_present,
        lockfiles=lockfiles[:100],
        sensitive_named_changes=sensitive_changes[:100],
        git_error=git_error,
    )
