import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from mcp_rl_env import tools

# ROOT defaults to the repository this file lives in (2 parents up from
# src/mcp_rl_env/server.py), matching the original behaviour. Set
# MCP_RL_ENV_ROOT to point an agent session at an isolated episode
# workspace instead - this is how the evaluation harness runs many
# episodes without ever touching the real repository on disk.
ROOT = Path(os.environ.get("MCP_RL_ENV_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()
SRC_ROOT = ROOT
mcp = FastMCP("software-engineering-environment")


@mcp.tool()
def list_files() -> list[str]:
    """List repository files available to the coding agent."""
    return tools.list_files(SRC_ROOT)


@mcp.tool()
def read_file(path: str) -> str:
    """Read a text file from the repository."""
    return tools.read_file(SRC_ROOT, path)


@mcp.tool()
def search_code(query: str) -> list[str]:
    """Find repository files containing a case-sensitive query."""
    return tools.search_code(SRC_ROOT, query)


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write a repository text file."""
    return tools.write_file(SRC_ROOT, path, content)


@mcp.tool()
def run_tests() -> dict:
    """Run the deterministic pytest suite."""
    return tools.run_tests(SRC_ROOT)


@mcp.tool()
def git_diff() -> str:
    """Return the current git diff."""
    return tools.git_diff(SRC_ROOT)


if __name__ == "__main__":
    mcp.run()
