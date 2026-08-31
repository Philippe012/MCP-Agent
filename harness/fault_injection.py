from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness.mcp_client import MCPToolError, MCPToolSession


@dataclass(frozen=True)
class FaultCondition:

    tool: str
    occurrence: int
    message: str = "simulated tool failure (fault_injection condition)"


NORMAL: tuple[FaultCondition, ...] = ()


class FaultInjectingMCPToolSession:

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
