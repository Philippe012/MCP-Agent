from __future__ import annotations

import time
import anthropic 
from pathlib import Path
from typing import Callable

from harness.mcp_client import MCPToolError, MCPToolSession
from harness.task_registry import DEFAULT_TASK_ID
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
    task_id: str = DEFAULT_TASK_ID,
    session_factory: Callable[[Path], object] = MCPToolSession,
) -> dict:
    
    client = anthropic.AsyncAnthropic(max_retries=5)
    traj = Trajectory(episode_id=episode_id, agent=agent_name, model=model, task=task_prompt)

    messages: list[dict] = [{"role": "user", "content": task_prompt}]

    async with session_factory(workspace) as session:
        turn = 0
        pending_failures: dict[str, int] = {}  # tool name -> index of its latest unresolved failure
        try:
            while turn < max_turns:
                turn += 1
                response = await client.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=TOOLS,
                    messages=messages,
                )

                if response.stop_reason != "tool_use":
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
                    except MCPToolError as exc:
                        result = str(exc)
                        is_error = True
                    duration_s = time.monotonic() - call_start

                    retry_of = pending_failures.pop(block.name, None)
                    traj.step(
                        block.name,
                        dict(block.input),
                        result,
                        note,
                        retry_of=retry_of,
                        success=not is_error,
                        duration_s=duration_s,
                    )
                    if is_error:
                        pending_failures[block.name] = traj.steps[-1]["index"]
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                            **({"is_error": True} if is_error else {}),
                        }
                    )

                messages.append({"role": "user", "content": tool_results})
                traj.save(trajectory_out_dir) 
            else:
                traj.truncated_by_max_turns = True
        except Exception:
            traj.save(trajectory_out_dir)
            raise

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

    report = verify_workspace(workspace, task_id=task_id)
    traj.finish(report)
    traj.save(trajectory_out_dir)
    return report
