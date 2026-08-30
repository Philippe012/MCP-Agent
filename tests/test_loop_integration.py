"""Proves task_id and session_factory actually propagate through the full
run_agent_episode loop, not just through the individual components in
isolation - the previous Phase 1 hardening pass caught a real bug this
same way (a hardcoded retry_of=None that individual-component tests never
exercised). No live model: anthropic.AsyncAnthropic is replaced with a
scripted stand-in that returns one tool call then finishes, matching the
verification style CHANGELOG's Phase 1 entry already established.
"""

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

    # If task_id had silently defaulted to bugfix_inventory instead of
    # actually being threaded through to verify_workspace, this seeded-but-
    # untouched restock bug would score 0.85 (bugfix_inventory's behavior
    # check only exercises search(), which this seed's search() already
    # passes) instead of the correct 0.5 (restock's own behavior check
    # catches the seeded bug).
    assert report["behavior_passed"] is False
    assert report["reward"] == 0.5

    trajectory_path = tmp_path / "trajectories" / "loop-integration.json"
    import json

    steps = json.loads(trajectory_path.read_text(encoding="utf-8"))["steps"]
    assert len(steps) == 1
    # If session_factory had silently fallen back to a real MCPToolSession,
    # this call would have succeeded instead of hitting the injected fault.
    assert steps[0]["tool"] == "list_files"
    assert steps[0]["success"] is False
