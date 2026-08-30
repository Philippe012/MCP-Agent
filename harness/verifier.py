from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("mcp_rl_env_verify", REPO_ROOT / "verify.py")
_verify_module = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_verify_module)


def verify_workspace(workspace: Path) -> dict:
    """Run the deterministic verifier against `workspace` and return its report."""
    return _verify_module.verify(workspace)
