from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("apply_golden", REPO_ROOT / "apply_golden.py")
apply_golden = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(apply_golden)


def test_main_never_overwrites_an_existing_regression_test(tmp_path, monkeypatch):
    sentinel = "# sentinel content that must survive\n"
    fake_regression = tmp_path / "test_task_regression.py"
    fake_regression.write_text(sentinel, encoding="utf-8")
    monkeypatch.setattr(apply_golden, "regression_path", fake_regression)

    rc = apply_golden.main()

    assert rc == 0
    assert fake_regression.read_text(encoding="utf-8") == sentinel


def test_main_writes_the_regression_test_when_missing(tmp_path, monkeypatch):
    missing = tmp_path / "test_task_regression.py"
    monkeypatch.setattr(apply_golden, "regression_path", missing)

    rc = apply_golden.main()

    assert rc == 0
    assert missing.exists()
    assert missing.read_text(encoding="utf-8") == apply_golden.golden_test


def test_golden_test_fallback_matches_the_real_committed_file():
    real = (REPO_ROOT / "tests" / "test_task_regression.py").read_text(encoding="utf-8")
    assert apply_golden.golden_test == real
