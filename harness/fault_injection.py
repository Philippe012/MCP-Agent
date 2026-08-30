"""Deterministic, seeded tool-failure injection for robustness experiments
(TASK_SUITE_DESIGN.md Section 7).

Wraps a real MCPToolSession so any existing task can be run under a
NORMAL or TOOL_FAILURE condition without touching the task itself - the
one genuine recovered failure this project has on record
(trajectories/advanced/manual-recovery-01.md) happened while solving
bugfix_inventory, not a task built around failing, and this wrapper
studies the same phenomenon (does the agent's next action reference an
observed failure) on demand instead of waiting for one to happen by
accident.

Deliberately deterministic, not random: a condition names an exact tool
and an exact 1-indexed call number to fail, so a given (tool, n) pair
always fails the same way on every run - repeatable evidence, not chaos
that would make a "recovery happened" claim irreproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness.mcp_client import MCPToolError, MCPToolSession


@dataclass(frozen=True)
class FaultCondition:
    """Fail the `occurrence`-th call to `tool` with `message`. `occurrence`
    is 1-indexed per tool name (the first call to that tool is occurrence
    1), matching how a human would describe the condition ("fail the
    first read_file call")."""

    tool: str
    occurrence: int
    message: str = "simulated tool failure (fault_injection condition)"


NORMAL: tuple[FaultCondition, ...] = ()


class FaultInjectingMCPToolSession:
    """Drop-in replacement for MCPToolSession that deterministically raises
    MCPToolError on specific, pre-declared calls and otherwise delegates
    to a real session - every non-faulted call still reaches the real MCP
    server, so this measures recovery from a genuine environment contract
    (MCPToolError), not a mocked one.
    """

    def __init__(self, workspace: Path, conditions: tuple[FaultCondition, ...] = NORMAL):
        self._real = MCPToolSession(workspace)
        self._conditions = conditions
        self._call_counts: dict[str, int] = {}
        self.injected_failures: list[dict] = []

    async def __aenter__(self) -> "FaultInjectingMCPToolSession":
        await self._real.__aenter__()
        return self

    async def __aexit__(self, *exc):
        await self._real.__aexit__(*exc)

    async def list_tools(self) -> list[str]:
        return await self._real.list_tools()

    async def call(self, tool: str, **kwargs):
        self._call_counts[tool] = self._call_counts.get(tool, 0) + 1
        occurrence = self._call_counts[tool]
        for condition in self._conditions:
            if condition.tool == tool and condition.occurrence == occurrence:
                self.injected_failures.append({"tool": tool, "occurrence": occurrence})
                raise MCPToolError(condition.message)
        return await self._real.call(tool, **kwargs)
