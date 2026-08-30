"""Run N episodes for both the baseline and advanced agents and save the comparison in results/results.json and results/results.md. It requires the anthropic package and an ANTHROPIC_API_KEY; see REPRODUCE.md for setup.
This is the script to rerun the experiment and update the measured improvement results.

Usage:
python -m eval.run_experiment --n 5 --model claude-opus-5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from harness.task_registry import DEFAULT_TASK_ID, get_task
from harness.workspace import make_episode_workspace, cleanup
from agents import baseline_agent, advanced_agent

REPO_ROOT = Path(__file__).resolve().parents[1]


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
    ap.add_argument("--n", type=int, default=3, help="episodes per agent")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--task-id", default=DEFAULT_TASK_ID, help="see harness/task_registry.py for the full list")
    ap.add_argument("--task-file", default=None, help="defaults to the task-id's own task.md")
    ap.add_argument("--keep-workspaces", action="store_true")
    ap.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ"),
        help="prefixes episode/trajectory filenames so a rerun doesn't overwrite a previous run's evidence",
    )
    args = ap.parse_args()
    asyncio.run(_main_async(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
