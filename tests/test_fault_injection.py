"""FaultInjectingMCPToolSession must be deterministic (same condition ->
same failure point, every run) and must leave every non-faulted call
reaching the real MCP server unmodified - otherwise a "recovery" measured
against it would be recovery from a mock, not from the real environment
contract (MCPToolError) agents actually see.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from harness.fault_injection import NORMAL, FaultCondition, FaultInjectingMCPToolSession
from harness.mcp_client import MCPToolError
from harness.workspace import make_episode_workspace, cleanup


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def seeded_workspace(tmp_path):
    ws = make_episode_workspace(base_dir=tmp_path, episode_id="fault-injection-test")
    yield ws
    cleanup(ws)


def test_normal_condition_never_injects_a_failure(seeded_workspace):
    async def _go():
        async with FaultInjectingMCPToolSession(seeded_workspace, NORMAL) as session:
            for _ in range(3):
                await session.call("list_files")
            return session.injected_failures

    assert _run(_go()) == []


def test_fails_the_declared_occurrence_deterministically(seeded_workspace):
    conditions = (FaultCondition(tool="list_files", occurrence=2),)

    async def _go():
        outcomes = []
        async with FaultInjectingMCPToolSession(seeded_workspace, conditions) as session:
            for _ in range(3):
                try:
                    await session.call("list_files")
                    outcomes.append("ok")
                except MCPToolError:
                    outcomes.append("failed")
            return outcomes, session.injected_failures

    outcomes, injected = _run(_go())
    assert outcomes == ["ok", "failed", "ok"]
    assert injected == [{"tool": "list_files", "occurrence": 2}]


def test_same_condition_produces_the_same_failure_point_on_a_second_run(seeded_workspace):
    conditions = (FaultCondition(tool="list_files", occurrence=2),)

    async def _go():
        async with FaultInjectingMCPToolSession(seeded_workspace, conditions) as session:
            outcomes = []
            for _ in range(3):
                try:
                    await session.call("list_files")
                    outcomes.append("ok")
                except MCPToolError:
                    outcomes.append("failed")
            return outcomes

    first_run = _run(_go())
    second_run = _run(_go())
    assert first_run == second_run == ["ok", "failed", "ok"]


def test_non_faulted_calls_still_reach_the_real_server(seeded_workspace):
    # Fault only read_file; list_files must still return the real,
    # unmodified file listing from the real server.
    conditions = (FaultCondition(tool="read_file", occurrence=1),)

    async def _go():
        async with FaultInjectingMCPToolSession(seeded_workspace, conditions) as session:
            files = await session.call("list_files")
            try:
                await session.call("read_file", path="src/mcp_rl_env/inventory.py")
                read_failed = False
            except MCPToolError:
                read_failed = True
            return files, read_failed

    files, read_failed = _run(_go())
    assert any("inventory.py" in f for f in files)  # list_files uses native path separators on Windows
    assert read_failed is True
