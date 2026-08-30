from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from mcp_agent_benchmark import tools


@pytest.fixture
def root(tmp_path):
    (tmp_path / "inside.txt").write_text("safe", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    "escaping_path",
    [
        "../outside.txt",
        "../../outside.txt",
        "C:/Windows/win.ini",
        "/etc/passwd",
    ],
)
def test_read_file_rejects_escaping_paths(root, escaping_path):
    with pytest.raises(ValueError):
        tools.read_file(root, escaping_path)


@pytest.mark.parametrize(
    "escaping_path",
    ["../outside.txt", "../../outside.txt", "C:/Windows/win.ini", "/etc/passwd"],
)
def test_write_file_rejects_escaping_paths(root, escaping_path):
    with pytest.raises(ValueError):
        tools.write_file(root, escaping_path, "pwned")
    assert not (root.parent / "outside.txt").exists()


def test_read_file_allows_a_path_inside_the_root(root):
    assert tools.read_file(root, "inside.txt") == "safe"


def test_write_file_allows_a_path_inside_the_root(root):
    tools.write_file(root, "new.txt", "content")
    assert (root / "new.txt").read_text(encoding="utf-8") == "content"
