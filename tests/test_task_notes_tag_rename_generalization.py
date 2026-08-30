from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from harness.workspace import make_episode_workspace, cleanup
from harness.verifier import verify_workspace

TASK_ID = "notes_tag_rename_generalization"


@pytest.fixture
def seeded_workspace(tmp_path):
    ws = make_episode_workspace(base_dir=tmp_path, episode_id="test-notes-seed", task_id=TASK_ID)
    yield ws
    cleanup(ws)


def test_seed_workspace_contains_only_sandboxed_files(seeded_workspace):
    names = {p.relative_to(seeded_workspace).as_posix() for p in seeded_workspace.rglob("*") if p.is_file()}
    assert "src/notes/store.py" in names
    assert "src/notes/__init__.py" in names
    assert "tests/test_notes.py" in names
    assert "tasks/notes_tag_rename_generalization/task.md" in names
    assert "tests/test_task_regression.py" not in names
    assert not any("golden" in n for n in names)
    # A genuinely separate domain, not a relabeled inventory/restock task.
    assert not any("mcp_agent_benchmark" in n for n in names)


def test_seed_has_the_substring_matching_bug(seeded_workspace):
    text = (seeded_workspace / "src" / "notes" / "store.py").read_text(encoding="utf-8")
    assert "old in t for t in note.tags" in text


def test_verifier_scores_unfixed_seed_below_full_reward(seeded_workspace):
    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["reward"] < 1.0
    assert report["behavior_passed"] is False  # "workshop" wrongly renamed alongside "work"


def test_verifier_scores_the_real_fix_plus_regression_test_at_full_reward(seeded_workspace):
    fixed = (REPO_ROOT / "src" / "notes" / "store.py").read_text(encoding="utf-8")
    (seeded_workspace / "src" / "notes" / "store.py").write_text(fixed, encoding="utf-8")

    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text(
        (REPO_ROOT / "tests" / "test_task_regression_notes.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["reward"] == 1.0
    assert report["regression_test_present"] is True


def test_verifier_rejects_a_vacuous_regression_test(seeded_workspace):
    fixed = (REPO_ROOT / "src" / "notes" / "store.py").read_text(encoding="utf-8")
    (seeded_workspace / "src" / "notes" / "store.py").write_text(fixed, encoding="utf-8")

    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text("def test_notes():\n    assert True\n", encoding="utf-8")

    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["regression_test_present"] is False
    assert report["reward"] == 0.85


def test_an_overcorrected_exact_only_search_fix_breaks_the_existing_suite(seeded_workspace):
    # The self-correction trap this task transfers from C1 (bugfix_restock_
    # exact_match): an agent that "fixes" rename_tag by making BOTH
    # rename_tag and find_by_tag exact-match only has misread the task -
    # find_by_tag's substring behavior is required to stay unchanged, and
    # the pre-existing test suite (not a new test) must catch this.
    overcorrected = '''from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Note:
    note_id: str
    title: str
    tags: tuple[str, ...]


class NoteStore:
    def __init__(self, notes):
        self.notes = notes

    def find_by_tag(self, query):
        return [n for n in self.notes if query in n.tags]

    def rename_tag(self, old, new):
        changed = 0
        updated = []
        for note in self.notes:
            if old in note.tags:
                new_tags = tuple(new if t == old else t for t in note.tags)
                updated.append(replace(note, tags=new_tags))
                changed += 1
            else:
                updated.append(note)
        self.notes = updated
        return changed
'''
    (seeded_workspace / "src" / "notes" / "store.py").write_text(overcorrected, encoding="utf-8")

    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["tests_passed"] is False  # test_find_by_tag_substring_match regresses
    assert report["reward"] == 0.0
