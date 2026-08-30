"""Manual Anthropic tool-use loop shared by the baseline and advanced agents.

Kept manual so tool calls, retries, and human approval stay under our control
without relying on the SDK's beta tool_runner.

Requires anthropic and ANTHROPIC_API_KEY. See REPRODUCE.md.
"""

from __future__ import annotations

import time
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

    `task_id` must match the task_id the workspace was actually seeded
    with (harness/workspace.py's make_episode_workspace) - it's not
    inferred from the workspace, so the caller is responsible for keeping
    the two in sync (mirrors how MCP_RL_ENV_ROOT has no silent fallback:
    an explicit, possibly-wrong value fails loudly and correctably, a
    guessed one wouldn't). `session_factory` swaps in a
    FaultInjectingMCPToolSession (harness/fault_injection.py) for
    robustness experiments; defaults to a real, unmodified MCPToolSession.
    """
    import anthropic  # imported lazily so the rest of the harness works without the package installed

    # AsyncAnthropic, not the sync client: run_agent_episode runs inside an
    # event loop (many episodes get driven concurrently by
    # eval/run_experiment.py), and a sync client.messages.create() call
    # would block that loop for the whole request, silently serializing
    # everything anyway. max_retries is raised from the SDK default (2) to
    # 5: the client already retries RateLimitError/APIConnectionError/
    # InternalServerError with exponential backoff on its own (see
    # anthropic's own retry handling) - a second, hand-written retry loop
    # here would just duplicate that. What the SDK can't do for us is save
    # our own trajectory state, so if retries are ultimately exhausted the
    # `except Exception` below still saves whatever was captured before
    # re-raising, instead of losing the whole episode.
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
                    except MCPToolError as exc:
                        # A genuine tool failure (the real MCP server
                        # reported one) - this is the recovery signal we
                        # want to measure. Anything else raised by
                        # session.call (a transport problem, a bug in our
                        # own client) is NOT caught here on purpose: it
                        # should crash the episode loudly via the outer
                        # `except Exception` below, not get silently
                        # recorded as if the agent had hit a normal tool
                        # error.
                        result = str(exc)
                        is_error = True
                    duration_s = time.monotonic() - call_start

                    # A call is a retry of the most recent unresolved
                    # failure of the *same tool name* - not just the
                    # immediately preceding step, since a real recovery
                    # often has other tool calls (e.g. list_files) in
                    # between a failed read_file and the corrected one.
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
                traj.save(trajectory_out_dir)  # incremental: a crash on the next turn shouldn't erase this one
            else:
                # The while condition went false without a `break`, i.e.
                # the loop ran out of turns rather than the model deciding
                # it was done - record that distinction so it isn't
                # silently conflated with a normal finish downstream.
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
