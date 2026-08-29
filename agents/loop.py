"""Manual Anthropic tool-use loop shared by baseline_agent.py and
advanced_agent.py.

A manual loop (rather than the SDK's beta tool_runner) was chosen
deliberately: it keeps every tool call, retry, and the human-approval
checkpoint under this project's explicit control instead of a beta
helper's, and avoids an extra beta SDK dependency
(`anthropic[mcp]`/tool_runner) for something this small. See
shared/tool-use-concepts.md in the claude-api skill for the tradeoff.

Requires `pip install anthropic` and an ANTHROPIC_API_KEY in the
environment - see REPRODUCE.md.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from harness.mcp_client import MCPToolSession
from harness.trajectory import Trajectory
from harness.verifier import verify_workspace
from agents.tool_schemas import TOOLS

DEFAULT_MODEL = "claude-opus-5"
DEFAULT_MAX_TURNS = 15


def _reasoning_note(content_blocks) -> str:
    texts = [b.text for b in content_blocks if getattr(b, "type", None) == "text" and b.text.strip()]
    return " ".join(texts) if texts else "(model called the tool without narrating its reasoning)"


async def run_agent_episode(
    *,
    workspace: Path,
    episode_id: str,
    agent_name: str,
    system_prompt: str,
    task_prompt: str,
    trajectory_out_dir: Path,
    model: str = DEFAULT_MODEL,
    max_turns: int = DEFAULT_MAX_TURNS,
    require_approval: bool = False,
    interactive_approval: bool = False,
    approval_hook: Callable[[str], bool] | None = None,
) -> dict:
    """Run one episode: agent <-> real MCP server, until the model stops
    calling tools or `max_turns` is hit. Returns the verifier's report.

    `require_approval=True` adds a human-approval checkpoint before the
    episode is allowed to finish (Rule Book: gate consequential actions
    behind a sandbox + human approval). In batch/unattended runs
    (`interactive_approval=False`) the checkpoint is auto-approved and the
    fact that it was auto- rather than human-approved is recorded in the
    trajectory, not hidden. Pass `interactive_approval=True` (with an
    optional `approval_hook`, default: a real terminal prompt) to make it
    a genuine blocking approval.
    """
    import anthropic  # imported lazily so the rest of the harness works without the package installed

    client = anthropic.Anthropic()
    traj = Trajectory(episode_id=episode_id, agent=agent_name, model=model, task=task_prompt)

    messages: list[dict] = [{"role": "user", "content": task_prompt}]

    async with MCPToolSession(workspace) as session:
        turn = 0
        while turn < max_turns:
            turn += 1
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                # end_turn, max_tokens, or anything else: the model believes it is done (or stuck).
                break

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            note = _reasoning_note(response.content)
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in tool_use_blocks:
                call_start = time.monotonic()
                try:
                    result = await session.call(block.name, **block.input)
                    is_error = False
                except Exception as exc:  # noqa: BLE001 - a real tool failure is exactly what we want to record
                    result = str(exc)
                    is_error = True
                duration_s = time.monotonic() - call_start

                traj.step(
                    block.name,
                    dict(block.input),
                    result,
                    note,
                    retry_of=None,
                    success=not is_error,
                    duration_s=duration_s,
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                        **({"is_error": True} if is_error else {}),
                    }
                )

            messages.append({"role": "user", "content": tool_results})

    if require_approval:
        approved = True
        if interactive_approval:
            hook = approval_hook or (lambda summary: input(f"{summary}\nApprove and finish? [y/N] ").strip().lower() == "y")
            approved = hook(f"Episode {episode_id}: agent believes the task is complete.")
        traj.checkpoint(
            "finalize",
            "Agent believes the task is complete; requesting approval before ending the episode.",
            approved=approved,
            auto=not interactive_approval,
        )

    report = verify_workspace(workspace)
    traj.finish(report)
    traj.save(trajectory_out_dir)
    return report
