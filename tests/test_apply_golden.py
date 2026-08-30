from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# apply_golden.py is a standalone script at the repo root, not a package -
# load it directly rather than adding the root to sys.path and risking a
# name collision with an installed package.
_spec = importlib.util.spec_from_file_location("apply_golden", REPO_ROOT / "apply_golden.py")
apply_golden = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(apply_golden)


def test_main_never_overwrites_an_existing_regression_test(tmp_path, monkeypatch):
    # Regression test for a real bug: apply_golden.py used to write its own
    # hardcoded copy of the golden test over tests/test_task_regression.py
    # on every run, even though the file already existed and was correct.
    # That hardcoded copy had silently drifted from the actual committed
    # test (different function name, different search query) - anyone
    # following REPRODUCE.md's documented `python apply_golden.py` step
    # unknowingly mutated a tracked answer-key file.
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
    # The two copies (this constant, and the real tracked file) must not be
    # allowed to drift again - this is what actually caused the bug above.
    real = (REPO_ROOT / "tests" / "test_task_regression.py").read_text(encoding="utf-8")
    assert apply_golden.golden_test == real
