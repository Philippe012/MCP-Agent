from __future__ import annotations

import asyncio
import argparse
from pathlib import Path

from agents.loop import DEFAULT_MODEL, run_agent_episode
from harness.task_registry import DEFAULT_TASK_ID
from harness.workspace import make_episode_workspace
from harness.task_registry import get_task

SYSTEM_PROMPT = """You are a coding agent working in a small software repository.
You have tools to list files, read files, search code, write files, run the
test suite, and inspect the git diff. Use them to complete the task you are
given. Run the tests before declaring the task finished."""


async def run(
    workspace: Path,
    episode_id: str,
    trajectory_out_dir: Path,
    task_prompt: str,
    model: str,
    task_id: str = DEFAULT_TASK_ID,
) -> dict:
    return await run_agent_episode(
        workspace=workspace,
        episode_id=episode_id,
        agent_name="baseline",
        system_prompt=SYSTEM_PROMPT,
        task_prompt=task_prompt,
        trajectory_out_dir=trajectory_out_dir,
        model=model,
        require_approval=False,
        task_id=task_id,
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default="baseline-auto-01")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--task-id", default=DEFAULT_TASK_ID)
    ap.add_argument("--task-file", default=None, help="defaults to the task-id's own task.md")
    ap.add_argument("--out-dir", default="trajectories/baseline")
    args = ap.parse_args()

    task_file = args.task_file or get_task(args.task_id).task_file
    ws = make_episode_workspace(episode_id=args.episode, task_id=args.task_id)
    task_prompt = (Path(__file__).resolve().parents[1] / task_file).read_text(encoding="utf-8")
    report = asyncio.run(run(ws, args.episode, Path(args.out_dir), task_prompt, args.model, task_id=args.task_id))
    print(report)
