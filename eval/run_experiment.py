"""Run N episodes for both the baseline and advanced agents and save the comparison in results/results.json and results/results.md. It requires the anthropic package and an ANTHROPIC_API_KEY; see REPRODUCE.md for setup.
This is the script to rerun the experiment and update the measured improvement results.

Single-task usage (unchanged from before this file supported multiple
tasks - writes results/results.json and results/results.md exactly as
always):
python -m eval.run_experiment --n 5 --model claude-opus-5 --task-id bugfix_inventory

Multi-task usage (writes the separate results/multitask_results.json and
results/multitask_results.md instead, so a multi-task run can never
silently overwrite a single-task run's evidence or vice versa):
python -m eval.run_experiment --n 5 --task-ids bugfix_inventory ledger_transfer_rollback
python -m eval.run_experiment --n 5 --all-tasks

Both forms need a real ANTHROPIC_API_KEY - see REPRODUCE.md. `--all-tasks`
runs every *agent-facing* task in harness/task_registry.py; it never
includes `edge_case_coverage`, which is an evaluator-only fixture, not a
live-agent task (see its own task.md). Naming `edge_case_coverage`
explicitly via --task-ids is also refused, for the same reason.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from harness.task_registry import DEFAULT_TASK_ID, all_task_ids, get_task
from harness.workspace import make_episode_workspace, cleanup
from agents import baseline_agent, advanced_agent

REPO_ROOT = Path(__file__).resolve().parents[1]

# Tasks that exist in the registry but are deliberately not shown to a
# live agent (see each one's own task.md). A live baseline/advanced run
# must never be pointed at one of these, whether via --all-tasks or an
# explicit --task-ids.
NON_AGENT_FACING_TASK_IDS = frozenset({"edge_case_coverage"})


def _summarize(reports: list[dict]) -> dict:
    rewards = [r.get("reward", 0.0) for r in reports]
    return {
        "n": len(reports),
        "mean_reward": round(statistics.mean(rewards), 4) if rewards else None,
        "median_reward": round(statistics.median(rewards), 4) if rewards else None,
        # A sample standard deviation needs at least 2 points; below that
        # it's not a meaningful spread, so leave it unreported (None)
        # rather than print 0.0, which would misleadingly look like "no
        # variance was observed" instead of "not enough data to say."
        "stdev_reward": round(statistics.stdev(rewards), 4) if len(rewards) >= 2 else None,
        "min_reward": min(rewards) if rewards else None,
        "max_reward": max(rewards) if rewards else None,
        "behavior_pass_rate": round(sum(r.get("behavior_passed", False) for r in reports) / len(reports), 4) if reports else None,
        "regression_test_rate": round(sum(r.get("regression_test_present", False) for r in reports) / len(reports), 4) if reports else None,
        # No confidence interval is computed here even for larger n: this
        # project's actual sample sizes (n=1-5 per REPRODUCE.md's cost
        # estimate) are too small for a normal-approximation CI to mean
        # anything, and manufacturing one would look more rigorous than
        # the evidence actually is. Report n, mean, median, and stdev
        # honestly instead; a reviewer wanting a CI can compute one from
        # the per-episode rewards in "episodes" below at whatever n they
        # actually ran.
    }


def _write_results(args: argparse.Namespace, results: dict[str, list[dict]]) -> None:
    summary = {agent: _summarize(reports) for agent, reports in results.items()}
    out = {"model": args.model, "run_id": args.run_id, "n_per_agent": args.n, "episodes": results, "summary": summary}

    out_dir = REPO_ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    md = [
        "# Automated experiment results",
        "",
        f"Run: `{args.run_id}`, model `{args.model}`, {args.n} episodes per agent.",
        "",
        "| Agent | N | Mean reward | Median reward | Stdev reward | Min | Max | Behavior pass rate | Regression test rate |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for agent, s in summary.items():
        md.append(
            f"| {agent} | {s['n']} | {s['mean_reward']} | {s['median_reward']} | {s['stdev_reward']} | "
            f"{s['min_reward']} | {s['max_reward']} | {s['behavior_pass_rate']} | {s['regression_test_rate']} |"
        )
    if args.n < 5:
        md += [
            "",
            f"**N={args.n} per agent is a small sample** - treat these numbers as "
            "preliminary/mechanistic evidence, not a statistically powered claim. "
            "See RESEARCH.md and results/results.md for how this project "
            "distinguishes a deterministic-mechanism finding (no sampling "
            "variance, repeated runs add no information) from a genuinely "
            "stochastic one like this (LLM sampling variance, where N matters).",
        ]
    (out_dir / "results.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def agent_facing_task_ids() -> tuple[str, ...]:
    """Every registered task except the evaluator-only fixtures - the set
    --all-tasks runs, and the set an explicit --task-ids selection is
    checked against."""
    return tuple(t for t in all_task_ids() if t not in NON_AGENT_FACING_TASK_IDS)


def resolve_task_ids(args: argparse.Namespace) -> list[str]:
    """Turn --task-id / --task-ids / --all-tasks into the actual list of
    task IDs to run, without touching any registry or verifier state.

    Precedence matches argparse.error's own contract: --all-tasks and
    --task-ids are mutually exclusive (enforced by the caller); when
    neither is given, this returns exactly [args.task_id], which is the
    single-task path that existed before multi-task support was added -
    that path's behavior is otherwise untouched.
    """
    if args.all_tasks:
        return list(agent_facing_task_ids())
    if args.task_ids:
        non_agent_facing = [t for t in args.task_ids if t in NON_AGENT_FACING_TASK_IDS]
        if non_agent_facing:
            raise SystemExit(
                f"refusing to run a live agent against non-agent-facing task(s) "
                f"{non_agent_facing}: these are evaluator-only fixtures, never shown "
                "to a live agent (see each one's own task.md)."
            )
        for task_id in args.task_ids:
            get_task(task_id)  # raises KeyError (with the full registered list) if unknown
        return list(args.task_ids)
    return [args.task_id]


def _aggregate_multi_task(per_task: dict[str, dict[str, list[dict]]]) -> dict:
    """Per-task summaries, plus one overall summary pooling every episode
    of each agent across every selected task. Pure function of already-
    collected reports - no I/O, so it's directly unit-testable."""
    per_task_summary = {
        task_id: {agent: _summarize(reports) for agent, reports in results.items()}
        for task_id, results in per_task.items()
    }
    overall: dict[str, list[dict]] = {"baseline": [], "advanced": []}
    for results in per_task.values():
        for agent, reports in results.items():
            overall.setdefault(agent, []).extend(reports)
    overall_summary = {agent: _summarize(reports) for agent, reports in overall.items()}
    return {"per_task": per_task_summary, "overall": overall_summary}


def _write_multi_task_results(
    args: argparse.Namespace, task_ids: list[str], per_task: dict[str, dict[str, list[dict]]]
) -> None:
    """Same incremental-save discipline as _write_results: called after
    every single episode, so a crash on task 3 of 5 doesn't lose the first
    two tasks' results. Writes to multitask_results.{json,md} - a separate
    file from results.{json,md}, so a multi-task run can never overwrite a
    single-task run's evidence, and running both cannot clobber each
    other regardless of order."""
    aggregate = _aggregate_multi_task(per_task)
    out = {
        "model": args.model,
        "run_id": args.run_id,
        "n_per_agent_per_task": args.n,
        "task_ids": task_ids,
        "episodes": per_task,
        "per_task_summary": aggregate["per_task"],
        "overall_summary": aggregate["overall"],
    }

    out_dir = REPO_ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "multitask_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    md = [
        "# Automated multi-task experiment results",
        "",
        f"Run: `{args.run_id}`, model `{args.model}`, {args.n} episode(s) per agent per task, "
        f"{len(task_ids)} task(s): {', '.join(task_ids)}.",
        "",
        "This aggregates real episodes only - a task with 0 completed episodes so far "
        "(e.g. a crash before its first episode finished) is simply absent below, not "
        "reported as a zero.",
        "",
        "## Per-task results",
        "",
        "| Task | Agent | N | Mean reward | Median reward | Stdev reward | Min | Max | Behavior pass rate | Regression test rate |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for task_id, agents in aggregate["per_task"].items():
        for agent, s in agents.items():
            if s["n"] == 0:
                continue
            md.append(
                f"| {task_id} | {agent} | {s['n']} | {s['mean_reward']} | {s['median_reward']} | {s['stdev_reward']} | "
                f"{s['min_reward']} | {s['max_reward']} | {s['behavior_pass_rate']} | {s['regression_test_rate']} |"
            )
    md += [
        "",
        "## Aggregate across the selected task set",
        "",
        "| Agent | N | Mean reward | Median reward | Stdev reward | Min | Max | Behavior pass rate | Regression test rate |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for agent, s in aggregate["overall"].items():
        if s["n"] == 0:
            continue
        md.append(
            f"| {agent} | {s['n']} | {s['mean_reward']} | {s['median_reward']} | {s['stdev_reward']} | "
            f"{s['min_reward']} | {s['max_reward']} | {s['behavior_pass_rate']} | {s['regression_test_rate']} |"
        )
    if args.n < 5:
        md += [
            "",
            f"**N={args.n} per agent per task is a small sample** - treat these numbers "
            "as preliminary/mechanistic evidence, not a statistically powered claim, "
            "exactly as results.md's own single-task caveat says.",
        ]
    (out_dir / "multitask_results.md").write_text("\n".join(md) + "\n", encoding="utf-8")


async def _run_multi_task(args: argparse.Namespace, task_ids: list[str]) -> None:
    """Runs baseline + advanced, args.n episodes each, on every task in
    task_ids, in the same environment/tools/verifier/scoring every
    single-task run already uses (make_episode_workspace + baseline_agent
    .run / advanced_agent.run + verify.py, unchanged) - this function only
    adds the loop over tasks and the aggregation, nothing about how one
    episode is run or scored."""
    per_task: dict[str, dict[str, list[dict]]] = {}
    for task_id in task_ids:
        task_prompt = (REPO_ROOT / get_task(task_id).task_file).read_text(encoding="utf-8")
        results: dict[str, list[dict]] = {"baseline": [], "advanced": []}
        per_task[task_id] = results

        for i in range(1, args.n + 1):
            b_id = f"{args.run_id}-{task_id}-baseline-{i:02d}"
            ws = make_episode_workspace(episode_id=b_id, task_id=task_id)
            report = await baseline_agent.run(
                ws, b_id, REPO_ROOT / "trajectories" / "baseline", task_prompt, args.model, task_id=task_id
            )
            results["baseline"].append({"episode_id": b_id, **report})
            if not args.keep_workspaces:
                cleanup(ws)
            _write_multi_task_results(args, task_ids, per_task)

            a_id = f"{args.run_id}-{task_id}-advanced-{i:02d}"
            ws = make_episode_workspace(episode_id=a_id, task_id=task_id)
            report = await advanced_agent.run(
                ws, a_id, REPO_ROOT / "trajectories" / "advanced", task_prompt, args.model, task_id=task_id
            )
            results["advanced"].append({"episode_id": a_id, **report})
            if not args.keep_workspaces:
                cleanup(ws)
            _write_multi_task_results(args, task_ids, per_task)

    print(json.dumps(_aggregate_multi_task(per_task), indent=2))


async def _main_async(args: argparse.Namespace) -> None:
    task_file = args.task_file or get_task(args.task_id).task_file
    task_prompt = (REPO_ROOT / task_file).read_text(encoding="utf-8")

    results: dict[str, list[dict]] = {"baseline": [], "advanced": []}
    for i in range(1, args.n + 1):
        b_id = f"{args.run_id}-baseline-{i:02d}"
        ws = make_episode_workspace(episode_id=b_id, task_id=args.task_id)
        report = await baseline_agent.run(
            ws, b_id, REPO_ROOT / "trajectories" / "baseline", task_prompt, args.model, task_id=args.task_id
        )
        results["baseline"].append({"episode_id": b_id, **report})
        if not args.keep_workspaces:
            cleanup(ws)
        _write_results(args, results)  # incremental: a later episode's crash shouldn't lose this one

        a_id = f"{args.run_id}-advanced-{i:02d}"
        ws = make_episode_workspace(episode_id=a_id, task_id=args.task_id)
        report = await advanced_agent.run(
            ws, a_id, REPO_ROOT / "trajectories" / "advanced", task_prompt, args.model, task_id=args.task_id
        )
        results["advanced"].append({"episode_id": a_id, **report})
        if not args.keep_workspaces:
            cleanup(ws)
        _write_results(args, results)

    print(json.dumps({agent: _summarize(reports) for agent, reports in results.items()}, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3, help="episodes per agent (per task, in multi-task mode)")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument(
        "--task-id",
        default=DEFAULT_TASK_ID,
        help="single task to run (default mode - unchanged single-task behavior). "
        "Ignored if --task-ids or --all-tasks is given.",
    )
    ap.add_argument(
        "--task-ids",
        nargs="+",
        default=None,
        help="run multiple named tasks (baseline+advanced on each); switches to multi-task "
        "output (results/multitask_results.{json,md}). Cannot include edge_case_coverage "
        "(evaluator-only, not agent-facing).",
    )
    ap.add_argument(
        "--all-tasks",
        action="store_true",
        help="run every agent-facing task in harness/task_registry.py (excludes edge_case_coverage). "
        "Switches to multi-task output like --task-ids.",
    )
    ap.add_argument(
        "--task-file", default=None, help="defaults to the task-id's own task.md (single-task mode only)"
    )
    ap.add_argument("--keep-workspaces", action="store_true")
    ap.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ"),
        help="prefixes episode/trajectory filenames so a rerun doesn't overwrite a previous run's evidence",
    )
    args = ap.parse_args()

    if args.all_tasks and args.task_ids:
        ap.error("--all-tasks and --task-ids are mutually exclusive")

    if args.all_tasks or args.task_ids:
        task_ids = resolve_task_ids(args)
        asyncio.run(_run_multi_task(args, task_ids))
    else:
        # Unchanged single-task path: same function, same output files
        # (results/results.json, results/results.md) as before multi-task
        # support existed.
        asyncio.run(_main_async(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
