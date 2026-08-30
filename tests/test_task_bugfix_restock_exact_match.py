from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from harness.workspace import make_episode_workspace, cleanup
from harness.verifier import verify_workspace

TASK_ID = "bugfix_restock_exact_match"


@pytest.fixture
def seeded_workspace(tmp_path):
    ws = make_episode_workspace(base_dir=tmp_path, episode_id="test-restock-seed", task_id=TASK_ID)
    yield ws
    cleanup(ws)


def test_seed_has_the_substring_matching_bug(seeded_workspace):
    text = (seeded_workspace / "src" / "mcp_rl_env" / "inventory.py").read_text(encoding="utf-8")
    assert "sku in p.sku" in text  # the buggy comparison, not the fixed `p.sku == sku`


def test_seed_workspace_contains_only_sandboxed_files(seeded_workspace):
    names = {p.relative_to(seeded_workspace).as_posix() for p in seeded_workspace.rglob("*") if p.is_file()}
    assert "src/mcp_rl_env/inventory.py" in names
    assert "tasks/bugfix_restock_exact_match/task.md" in names
    assert not any(n.startswith("tasks/") and n != "tasks/bugfix_restock_exact_match/task.md" for n in names)
    assert "tests/test_task_regression.py" not in names
    assert not any("golden" in n for n in names)


def test_verifier_scores_unfixed_seed_below_full_reward(seeded_workspace):
    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["reward"] < 1.0
    assert report["behavior_passed"] is False  # A1 restock leaks into A10


def test_verifier_scores_the_real_fix_plus_regression_test_at_full_reward(seeded_workspace):
    fixed = (REPO_ROOT / "src" / "mcp_rl_env" / "inventory.py").read_text(encoding="utf-8")
    (seeded_workspace / "src" / "mcp_rl_env" / "inventory.py").write_text(fixed, encoding="utf-8")

    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text(
        (REPO_ROOT / "tests" / "test_task_regression_restock.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["reward"] == 1.0
    assert report["regression_test_present"] is True


def test_verifier_rejects_a_vacuous_regression_test(seeded_workspace):
    fixed = (REPO_ROOT / "src" / "mcp_rl_env" / "inventory.py").read_text(encoding="utf-8")
    (seeded_workspace / "src" / "mcp_rl_env" / "inventory.py").write_text(fixed, encoding="utf-8")

    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text("def test_restock():\n    assert True\n", encoding="utf-8")

    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["regression_test_present"] is False
    assert report["reward"] == 0.85


def test_an_over_generalized_fix_that_breaks_search_scores_zero(seeded_workspace):
    # The realistic self-correction trap this task is designed to surface
    # (TASK_SUITE_DESIGN.md C1): an agent "fixing" restock's matching style
    # could over-generalize and make search() exact-match too, which is
    # wrong and must be caught by the *existing* test suite, not a new one.
    over_generalized = """from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    tags: tuple[str, ...]
    stock: int


class InventoryService:
    def __init__(self, products):
        self.products = products

    def restock(self, sku, qty):
        self.products = [
            replace(p, stock=p.stock + qty) if p.sku == sku else p
            for p in self.products
        ]

    def search(self, query):
        query = query.strip().lower()
        if not query:
            return list(self.products)
        return [p for p in self.products if query == p.name.lower()]
"""
    (seeded_workspace / "src" / "mcp_rl_env" / "inventory.py").write_text(over_generalized, encoding="utf-8")

    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["tests_passed"] is False  # tests/test_inventory.py::test_search_by_name regresses
    assert report["reward"] == 0.0
