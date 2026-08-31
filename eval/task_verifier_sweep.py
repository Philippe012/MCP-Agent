from __future__ import annotations

import json
import tempfile
from pathlib import Path

from harness.task_registry import all_task_ids, get_task
from harness.verifier import verify_workspace
from harness.workspace import make_episode_workspace, cleanup

REPO_ROOT = Path(__file__).resolve().parents[1]

TASK_FIXTURES: dict[str, tuple[list[tuple[str, str]], str | None]] = {
    "bugfix_inventory": (
        [("src/mcp_agent_benchmark/inventory.py", "src/mcp_agent_benchmark/inventory.py")],
        "tests/test_task_regression.py",
    ),
    "bugfix_restock_exact_match": (
        [("src/mcp_agent_benchmark/inventory.py", "src/mcp_agent_benchmark/inventory.py")],
        "tests/test_task_regression_restock.py",
    ),
    "decoy_context_efficiency": (
        [("src/mcp_agent_benchmark/inventory.py", "src/mcp_agent_benchmark/inventory.py")],
        "tests/test_task_regression.py",
    ),
    "edge_case_coverage": (
        [("src/mcp_agent_benchmark/inventory.py", "src/mcp_agent_benchmark/inventory.py")],
        None,  
    ),
    "generalization_contact_index": (
        [("src/contact_index/directory.py", "src/contact_index/directory.py")],
        "tests/test_task_regression_contact_index.py",
    ),
    "ledger_transfer_rollback": (
        [("src/ledger/account.py", "src/ledger/account.py")],
        "tests/test_task_regression_ledger.py",
    ),
    "calendar_booking_overlap": (
        [("src/scheduler/calendar.py", "src/scheduler/calendar.py")],
        "tests/test_task_regression_calendar.py",
    ),
    "config_loader_backward_compat": (
        [("src/configloader/loader.py", "src/configloader/loader.py")],
        "tests/test_task_regression_configloader.py",
    ),
    "batch_partial_failure_recovery": (
        [("src/batch/processor.py", "src/batch/processor.py")],
        "tests/test_task_regression_batch.py",
    ),
    "lru_cache_eviction_invariant": (
        [("src/cache/lru.py", "src/cache/lru.py")],
        "tests/test_task_regression_lru.py",
    ),
    "template_render_decoy": (
        [("src/templating/render.py", "src/templating/render.py")],
        "tests/test_task_regression_templating.py",
    ),
    "pricing_discount_rounding": (
        [("src/pricing/cart.py", "src/pricing/cart.py")],
        "tests/test_task_regression_pricing.py",
    ),
    "notes_tag_rename_generalization": (
        [("src/notes/store.py", "src/notes/store.py")],
        "tests/test_task_regression_notes.py",
    ),
    "shipping_quote_root_cause": (
        [("src/shipping/rates.py", "src/shipping/rates.py")],
        "tests/test_task_regression_shipping.py",
    ),
    "dependency_resolver_cycle_detection": (
        [("src/deps/resolver.py", "src/deps/resolver.py")],
        "tests/test_task_regression_deps.py",
    ),
}

VACUOUS_TEST = "def test_vacuous():\n    assert True\n"


def _apply_fixed(ws: Path, fixed_files: list[tuple[str, str]]) -> None:
    for dest_rel, source_rel in fixed_files:
        text = (REPO_ROOT / source_rel).read_text(encoding="utf-8")
        (ws / dest_rel).write_text(text, encoding="utf-8")


def sweep_task(task_id: str, base_dir: Path) -> dict:
    fixed_files, regression_fixture = TASK_FIXTURES[task_id]
    result: dict = {"task_id": task_id, "agent_facing": regression_fixture is not None}

    # 1. Unfixed seed - the bug as an agent would first see it.
    ws = make_episode_workspace(base_dir=base_dir, episode_id=f"sweep-{task_id}-unfixed", task_id=task_id)
    report = verify_workspace(ws, task_id=task_id)
    result["unfixed_seed_reward"] = report["reward"]
    cleanup(ws)

    if regression_fixture is None:
        return result
    ws = make_episode_workspace(base_dir=base_dir, episode_id=f"sweep-{task_id}-fixnotest", task_id=task_id)
    _apply_fixed(ws, fixed_files)
    report = verify_workspace(ws, task_id=task_id)
    result["fixed_no_regression_test_reward"] = report["reward"]
    cleanup(ws)

    # 3. Real fix + real regression test - the full-reward case.
    ws = make_episode_workspace(base_dir=base_dir, episode_id=f"sweep-{task_id}-fixtest", task_id=task_id)
    _apply_fixed(ws, fixed_files)
    regression_text = (REPO_ROOT / regression_fixture).read_text(encoding="utf-8")
    (ws / get_task(task_id).regression_test_path).write_text(regression_text, encoding="utf-8")
    report = verify_workspace(ws, task_id=task_id)
    result["fixed_plus_real_regression_reward"] = report["reward"]
    result["regression_test_present"] = report["regression_test_present"]
    cleanup(ws)

    # 4. Real fix + vacuous regression test - must be rejected at 0.85.
    ws = make_episode_workspace(base_dir=base_dir, episode_id=f"sweep-{task_id}-vacuous", task_id=task_id)
    _apply_fixed(ws, fixed_files)
    (ws / get_task(task_id).regression_test_path).write_text(VACUOUS_TEST, encoding="utf-8")
    report = verify_workspace(ws, task_id=task_id)
    result["fixed_plus_vacuous_regression_reward"] = report["reward"]
    result["vacuous_regression_test_present"] = report["regression_test_present"]
    cleanup(ws)

    return result


def main() -> None:
    all_ids = all_task_ids()
    assert len(all_ids) == 15, f"expected 15 registered tasks, found {len(all_ids)}: {all_ids}"
    assert set(TASK_FIXTURES) == set(all_ids), (
        f"fixture map is out of sync with the registry: "
        f"missing={set(all_ids) - set(TASK_FIXTURES)} extra={set(TASK_FIXTURES) - set(all_ids)}"
    )

    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(tmp)
        results = [sweep_task(task_id, base_dir) for task_id in all_ids]

    out_path = REPO_ROOT / "results" / "task_verifier_sweep.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
