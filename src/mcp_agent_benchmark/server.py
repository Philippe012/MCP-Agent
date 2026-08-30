import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from mcp_agent_benchmark import tools

_env_root = os.environ.get("MCP_AGENT_BENCHMARK_ROOT")
if not _env_root:
    # No silent fallback to the real repo root: that repo contains
    # golden/ and verify.py - the answer key. Every real
    # caller (MCPToolSession) sets this explicitly; an unset value means
    # something is misconfigured, not "use the real repo instead."
    raise RuntimeError(
        "MCP_AGENT_BENCHMARK_ROOT is not set - refusing to serve the real repository. "
        "Set it to the episode workspace this server should operate on."
    )
ROOT = Path(_env_root).resolve()
mcp = FastMCP("software-engineering-environment")


@mcp.tool()
def list_files() -> list[str]:
    """List repository files available to the coding agent."""
    return tools.list_files(ROOT)


@mcp.tool()
def read_file(path: str) -> str:
    """Read a text file from the repository."""
    return tools.read_file(ROOT, path)


@mcp.tool()
def search_code(query: str) -> list[str]:
    """Find repository files containing a case-sensitive query."""
    return tools.search_code(ROOT, query)


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write a repository text file."""
    return tools.write_file(ROOT, path, content)


@mcp.tool()
def run_tests() -> dict:
    """Run the deterministic pytest suite."""
    return tools.run_tests(ROOT)


@mcp.tool()
def git_diff() -> str:
    """Return the current git diff."""
    return tools.git_diff(ROOT)


if __name__ == "__main__":
    mcp.run()
