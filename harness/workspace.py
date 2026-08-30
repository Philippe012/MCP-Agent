from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

REPO_ROOT = Path(__file__).resolve().parents[1]

# What a fresh clone of the sandboxed repo contains. Order doesn't matter;
# missing optional paths are skipped. Note this excludes
# src/mcp_rl_env/server.py and tools.py - those implement the MCP
# environment itself (harness plumbing), not the inventory service the
# task is about, so the agent never sees them as part of "the repository".
# inventory.py itself isn't listed here - it gets written directly below
# from the buggy seed, so copying the fixed version first would be wasted
# work.
_SEED_INCLUDE = [
    "src/mcp_rl_env/__init__.py",
    "tests/test_inventory.py",
    "tasks",
    "requirements.txt",
    "pyproject.toml",
]


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{proc.stdout}\n{proc.stderr}")


def make_episode_workspace(base_dir: Path | None = None, episode_id: str | None = None) -> Path:
    """Materialize a fresh, isolated copy of the seeded (buggy) repository.

    Returns the path to the new workspace. The caller owns cleanup.
    """
    episode_id = episode_id or uuid.uuid4().hex[:12]
    base_dir = base_dir or Path(tempfile.gettempdir()) / "mcp_rl_env_runs"
    workspace = base_dir / episode_id
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    for rel in _SEED_INCLUDE:
        src = REPO_ROOT / rel
        if not src.exists():
            continue
        dst = workspace / rel
        if src.is_dir():
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Overwrite the fixed inventory.py with the buggy seed version so there
    # is a real bug for the agent to find and fix.
    buggy = (REPO_ROOT / "seed" / "inventory_buggy.py").read_text(encoding="utf-8")
    (workspace / "src" / "mcp_rl_env" / "inventory.py").write_text(buggy, encoding="utf-8")

    # Pre-task state has no regression test yet - adding one is part of the task.
    regression = workspace / "tests" / "test_task_regression.py"
    if regression.exists():
        regression.unlink()

    # Make the workspace a real git repo so git_diff is meaningful.
    _run(["git", "init", "-q"], cwd=workspace)
    _run(["git", "config", "user.email", "seed@example.invalid"], cwd=workspace)
    _run(["git", "config", "user.name", "seed"], cwd=workspace)
    _run(["git", "add", "-A"], cwd=workspace)
    _run(["git", "commit", "-q", "-m", "seed: buggy inventory search"], cwd=workspace)

    return workspace


def cleanup(workspace: Path) -> None:
    shutil.rmtree(workspace, ignore_errors=True)
