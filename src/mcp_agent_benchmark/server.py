import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from mcp_agent_benchmark import tools

_env_root = os.environ.get("MCP_AGENT_BENCHMARK_ROOT")
if not _env_root:
    raise RuntimeError(
        "MCP_AGENT_BENCHMARK_ROOT is not set - refusing to serve the real repository. "
        "Set it to the episode workspace this server should operate on."
    )
ROOT = Path(_env_root).resolve()
mcp = FastMCP("software-engineering-environment")


@mcp.tool()
def list_files() -> list[str]:
    return tools.list_files(ROOT)


@mcp.tool()
def read_file(path: str) -> str:
    return tools.read_file(ROOT, path)


@mcp.tool()
def search_code(query: str) -> list[str]:
    return tools.search_code(ROOT, query)


@mcp.tool()
def write_file(path: str, content: str) -> str:
    return tools.write_file(ROOT, path, content)


@mcp.tool()
def run_tests() -> dict:
    return tools.run_tests(ROOT)


@mcp.tool()
def git_diff() -> str:
    return tools.git_diff(ROOT)


if __name__ == "__main__":
    mcp.run()
