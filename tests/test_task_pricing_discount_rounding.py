from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from harness.workspace import make_episode_workspace, cleanup
from harness.verifier import verify_workspace

TASK_ID = "pricing_discount_rounding"


@pytest.fixture
def seeded_workspace(tmp_path):
    ws = make_episode_workspace(base_dir=tmp_path, episode_id="test-pricing-seed", task_id=TASK_ID)
    yield ws
    cleanup(ws)


def test_seed_has_the_per_line_rounding_bug(seeded_workspace):
    text = (seeded_workspace / "src" / "pricing" / "cart.py").read_text(encoding="utf-8")
    assert "for item in self.items" in text  # per-line loop, not a single subtotal computation


def test_seed_workspace_contains_only_sandboxed_files(seeded_workspace):
    names = {p.relative_to(seeded_workspace).as_posix() for p in seeded_workspace.rglob("*") if p.is_file()}
    assert "src/pricing/cart.py" in names
    assert "tasks/pricing_discount_rounding/task.md" in names
    assert not any(n.startswith("tasks/") and n != "tasks/pricing_discount_rounding/task.md" for n in names)
    assert "tests/test_task_regression.py" not in names
    assert not any("golden" in n for n in names)


def test_the_pre_existing_visible_suite_already_fails_on_the_unfixed_seed(seeded_workspace):
    # This is the task's whole point: unlike every other task in this
    # suite, the agent doesn't have to discover a hidden bug from scratch -
    # tests/test_pricing.py (copied in verbatim below via seed_include)
    # already fails on the seeded buggy code, forcing a real diagnosis of
    # *why*, not just a hidden-oracle discovery.
    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["reward"] == 0.0
    assert report["tests_passed"] is False


def test_verifier_scores_the_real_fix_plus_regression_test_at_full_reward(seeded_workspace):
    fixed = (REPO_ROOT / "src" / "pricing" / "cart.py").read_text(encoding="utf-8")
    (seeded_workspace / "src" / "pricing" / "cart.py").write_text(fixed, encoding="utf-8")

    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text(
        (REPO_ROOT / "tests" / "test_task_regression_pricing.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["reward"] == 1.0
    assert report["regression_test_present"] is True


def test_verifier_rejects_a_vacuous_regression_test(seeded_workspace):
    fixed = (REPO_ROOT / "src" / "pricing" / "cart.py").read_text(encoding="utf-8")
    (seeded_workspace / "src" / "pricing" / "cart.py").write_text(fixed, encoding="utf-8")

    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text("def test_cart():\n    assert True\n", encoding="utf-8")

    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["regression_test_present"] is False
    assert report["reward"] == 0.85
