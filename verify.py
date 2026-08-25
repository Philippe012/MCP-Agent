from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, env=ENV)


def main() -> int:
    proc = run([sys.executable, "-m", "pytest", "-q"])
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr)
        print("REWARD=0.0")
        return 1

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
    proc = run([sys.executable, "-c", check])
    if proc.returncode != 0:
        print(proc.stderr)
        print("REWARD=0.5")
        return 1

    regression = ROOT / "tests" / "test_task_regression.py"
    text = regression.read_text(encoding="utf-8") if regression.exists() else ""
    has_regression = "multiple_fields" in text and "assert" in text
    reward = 1.0 if has_regression else 0.85
    print("DETERMINISTIC_BEHAVIOR=PASS")
    print(f"REGRESSION_TEST={'PASS' if has_regression else 'MISSING'}")
    print(f"REWARD={reward:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
