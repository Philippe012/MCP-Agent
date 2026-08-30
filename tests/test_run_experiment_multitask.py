"""Tests for eval/run_experiment.py's multi-task support.

None of these call the real Anthropic API - agents.baseline_agent.run and
agents.advanced_agent.run are monkeypatched with fake async functions that
record their own calls and return canned reports, the same pattern
tests/test_loop_integration.py already uses for agents/loop.py. Real
harness.workspace.make_episode_workspace / cleanup calls are still
exercised for real (small, isolated, cleaned-up workspaces), so these
tests prove the actual task-selection, pairing, and aggregation logic
against a real registry, not a fully mocked one.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import pytest

from eval import run_experiment
from harness.task_registry import DEFAULT_TASK_ID, all_task_ids


def _args(**overrides) -> argparse.Namespace:
    base = dict(
        n=1,
        model="test-model",
        task_id=DEFAULT_TASK_ID,
        task_ids=None,
        all_tasks=False,
        task_file=None,
        keep_workspaces=False,
        run_id="test-run",
    )
    base.update(overrides)
    return argparse.Namespace(**base)


# --- task selection -----------------------------------------------------


def test_resolve_task_ids_defaults_to_the_single_task_id():
    args = _args(task_id="ledger_transfer_rollback")
    assert run_experiment.resolve_task_ids(args) == ["ledger_transfer_rollback"]


def test_resolve_task_ids_honors_explicit_task_ids():
    args = _args(task_ids=["bugfix_inventory", "calendar_booking_overlap"])
    assert run_experiment.resolve_task_ids(args) == ["bugfix_inventory", "calendar_booking_overlap"]


def test_resolve_task_ids_all_tasks_returns_every_agent_facing_task():
    args = _args(all_tasks=True)
    resolved = run_experiment.resolve_task_ids(args)
    assert set(resolved) == set(all_task_ids()) - {"edge_case_coverage"}
    assert len(resolved) == 14


def test_resolve_task_ids_rejects_unknown_task_id():
    args = _args(task_ids=["not_a_real_task"])
    with pytest.raises(KeyError):
        run_experiment.resolve_task_ids(args)


# --- exclusion of the evaluator-only task -------------------------------


def test_agent_facing_task_ids_excludes_edge_case_coverage():
    assert "edge_case_coverage" not in run_experiment.agent_facing_task_ids()
    assert set(run_experiment.agent_facing_task_ids()) | {"edge_case_coverage"} == set(all_task_ids())


def test_all_tasks_never_includes_the_evaluator_only_fixture():
    args = _args(all_tasks=True)
    assert "edge_case_coverage" not in run_experiment.resolve_task_ids(args)


def test_explicit_task_ids_refuses_the_evaluator_only_fixture():
    args = _args(task_ids=["bugfix_inventory", "edge_case_coverage"])
    with pytest.raises(SystemExit, match="edge_case_coverage"):
        run_experiment.resolve_task_ids(args)


# --- per-task and overall aggregation (pure function, no I/O) ----------


def test_aggregate_multi_task_per_task_summary():
    per_task = {
        "bugfix_inventory": {
            "baseline": [{"reward": 0.85, "behavior_passed": True, "regression_test_present": False}],
            "advanced": [{"reward": 1.0, "behavior_passed": True, "regression_test_present": True}],
        },
        "ledger_transfer_rollback": {
            "baseline": [{"reward": 0.5, "behavior_passed": False, "regression_test_present": False}],
            "advanced": [{"reward": 1.0, "behavior_passed": True, "regression_test_present": True}],
        },
    }
    aggregate = run_experiment._aggregate_multi_task(per_task)

    assert aggregate["per_task"]["bugfix_inventory"]["baseline"]["mean_reward"] == 0.85
    assert aggregate["per_task"]["bugfix_inventory"]["advanced"]["mean_reward"] == 1.0
    assert aggregate["per_task"]["ledger_transfer_rollback"]["baseline"]["mean_reward"] == 0.5
    assert aggregate["per_task"]["ledger_transfer_rollback"]["advanced"]["mean_reward"] == 1.0


def test_aggregate_multi_task_overall_pools_every_task():
    per_task = {
        "bugfix_inventory": {
            "baseline": [{"reward": 0.85, "behavior_passed": True, "regression_test_present": False}],
            "advanced": [{"reward": 1.0, "behavior_passed": True, "regression_test_present": True}],
        },
        "ledger_transfer_rollback": {
            "baseline": [{"reward": 0.5, "behavior_passed": False, "regression_test_present": False}],
            "advanced": [{"reward": 1.0, "behavior_passed": True, "regression_test_present": True}],
        },
    }
    aggregate = run_experiment._aggregate_multi_task(per_task)

    overall_baseline = aggregate["overall"]["baseline"]
    overall_advanced = aggregate["overall"]["advanced"]
    assert overall_baseline["n"] == 2
    assert overall_baseline["mean_reward"] == pytest.approx((0.85 + 0.5) / 2)
    assert overall_advanced["n"] == 2
    assert overall_advanced["mean_reward"] == 1.0


# --- baseline/advanced execution pairing (real workspaces, faked model) -


class _FakeAgentModule:
    """Stands in for agents.baseline_agent / agents.advanced_agent - records
    every call it receives and returns a canned report, with no real model
    call anywhere in the chain."""

    def __init__(self, reward: float):
        self.reward = reward
        self.calls: list[dict] = []

    async def run(self, workspace, episode_id, trajectory_out_dir, task_prompt, model, task_id=DEFAULT_TASK_ID):
        self.calls.append(
            {
                "workspace": workspace,
                "episode_id": episode_id,
                "task_id": task_id,
                "model": model,
            }
        )
        return {"reward": self.reward, "behavior_passed": True, "regression_test_present": True}


def test_run_multi_task_pairs_baseline_and_advanced_per_task(tmp_path, monkeypatch):
    fake_baseline = _FakeAgentModule(reward=0.85)
    fake_advanced = _FakeAgentModule(reward=1.0)
    monkeypatch.setattr(run_experiment, "baseline_agent", fake_baseline)
    monkeypatch.setattr(run_experiment, "advanced_agent", fake_advanced)

    out_dir = tmp_path / "results_out"

    # Redirect only the results/ output location, not REPO_ROOT itself
    # (task.md files must still be read from the real repo).
    def _fake_write(args, task_ids, per_task):
        out_dir.mkdir(exist_ok=True)
        (out_dir / "multitask_results.json").write_text(
            json.dumps(run_experiment._aggregate_multi_task(per_task), indent=2), encoding="utf-8"
        )

    monkeypatch.setattr(run_experiment, "_write_multi_task_results", _fake_write)

    task_ids = ["bugfix_inventory", "calendar_booking_overlap"]
    args = _args(n=1, task_ids=task_ids)

    asyncio.run(run_experiment._run_multi_task(args, task_ids))

    assert len(fake_baseline.calls) == 2
    assert len(fake_advanced.calls) == 2
    assert {c["task_id"] for c in fake_baseline.calls} == set(task_ids)
    assert {c["task_id"] for c in fake_advanced.calls} == set(task_ids)
    for call in fake_baseline.calls:
        assert call["episode_id"] == f"test-run-{call['task_id']}-baseline-01"
    for call in fake_advanced.calls:
        assert call["episode_id"] == f"test-run-{call['task_id']}-advanced-01"

    written = json.loads((out_dir / "multitask_results.json").read_text(encoding="utf-8"))
    assert set(written["per_task"]) == set(task_ids)
    assert written["overall"]["baseline"]["n"] == 2
    assert written["overall"]["advanced"]["n"] == 2


def test_run_multi_task_episode_ids_never_collide_across_tasks(tmp_path, monkeypatch):
    fake_baseline = _FakeAgentModule(reward=0.85)
    fake_advanced = _FakeAgentModule(reward=1.0)
    monkeypatch.setattr(run_experiment, "baseline_agent", fake_baseline)
    monkeypatch.setattr(run_experiment, "advanced_agent", fake_advanced)
    monkeypatch.setattr(run_experiment, "_write_multi_task_results", lambda *a, **kw: None)

    task_ids = ["bugfix_inventory", "calendar_booking_overlap", "dependency_resolver_cycle_detection"]
    args = _args(n=2, task_ids=task_ids)

    asyncio.run(run_experiment._run_multi_task(args, task_ids))

    all_episode_ids = [c["episode_id"] for c in fake_baseline.calls] + [c["episode_id"] for c in fake_advanced.calls]
    assert len(all_episode_ids) == len(set(all_episode_ids)), "episode IDs collided across tasks/episodes"
    assert len(fake_baseline.calls) == len(task_ids) * 2
    assert len(fake_advanced.calls) == len(task_ids) * 2


# --- preservation of existing single-task behavior ----------------------


def test_main_routes_to_the_unchanged_single_task_path_by_default(monkeypatch):
    calls: list[str] = []

    async def fake_main_async(args):
        calls.append("single")

    async def fake_multi_task(args, task_ids):
        calls.append("multi")

    monkeypatch.setattr(run_experiment, "_main_async", fake_main_async)
    monkeypatch.setattr(run_experiment, "_run_multi_task", fake_multi_task)
    monkeypatch.setattr(sys, "argv", ["run_experiment.py", "--n", "1", "--task-id", "bugfix_inventory"])

    assert run_experiment.main() == 0
    assert calls == ["single"]


def test_main_routes_to_multi_task_when_all_tasks_is_passed(monkeypatch):
    calls: list[tuple] = []

    async def fake_main_async(args):
        calls.append(("single",))

    async def fake_multi_task(args, task_ids):
        calls.append(("multi", tuple(task_ids)))

    monkeypatch.setattr(run_experiment, "_main_async", fake_main_async)
    monkeypatch.setattr(run_experiment, "_run_multi_task", fake_multi_task)
    monkeypatch.setattr(sys, "argv", ["run_experiment.py", "--n", "1", "--all-tasks"])

    assert run_experiment.main() == 0
    assert len(calls) == 1
    assert calls[0][0] == "multi"
    assert "edge_case_coverage" not in calls[0][1]
    assert len(calls[0][1]) == 14


def test_main_rejects_all_tasks_and_task_ids_together(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_experiment.py", "--all-tasks", "--task-ids", "bugfix_inventory"])
    with pytest.raises(SystemExit):
        run_experiment.main()
