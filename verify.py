"""Deterministic verifier for the bugfix_inventory task.

Computes a reward in [0, 1] for a workspace (the real repo by default, or
any episode workspace via VERIFY_ROOT / verify(root=...)). The model never
grades itself: this script is the only source of truth for reward, and the
evaluation harness (harness/verifier.py) imports `verify()` directly so
batch runs and this CLI always agree.

verify(root) always returns a dict with exactly these keys:
  tests_passed: bool, behavior_passed: bool, regression_test_present: bool,
  reward: float in {0.0, 0.5, 0.85, 1.0}, stdout: str
"""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

HARNESS_ROOT = Path(__file__).resolve().parent
PASSING_REWARD_THRESHOLD = 0.85


def _run(root: Path, cmd: list[str]) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    return subprocess.run(
        cmd, cwd=root, text=True, capture_output=True, env=env, stdin=subprocess.DEVNULL
    )


def _regression_test_proves_the_fix(root: Path) -> bool:
    """Run the candidate regression test against the benchmark's own
    known-buggy inventory.py in a scratch copy, and require it to fail
    there - a test that can't tell the buggy implementation from the fixed
    one doesn't prove anything, whatever it's named.

    pytest's exit code 1 means "tests ran and at least one failed" -
    checked instead of a generic `!= 0`, because a regression file with no
    test function at all exits 5 ("no tests collected"), which is also
    non-zero and would otherwise be misread as a genuine failure. Confirmed
    empirically (see CHANGELOG) before relying on this distinction.
    """
    regression = root / "tests" / "test_task_regression.py"
    if not regression.exists():
        return False

    buggy_source = (HARNESS_ROOT / "seed" / "inventory_buggy.py").read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        mutated_root = Path(tmp)
        shutil.copytree(
            root, mutated_root, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
        (mutated_root / "src" / "mcp_rl_env" / "inventory.py").write_text(buggy_source, encoding="utf-8")
        proc = _run(mutated_root, [sys.executable, "-m", "pytest", "-q", "tests/test_task_regression.py"])
        return proc.returncode == 1


def verify(root: Path) -> dict:
    """Run the full verification pipeline against `root` and return a report."""
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
    # 0.0 broken code, 0.5 code works but the fix is unverified/wrong,
    # 0.85 correct fix without a regression test, 1.0 correct fix +
    # regression test - each threshold is a distinct, separately-checked
    # failure mode, not an arbitrary scale.
    reward = 1.0 if has_regression else PASSING_REWARD_THRESHOLD
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
    return 0 if report["reward"] >= PASSING_REWARD_THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(main())
