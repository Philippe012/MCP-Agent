from __future__ import annotations

import asyncio
import functools
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import anthropic

from agents.loop import run_agent_episode
from harness.fault_injection import FaultCondition, FaultInjectingMCPToolSession
from harness.workspace import make_episode_workspace, cleanup


class _Block:
    def __init__(self, type_, **kw):
        self.type = type_
        for k, v in kw.items():
            setattr(self, k, v)


class _Response:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


class _FakeMessages:
    def __init__(self):
        self._responses = [
            _Response(
                "tool_use",
                [_Block("text", text="orienting"), _Block("tool_use", name="list_files", input={}, id="t1")],
            ),
            _Response("end_turn", [_Block("text", text="done")]),
        ]

    async def create(self, **kwargs):
        return self._responses.pop(0)


class _FakeAsyncAnthropic:
    def __init__(self, *args, **kwargs):
        self.messages = _FakeMessages()


def test_task_id_and_session_factory_propagate_through_the_full_loop(tmp_path, monkeypatch):
    monkeypatch.setattr(anthropic, "AsyncAnthropic", _FakeAsyncAnthropic)

    task_id = "bugfix_restock_exact_match"
    ws = make_episode_workspace(base_dir=tmp_path, episode_id="loop-integration", task_id=task_id)
    faulted_session = functools.partial(
        FaultInjectingMCPToolSession,
        conditions=(FaultCondition(tool="list_files", occurrence=1),),
    )
    try:
        report = asyncio.run(
            run_agent_episode(
                workspace=ws,
                episode_id="loop-integration",
                agent_name="baseline",
                system_prompt="test",
                task_prompt="test",
                trajectory_out_dir=tmp_path / "trajectories",
                task_id=task_id,
                session_factory=faulted_session,
            )
        )
    finally:
        cleanup(ws)

    assert report["behavior_passed"] is False
    assert report["reward"] == 0.5

    trajectory_path = tmp_path / "trajectories" / "loop-integration.json"
    import json

    steps = json.loads(trajectory_path.read_text(encoding="utf-8"))["steps"]
    assert len(steps) == 1
    assert steps[0]["tool"] == "list_files"
    assert steps[0]["success"] is False
