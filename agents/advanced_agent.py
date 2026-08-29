"""Advanced agent: structured plan -> implement -> verify -> checklist ->
approval policy.

Automates the exact protocol the manually-driven reference episode in
trajectories/advanced/ followed (see trajectories/README.md): read the
task and the existing tests, form an explicit plan against every numbered
requirement, implement, run the tests, re-check the diff against the full
requirements list (not just "did pytest exit 0"), and pass through a
human-approval checkpoint before the episode is allowed to finish.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from agents.loop import run_agent_episode

SYSTEM_PROMPT = """You are a coding agent working in a small software repository.
You have tools to list files, read files, search code, write files, run the
test suite, and inspect the git diff.

Follow this protocol:
1. Read the task statement and enumerate every numbered requirement it lists
   as an explicit checklist before writing any code.
2. Read the existing test file(s) to see what is already covered - do not
   assume the existing suite exercises every requirement.
3. Implement the fix.
4. Run the tests. A green run of the *existing* suite is not sufficient
   evidence of completion by itself if the checklist includes a requirement
   (e.g. a new regression test) that the existing suite could not have
   exercised - go back and satisfy it.
5. Re-check your changes against every item in the checklist from step 1,
   one by one, before declaring the task finished. Note: `git diff` only
   shows changes to files git already tracks - it will NOT show a newly
   created file, so do not rely on it alone to confirm a new test file was
   actually written; cross-check against run_tests output or list_files.
6. If a tool call fails or a test fails, diagnose the reason from the tool's
   output and retry with a corrected approach rather than giving up or
   ignoring it.
Only stop once every checklist item is genuinely satisfied."""


async def run(workspace: Path, episode_id: str, trajectory_out_dir: Path, task_prompt: str, model: str, interactive_approval: bool = False) -> dict:
    return await run_agent_episode(
        workspace=workspace,
        episode_id=episode_id,
        agent_name="advanced",
        system_prompt=SYSTEM_PROMPT,
        task_prompt=task_prompt,
        trajectory_out_dir=trajectory_out_dir,
        model=model,
        require_approval=True,
        interactive_approval=interactive_approval,
    )


if __name__ == "__main__":
    import argparse
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from harness.workspace import make_episode_workspace

    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default="advanced-auto-01")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--task-file", default="tasks/bugfix_inventory/task.md")
    ap.add_argument("--out-dir", default="trajectories/advanced")
    ap.add_argument("--interactive-approval", action="store_true")
    args = ap.parse_args()

    ws = make_episode_workspace(episode_id=args.episode)
    task_prompt = (Path(__file__).resolve().parents[1] / args.task_file).read_text(encoding="utf-8")
    report = asyncio.run(
        run(ws, args.episode, Path(args.out_dir), task_prompt, args.model, args.interactive_approval)
    )
    print(report)
