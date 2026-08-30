from __future__ import annotations

from pathlib import Path
import os
import shutil
import stat
import subprocess
import tempfile
import uuid

from harness.task_registry import DEFAULT_TASK_ID, get_task

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{proc.stdout}\n{proc.stderr}")


def _force_rmtree(path: Path) -> None:
    """Delete a directory tree that may be a real git repository.

    Plain shutil.rmtree fails on Windows here: git writes .git/objects/*
    read-only by design, and rmtree does not clear that attribute before
    unlinking. Discovered by running eval/reward.py after a prior episode's
    cleanup() had silently swallowed exactly this error (ignore_errors=True)
    and left read-only debris behind - the next episode reusing that ID then
    crashed on this line instead of at cleanup time.
    """
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            try:
                os.chmod(os.path.join(root, name), stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(path)


def make_episode_workspace(
    base_dir: Path | None = None,
    episode_id: str | None = None,
    task_id: str = DEFAULT_TASK_ID,
) -> Path:
    """Materialize a fresh, isolated copy of the seeded (buggy) repository
    for the given task. Returns the path to the new workspace. The caller
    owns cleanup.
    """
    spec = get_task(task_id)
    episode_id = episode_id or uuid.uuid4().hex[:12]
    base_dir = base_dir or Path(tempfile.gettempdir()) / "mcp_rl_env_runs"
    workspace = base_dir / episode_id
    if workspace.exists():
        _force_rmtree(workspace)
    workspace.mkdir(parents=True)

    for rel in spec.seed_include:
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

    # Overwrite each fixed source with its buggy seed so there is a real
    # bug for the agent to find and fix.
    for dest_rel, source_rel in spec.buggy_sources:
        buggy = (REPO_ROOT / source_rel).read_text(encoding="utf-8")
        dest = workspace / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(buggy, encoding="utf-8")

    # Pre-task state has no regression test yet - adding one is part of the task.
    regression = workspace / spec.regression_test_path
    if regression.exists():
        regression.unlink()

    # Make the workspace a real git repo so git_diff is meaningful.
    _run(["git", "init", "-q"], cwd=workspace)
    _run(["git", "config", "user.email", "seed@example.invalid"], cwd=workspace)
    _run(["git", "config", "user.name", "seed"], cwd=workspace)
    _run(["git", "add", "-A"], cwd=workspace)
    _run(["git", "commit", "-q", "-m", f"seed: {task_id}"], cwd=workspace)

    return workspace


def cleanup(workspace: Path) -> None:
    """Best-effort delete of an episode workspace.

    Never raises: eval/run_experiment.py calls this in a loop across many
    episodes, and one undeletable workspace must not abort the rest. Tries
    the read-only-safe delete first; only falls back to silently-ignored
    deletion (and a printed warning, so the failure is visible instead of
    invisible debris) if that still fails for some other reason.
    """
    try:
        _force_rmtree(workspace)
    except OSError as exc:
        print(f"warning: could not fully clean up workspace {workspace}: {exc}")
        shutil.rmtree(workspace, ignore_errors=True)
