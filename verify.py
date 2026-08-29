"""Deterministic verifier for the bugfix_inventory task.

Computes a reward in [0, 1] for a workspace (the real repo by default, or
any episode workspace via VERIFY_ROOT / verify(root=...)). The model never
grades itself: this script is the only source of truth for reward, and the
evaluation harness (harness/verifier.py) imports `verify()` directly so
batch runs and this CLI always agree.
"""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

HARNESS_ROOT = Path(__file__).resolve().parent


def _run(root: Path, cmd: list[str]) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    return subprocess.run(
        cmd, cwd=root, text=True, capture_output=True, env=env, stdin=subprocess.DEVNULL
    )


def _regression_test_proves_the_fix(root: Path) -> bool:
    """Check that the regression test actually exercises the bug, not just
    that a file with the right keywords in it exists.

    An earlier version of this check was `"multiple_fields" in text and
    "assert" in text` - a keyword match on the test *file*, not a check of
    what the test actually does. That is gameable: a test containing only
    `assert True` under a name like `test_multiple_fields` satisfies it
    while proving nothing. Confirmed empirically (see CHANGELOG.md) before
    this was written.

    The fix: run the candidate regression test file against the known-buggy
    inventory.py (this benchmark's own seed, never exposed to the agent's
    workspace - see harness/workspace.py) in a scratch copy, and require it
    to fail there. A test that cannot tell the buggy implementation from
    the fixed one is not "a regression test that proves" anything, whatever
    it's named. Combined with the full suite already passing against the
    agent's actual (fixed) code, this proves the test is genuinely sensitive
    to the bug rather than vacuous.
    """
    regression = root / "tests" / "test_task_regression.py"
    if not regression.exists():
        return False
    if "assert" not in regression.read_text(encoding="utf-8"):
        return False

    buggy_source = (HARNESS_ROOT / "seed" / "inventory_buggy.py").read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        mutated_root = Path(tmp)
        shutil.copytree(root, mutated_root, dirs_exist_ok=True)
        (mutated_root / "src" / "mcp_rl_env" / "inventory.py").write_text(buggy_source, encoding="utf-8")
        proc = _run(mutated_root, [sys.executable, "-m", "pytest", "-q", "tests/test_task_regression.py"])
        # It must fail against the buggy implementation - a test that
        # passes either way isn't testing the bug at all.
        return proc.returncode != 0


def verify(root: Path) -> dict:
    """Run the full verification pipeline against `root` and return a report.

    Report shape:
      {
        "tests_passed": bool,
        "behavior_passed": bool,
        "regression_test_present": bool,
        "reward": float,
        "stdout": str,        # combined human-readable log
      }
    """
    log: list[str] = []
    root = root.resolve()

    proc = _run(root, [sys.executable, "-m", "pytest", "-q"])
    log.append(proc.stdout)
    if proc.returncode != 0:
        log.append(proc.stderr)
        log.append("REWARD=0.0")
        return {
            "tests_passed": False,
            "behavior_passed": False,
            "regression_test_present": False,
            "reward": 0.0,
            "stdout": "\n".join(log),
        }

    check = """
from mcp_rl_env.inventory import InventoryService, Product
p = Product('X', 'Red Shoe', ('sport', 'red', 'shoe'), 1)
q = Product('Y', 'Blue Bag', ('travel', 'blue'), 2)
s = InventoryService([p, q])
assert [x.sku for x in s.search('red')] == ['X']
assert [x.sku for x in s.search('shoe')] == ['X']
assert [x.sku for x in s.search('re')] == ['X']
assert [x.sku for x in s.search('sport')] == ['X']
assert [x.sku for x in s.search('')] == ['X', 'Y']
"""
    proc = _run(root, [sys.executable, "-c", check])
    if proc.returncode != 0:
        log.append(proc.stderr)
        log.append("REWARD=0.5")
        return {
            "tests_passed": True,
            "behavior_passed": False,
            "regression_test_present": False,
            "reward": 0.5,
            "stdout": "\n".join(log),
        }

    has_regression = _regression_test_proves_the_fix(root)
    reward = 1.0 if has_regression else 0.85
    log.append("DETERMINISTIC_BEHAVIOR=PASS")
    log.append(f"REGRESSION_TEST={'PASS' if has_regression else 'MISSING_OR_VACUOUS'}")
    log.append(f"REWARD={reward:.2f}")
    return {
        "tests_passed": True,
        "behavior_passed": True,
        "regression_test_present": has_regression,
        "reward": reward,
        "stdout": "\n".join(log),
    }


def main() -> int:
    root = Path(os.environ.get("VERIFY_ROOT", str(HARNESS_ROOT)))
    report = verify(root)
    print(report["stdout"])
    return 0 if report["reward"] >= 0.85 else 1


if __name__ == "__main__":
    raise SystemExit(main())
