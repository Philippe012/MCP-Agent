from __future__ import annotations

import importlib.util
from pathlib import Path

from harness.task_registry import DEFAULT_TASK_ID

REPO_ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("mcp_agent_benchmark_verify", REPO_ROOT / "verify.py")
_verify_module = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_verify_module)


def verify_workspace(workspace: Path, task_id: str = DEFAULT_TASK_ID) -> dict:
    return _verify_module.verify(workspace, task_id)
