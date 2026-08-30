
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
    assert "src/mcp_rl_env/inventory.py" in names
    assert "src/mcp_rl_env/__init__.py" in names
    assert "src/mcp_rl_env/server.py" not in names
    assert "src/mcp_rl_env/tools.py" not in names
    assert not any(n.startswith("verify.py") for n in names)
    assert not any("golden" in n for n in names)
    assert "tests/test_task_regression.py" not in names


def test_seed_workspace_has_the_real_bug(seeded_workspace):
    text = (seeded_workspace / "src" / "mcp_rl_env" / "inventory.py").read_text(encoding="utf-8")
    assert "for tag in product.tags" in text 


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
    assert fixed  

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
    inventory = seeded_workspace / "src" / "mcp_rl_env" / "inventory.py"
    inventory.write_text(
        (REPO_ROOT / "src" / "mcp_rl_env" / "inventory.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text("def test_multiple_fields():\n    assert True\n", encoding="utf-8")

    report = verify_workspace(seeded_workspace)
    assert report["regression_test_present"] is False
    assert report["reward"] == 0.85


def test_seed_include_never_lists_the_answer_shaped_regression_test():
    # workspace.py already unlinks tests/test_task_regression.py defensively
    # (test_seed_workspace_contains_only_sandboxed_files covers that), but
    # this asserts the stronger invariant directly on _SEED_INCLUDE itself,
    # so a future edit (e.g. "tests/test_inventory.py" -> "tests") can't
    # silently start copying it in the first place.
    from harness.workspace import _SEED_INCLUDE

    assert "tests/test_task_regression.py" not in _SEED_INCLUDE
    assert "tests" not in _SEED_INCLUDE  # a whole-directory include would sweep it in


def test_server_refuses_to_start_without_mcp_rl_env_root():
    import os
    import subprocess

    env = {k: v for k, v in os.environ.items() if k != "MCP_RL_ENV_ROOT"}
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    proc = subprocess.run(
        [sys.executable, "-m", "mcp_rl_env.server"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )
    assert proc.returncode != 0
    assert "MCP_RL_ENV_ROOT" in proc.stderr


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
