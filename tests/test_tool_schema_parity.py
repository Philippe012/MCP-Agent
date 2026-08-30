"""agents/tool_schemas.py's TOOLS and the real MCP server's tool
definitions are two independently maintained lists with nothing enforcing
they match - server.py could gain a new tool, or a required parameter
could get renamed, and TOOLS would silently drift out of sync, meaning an
agent would be given a tool schema that doesn't match what the server
actually accepts. This connects to the real server and checks parity
directly, rather than trusting that both were edited together.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.mcp_client import MCPToolSession
from harness.workspace import make_episode_workspace, cleanup
from agents.tool_schemas import TOOLS


def _live_server_tools(workspace: Path) -> dict:
    async def _fetch():
        async with MCPToolSession(workspace) as session:
            assert session.session
            result = await session.session.list_tools()
            return {
                t.name: {
                    "required": set(t.inputSchema.get("required", [])),
                    "properties": set(t.inputSchema.get("properties", {}).keys()),
                }
                for t in result.tools
            }

    return asyncio.run(_fetch())


def test_tool_schemas_match_the_real_mcp_server(tmp_path):
    workspace = make_episode_workspace(base_dir=tmp_path, episode_id="schema-parity")
    try:
        live = _live_server_tools(workspace)
    finally:
        cleanup(workspace)

    declared = {t["name"]: t for t in TOOLS}

    assert set(live) == set(declared), (
        f"agents/tool_schemas.py and the real server disagree on which tools "
        f"exist: server-only={set(live) - set(declared)}, "
        f"schema-only={set(declared) - set(live)}"
    )

    for name, live_schema in live.items():
        declared_schema = declared[name]["input_schema"]
        declared_required = set(declared_schema.get("required", []))
        declared_properties = set(declared_schema.get("properties", {}).keys())

        assert declared_required == live_schema["required"], (
            f"{name}: declared required params {declared_required} != "
            f"server's actual required params {live_schema['required']}"
        )
        assert declared_properties == live_schema["properties"], (
            f"{name}: declared properties {declared_properties} != "
            f"server's actual properties {live_schema['properties']}"
        )
