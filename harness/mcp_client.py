
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
import json
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO_ROOT = Path(__file__).resolve().parents[1]

# The project already hit one real stdio deadlock (CHANGELOG item 3) - a
# hard timeout here means a future hang fails fast instead of blocking the
# harness indefinitely again.
MCP_CALL_TIMEOUT_S = 30


class MCPToolError(RuntimeError):
    """A tool call reached the real MCP server and the server reported a
    genuine failure (result.isError) - e.g. a path escaping the sandbox, a
    file that doesn't exist. Callers that want to treat "the environment
    failed" as meaningful signal (recovery-rate metrics, retry logic)
    should catch this specifically, not a bare Exception - anything else
    (a transport error, a bug in this client) is a harness problem and
    should propagate and crash loudly instead of being recorded as if the
    agent had encountered a normal tool failure."""


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
        """Call an MCP tool and return a JSON-decodable Python value.
        """
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
