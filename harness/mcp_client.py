"""Thin async MCP stdio client that drives the real server.py.

This is what the automated agents in agents/ use: it spawns
`python -m mcp_rl_env.server` as a subprocess pointed at one episode's
workspace (via the MCP_RL_ENV_ROOT env var) and exposes an
`await call(tool_name, **kwargs)` coroutine over the real MCP protocol -
the same transport a production MCP-aware coding agent would use, not a
shortcut that calls the tool functions in-process.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from pathlib import Path
import json
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO_ROOT = Path(__file__).resolve().parents[1]


class MCPToolSession:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._stack: AsyncExitStack | None = None
        self.session: ClientSession | None = None

    async def __aenter__(self) -> "MCPToolSession":
        self._stack = AsyncExitStack()
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_rl_env.server"],
            cwd=str(REPO_ROOT),
            env={"MCP_RL_ENV_ROOT": str(self.workspace), "PYTHONPATH": str(REPO_ROOT / "src")},
        )
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc):
        if self._stack:
            await self._stack.aclose()

    async def list_tools(self) -> list[str]:
        assert self.session
        result = await self.session.list_tools()
        return [t.name for t in result.tools]

    async def call(self, tool: str, **kwargs):
        """Call an MCP tool and return a JSON-decodable Python value.

        A tool that returns a Python list (list_files, search_code) comes
        back from FastMCP as one TextContent block per list element, not
        one block holding a JSON array - so every block must be collected,
        not just the first.
        """
        assert self.session
        result = await self.session.call_tool(tool, arguments=kwargs)
        if result.isError:
            text = "\n".join(getattr(c, "text", str(c)) for c in result.content)
            raise RuntimeError(f"tool `{tool}` returned an error: {text}")
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
