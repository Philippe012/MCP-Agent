
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
import json
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO_ROOT = Path(__file__).resolve().parents[1]
MCP_CALL_TIMEOUT_S = 30


class MCPToolError(RuntimeError):
    """Real MCP failures should be recorded as environment signals; transport errors and client bugs must propagate and crash loudly.
"""


class MCPToolSession:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._stack: AsyncExitStack | None = None
        self.session: ClientSession | None = None

    async def __aenter__(self) -> "MCPToolSession":
        self._stack = AsyncExitStack()
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_agent_benchmark.server"],
            cwd=str(REPO_ROOT),
            env={"MCP_AGENT_BENCHMARK_ROOT": str(self.workspace), "PYTHONPATH": str(REPO_ROOT / "src")},
        )
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await asyncio.wait_for(self.session.initialize(), timeout=MCP_CALL_TIMEOUT_S)
        return self

    async def __aexit__(self, *exc):
        if self._stack:
            await self._stack.aclose()

    async def list_tools(self) -> list[str]:
        assert self.session
        result = await self.session.list_tools()
        return [t.name for t in result.tools]

    async def call(self, tool: str, **kwargs):
        assert self.session
        result = await asyncio.wait_for(
            self.session.call_tool(tool, arguments=kwargs), timeout=MCP_CALL_TIMEOUT_S
        )
        if result.isError:
            text = "\n".join(getattr(c, "text", str(c)) for c in result.content)
            raise MCPToolError(f"tool `{tool}` returned an error: {text}")
        texts = [getattr(c, "text", None) for c in result.content]
        texts = [t for t in texts if t is not None]
        if not texts:
            return None

        def _decode(raw: str):
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw

        if len(texts) == 1:
            return _decode(texts[0])
        return [_decode(t) for t in texts]
