"""Pure, root-parametrized implementations of the repository tools.

These functions are the single source of truth for what "list_files",
"read_file", "search_code", "write_file", "run_tests" and "git_diff" actually
do. `server.py` wraps them as MCP tools for a live agent session; the
evaluation harness in `harness/` calls them directly (no MCP transport
needed) so that a manually-driven or scripted episode behaves identically to
one driven through a real MCP client.

Keeping this logic in one place means there is no drift between "what the
MCP server does" and "what the benchmark harness measured" - an important
property for a reproducible, judge-runnable evaluation.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

IGNORED_DIR_PARTS = {".git", ".venv", "__pycache__"}


def _safe_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if root not in path.parents and path != root:
        raise ValueError("Path escapes repository")
    return path


def list_files(root: Path) -> list[str]:
    """List repository files available to the coding agent."""
    return sorted(
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and not any(part in IGNORED_DIR_PARTS for part in p.parts)
    )


def read_file(root: Path, path: str) -> str:
    """Read a text file from the repository."""
    return _safe_path(root, path).read_text(encoding="utf-8")


def search_code(root: Path, query: str) -> list[str]:
    """Find repository files containing a case-sensitive query."""
    matches = []
    for path in root.rglob("*.py"):
        if any(part in {".venv", "__pycache__"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        if query in text:
            matches.append(str(path.relative_to(root)))
    return sorted(matches)


def write_file(root: Path, path: str, content: str) -> str:
    """Write a repository text file."""
    target = _safe_path(root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"wrote {path}"


def run_tests(root: Path) -> dict:
    """Run the deterministic pytest suite."""
    env = {"PYTHONPATH": str(root / "src")}
    import os

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
        text=True,
        capture_output=True,
        env={**os.environ, **env},
        stdin=subprocess.DEVNULL,
    )
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def git_diff(root: Path) -> str:
    """Return the current git diff."""
    proc = subprocess.run(
        ["git", "diff", "--"], cwd=root, text=True, capture_output=True, stdin=subprocess.DEVNULL
    )
    return proc.stdout
