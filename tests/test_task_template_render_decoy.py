from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from harness.workspace import make_episode_workspace, cleanup
from harness.verifier import verify_workspace

TASK_ID = "template_render_decoy"


@pytest.fixture
def seeded_workspace(tmp_path):
    ws = make_episode_workspace(base_dir=tmp_path, episode_id="test-template-seed", task_id=TASK_ID)
    yield ws
    cleanup(ws)


def test_seed_workspace_contains_the_decoy_alongside_the_real_bug(seeded_workspace):
    names = {p.relative_to(seeded_workspace).as_posix() for p in seeded_workspace.rglob("*") if p.is_file()}
    assert "src/templating/render.py" in names
    assert "src/templating/legacy_render.py" in names
    assert "tasks/template_render_decoy/task.md" in names
    assert not any("golden" in n for n in names)
    assert "tests/test_task_regression.py" not in names


def test_editing_only_the_decoy_never_fixes_anything(seeded_workspace):
    decoy = seeded_workspace / "src" / "templating" / "legacy_render.py"
    decoy.write_text("def render_legacy(t, c):\n    return t\n", encoding="utf-8")

    unfixed_report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert unfixed_report["behavior_passed"] is False


def test_verifier_scores_the_real_fix_plus_regression_test_at_full_reward(seeded_workspace):
    fixed = (REPO_ROOT / "src" / "templating" / "render.py").read_text(encoding="utf-8")
    (seeded_workspace / "src" / "templating" / "render.py").write_text(fixed, encoding="utf-8")

    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text(
        (REPO_ROOT / "tests" / "test_task_regression_templating.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["reward"] == 1.0
    assert report["regression_test_present"] is True


def test_verifier_rejects_a_vacuous_regression_test(seeded_workspace):
    fixed = (REPO_ROOT / "src" / "templating" / "render.py").read_text(encoding="utf-8")
    (seeded_workspace / "src" / "templating" / "render.py").write_text(fixed, encoding="utf-8")

    regression = seeded_workspace / "tests" / "test_task_regression.py"
    regression.write_text("def test_render():\n    assert True\n", encoding="utf-8")

    report = verify_workspace(seeded_workspace, task_id=TASK_ID)
    assert report["regression_test_present"] is False
    assert report["reward"] == 0.85
