from pathlib import Path
import subprocess
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT
mcp = FastMCP("software-engineering-environment")


def _safe_path(relative: str) -> Path:
    path = (SRC_ROOT / relative).resolve()
    if SRC_ROOT not in path.parents and path != SRC_ROOT:
        raise ValueError("Path escapes repository")
    return path


@mcp.tool()
def list_files() -> list[str]:
    """List repository files available to the coding agent."""
    ignored = {".git", ".venv", "__pycache__"}
    return sorted(
        str(p.relative_to(SRC_ROOT))
        for p in SRC_ROOT.rglob("*")
        if p.is_file() and not any(part in ignored for part in p.parts)
    )


@mcp.tool()
def read_file(path: str) -> str:
    """Read a text file from the repository."""
    return _safe_path(path).read_text(encoding="utf-8")


@mcp.tool()
def search_code(query: str) -> list[str]:
    """Find repository files containing a case-sensitive query."""
    matches = []
    for path in SRC_ROOT.rglob("*.py"):
        if any(part in {".venv", "__pycache__"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        if query in text:
            matches.append(str(path.relative_to(SRC_ROOT)))
    return sorted(matches)


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write a repository text file."""
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"wrote {path}"


@mcp.tool()
def run_tests() -> dict:
    """Run the deterministic pytest suite."""
    proc = subprocess.run(
        ["python", "-m", "pytest", "-q"],
        cwd=SRC_ROOT,
        text=True,
        capture_output=True,
    )
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


@mcp.tool()
def git_diff() -> str:
    """Return the current git diff."""
    proc = subprocess.run(["git", "diff", "--"], cwd=SRC_ROOT, text=True, capture_output=True)
    return proc.stdout


if __name__ == "__main__":
    mcp.run()
