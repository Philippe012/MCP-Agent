"""Tests for the evaluation harness itself (workspace seeding, the
verifier, and trajectory recording). None of these need an Anthropic API
key or a network connection - they are what CI runs to prove the
benchmark scaffold is sound even where the live-LLM episodes cannot be.

Run with: pytest tests/test_harness.py -q
(requires the repo root on sys.path; `pytest -q` from the repo root does
this automatically via pyproject.toml's pythonpath, but harness/ itself is
not under src/, so these tests add the repo root explicitly.)
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from harness.workspace import make_episode_workspace, cleanup
from harness.verifier import verify_workspace
from harness.trajectory import Trajectory


@pytest.fixture
def seeded_workspace(tmp_path):
    ws = make_episode_workspace(base_dir=tmp_path, episode_id="test-seed")
    yield ws
    cleanup(ws)


def test_seed_workspace_contains_only_sandboxed_files(seeded_workspace):
    names = {p.relative_to(seeded_workspace).as_posix() for p in seeded_workspace.rglob("*") if p.is_file()}
    # The buggy inventory module and its package must be present...
    assert "src/mcp_rl_env/inventory.py" in names
    assert "src/mcp_rl_env/__init__.py" in names
    # ...but the harness/environment's own implementation must NOT leak in -
    # the agent should never be able to read the MCP server's own source or
    # the private verifier as part of "the repository".
    assert "src/mcp_rl_env/server.py" not in names
    assert "src/mcp_rl_env/tools.py" not in names
    assert not any(n.startswith("verify.py") for n in names)
    assert not any("golden" in n for n in names)
    # The regression test is the agent's job to add - it must not pre-exist.
    assert "tests/test_task_regression.py" not in names


def test_seed_workspace_has_the_real_bug(seeded_workspace):
    text = (seeded_workspace / "src" / "mcp_rl_env" / "inventory.py").read_text(encoding="utf-8")
    assert "for tag in product.tags" in text  # the buggy double-append loop shape


def test_seed_workspace_is_a_git_repo_with_one_commit(seeded_workspace):
    import subprocess

    log = subprocess.run(["git", "log", "--oneline"], cwd=seeded_workspace, text=True, capture_output=True)
    assert log.returncode == 0
    assert len(log.stdout.strip().splitlines()) == 1


def test_verifier_scores_unfixed_seed_below_full_reward(seeded_workspace):
    report = verify_workspace(seeded_workspace)
    assert report["reward"] < 1.0
    assert report["regression_test_present"] is False


def test_verifier_scores_a_correct_fix_plus_regression_test_at_full_reward(seeded_workspace):
    fixed = (REPO_ROOT / "golden" / "solution.patch").exists()
    assert fixed  # sanity: the golden patch this test mirrors actually exists

    inventory = seeded_workspace / "src" / "mcp_rl_env" / "inventory.py"
    inventory.write_text(
        (REPO_ROOT / "src" / "mcp_rl_env" / "inventory.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text(
        "from mcp_rl_env.inventory import InventoryService, Product\n\n\n"
        "def test_multiple_fields_match_returns_product_once():\n"
        "    p = Product('X', 'Red Shoe', ('sport', 'red', 'shoe'), 1)\n"
        "    assert [x.sku for x in InventoryService([p]).search('re')] == ['X']\n",
        encoding="utf-8",
    )
    report = verify_workspace(seeded_workspace)
    assert report["reward"] == 1.0
    assert report["regression_test_present"] is True


def test_verifier_rejects_a_vacuous_regression_test(seeded_workspace):
    """A prior version of the verifier checked the regression test file's
    text for the keywords "multiple_fields" and "assert" instead of what
    the test actually does. That was gameable: `assert True` under a name
    like `test_multiple_fields` matched the keywords while testing nothing.
    Confirmed empirically before this test was written (see CHANGELOG.md);
    this test locks the fix in place so the exploit cannot silently reopen.
    """
    inventory = seeded_workspace / "src" / "mcp_rl_env" / "inventory.py"
    inventory.write_text(
        (REPO_ROOT / "src" / "mcp_rl_env" / "inventory.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text("def test_multiple_fields():\n    assert True\n", encoding="utf-8")

    report = verify_workspace(seeded_workspace)
    assert report["regression_test_present"] is False
    assert report["reward"] == 0.85  # correct fix still credited; the fake test just isn't


def test_trajectory_requires_a_reasoning_note():
    traj = Trajectory(episode_id="t1", agent="baseline", model="test", task="dummy")
    with pytest.raises(ValueError):
        traj.step("list_files", {}, ["a.py"], note="")


def test_trajectory_round_trips_through_save_and_load(tmp_path):
    traj = Trajectory(episode_id="t2", agent="advanced", model="test", task="dummy")
    traj.step("list_files", {}, ["a.py"], note="orient in the repo")
    traj.checkpoint("finalize", "ready to finish", approved=True, auto=True)
    traj.finish({"reward": 1.0})
    json_path, md_path = traj.save(tmp_path)

    reloaded = Trajectory.load(json_path)
    assert reloaded.steps[0]["tool"] == "list_files"
    assert reloaded.checkpoints[0]["approved"] is True
    assert md_path.exists() and "reasoning note" not in md_path.read_text(encoding="utf-8")  # sanity: real content, not a placeholder
    assert "orient in the repo" in md_path.read_text(encoding="utf-8")
