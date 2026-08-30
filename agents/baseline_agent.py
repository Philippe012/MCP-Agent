"""Baseline agent: minimal-instruction, single-pass policy.

This is the exact protocol the manually-driven reference episode in
trajectories/baseline/ followed (see trajectories/README.md), automated so
it can be re-run at scale with a real Anthropic API key. It deliberately
gives the model no more guidance than "fix the bug, use the tools, run
tests before finishing" - no explicit requirements checklist, no forced
self-verification loop, no human-approval checkpoint. This is the
comparison point the advanced agent (agents/advanced_agent.py) is measured
against.
"""

from __future__ import annotations

import asyncio
import argparse
from pathlib import Path

from agents.loop import DEFAULT_MODEL, run_agent_episode
from harness.workspace import make_episode_workspace

SYSTEM_PROMPT = """You are a coding agent working in a small software repository.
You have tools to list files, read files, search code, write files, run the
test suite, and inspect the git diff. Use them to complete the task you are
given. Run the tests before declaring the task finished."""


async def run(workspace: Path, episode_id: str, trajectory_out_dir: Path, task_prompt: str, model: str) -> dict:
    return await run_agent_episode(
        workspace=workspace,
        episode_id=episode_id,
        agent_name="baseline",
        system_prompt=SYSTEM_PROMPT,
        task_prompt=task_prompt,
        trajectory_out_dir=trajectory_out_dir,
        model=model,
        require_approval=False,
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default="baseline-auto-01")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--task-file", default="tasks/bugfix_inventory/task.md")
    ap.add_argument("--out-dir", default="trajectories/baseline")
    args = ap.parse_args()

    ws = make_episode_workspace(episode_id=args.episode)
    task_prompt = (Path(__file__).resolve().parents[1] / args.task_file).read_text(encoding="utf-8")
    report = asyncio.run(run(ws, args.episode, Path(args.out_dir), task_prompt, args.model))
    print(report)
