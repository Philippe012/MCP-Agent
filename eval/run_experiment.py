"""Run N episodes each of the baseline and advanced agents and write an
aggregate comparison to results/results.json and results/results.md.

Requires `pip install anthropic` and ANTHROPIC_API_KEY - see REPRODUCE.md.
This is the script a judge (or you) reruns to regenerate/extend the
Measured Improvement evidence beyond the two manually-driven reference
episodes already committed under trajectories/.

Usage:
    python -m eval.run_experiment --n 5 --model claude-opus-5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _summarize(reports: list[dict]) -> dict:
    rewards = [r["reward"] for r in reports]
    return {
        "n": len(reports),
        "mean_reward": round(statistics.mean(rewards), 4) if rewards else None,
        "min_reward": min(rewards) if rewards else None,
        "max_reward": max(rewards) if rewards else None,
        "behavior_pass_rate": round(sum(r["behavior_passed"] for r in reports) / len(reports), 4) if reports else None,
        "regression_test_rate": round(sum(r["regression_test_present"] for r in reports) / len(reports), 4) if reports else None,
    }


async def _main_async(args: argparse.Namespace) -> None:
    from harness.workspace import make_episode_workspace, cleanup
    from agents import baseline_agent, advanced_agent

    task_prompt = (REPO_ROOT / args.task_file).read_text(encoding="utf-8")

    results: dict[str, list[dict]] = {"baseline": [], "advanced": []}
    for i in range(1, args.n + 1):
        b_id = f"baseline-auto-{i:02d}"
        ws = make_episode_workspace(episode_id=b_id)
        report = await baseline_agent.run(ws, b_id, REPO_ROOT / "trajectories" / "baseline", task_prompt, args.model)
        results["baseline"].append({"episode_id": b_id, **report})
        if not args.keep_workspaces:
            cleanup(ws)

        a_id = f"advanced-auto-{i:02d}"
        ws = make_episode_workspace(episode_id=a_id)
        report = await advanced_agent.run(ws, a_id, REPO_ROOT / "trajectories" / "advanced", task_prompt, args.model)
        results["advanced"].append({"episode_id": a_id, **report})
        if not args.keep_workspaces:
            cleanup(ws)

    summary = {agent: _summarize(reports) for agent, reports in results.items()}
    out = {"model": args.model, "n_per_agent": args.n, "episodes": results, "summary": summary}

    out_dir = REPO_ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    md = ["# Automated experiment results", "", f"Model: `{args.model}`, {args.n} episodes per agent.", "", "| Agent | Mean reward | Behavior pass rate | Regression test rate |", "|---|---|---|---|"]
    for agent, s in summary.items():
        md.append(f"| {agent} | {s['mean_reward']} | {s['behavior_pass_rate']} | {s['regression_test_rate']} |")
    (out_dir / "results.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3, help="episodes per agent")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--task-file", default="tasks/bugfix_inventory/task.md")
    ap.add_argument("--keep-workspaces", action="store_true")
    args = ap.parse_args()
    asyncio.run(_main_async(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
