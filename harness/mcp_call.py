"""One-shot CLI: make exactly one real MCP tool call against an episode
workspace, print the result, and (optionally) append it to that episode's
trajectory file.

Why this exists: a live coding-agent turn is naturally one decision at a
time - read something, think about what it means, decide the next call.
This CLI lets a human-in-the-loop or manually-driven agent session issue
genuine MCP tool calls one at a time (each a fresh, short-lived client
connection to the real server.py over real stdio transport) while still
producing the exact same trajectory record format the automated
`agents/*.py` loop produces. It is not a shortcut around MCP: every call
here goes through mcp.client.stdio -> server.py -> tools.py, identically to
an autonomous agent.

Usage:
  python -m harness.mcp_call <workspace> <tool> [key=value ...]
      --episode ID --agent baseline|advanced --model "..." --task "..."
      --note "reasoning for this step" [--retry-of N] [--out-dir DIR]

  # mark the episode finished and score it:
  python -m harness.mcp_call <workspace> --finish --episode ID [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from harness.mcp_client import MCPToolSession
from harness.trajectory import Trajectory
from harness.verifier import verify_workspace

DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "trajectories"


def _parse_kv(pairs: list[str]) -> dict:
    args = {}
    for p in pairs:
        if "=" not in p:
            raise SystemExit(f"expected key=value, got: {p}")
        k, v = p.split("=", 1)
        try:
            args[k] = json.loads(v)
        except json.JSONDecodeError:
            args[k] = v
    return args


async def _call(workspace: Path, tool: str, kwargs: dict):
    async with MCPToolSession(workspace) as s:
        return await s.call(tool, **kwargs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace")
    ap.add_argument("tool", nargs="?")
    ap.add_argument("kv", nargs="*")
    ap.add_argument("--episode", required=True)
    ap.add_argument("--agent")
    ap.add_argument("--model")
    ap.add_argument("--task")
    ap.add_argument("--note")
    ap.add_argument("--retry-of", type=int, default=None)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--finish", action="store_true")
    ap.add_argument("--checkpoint", choices=["finalize"], default=None)
    ap.add_argument("--approved", action="store_true")
    ap.add_argument("--auto", action="store_true")
    args = ap.parse_args()

    workspace = Path(args.workspace)
    out_dir = Path(args.out_dir)
    json_path = out_dir / f"{args.episode}.json"

    if json_path.exists():
        traj = Trajectory.load(json_path)
    else:
        if not (args.agent and args.model and args.task):
            raise SystemExit("first call for a new episode needs --agent --model --task")
        traj = Trajectory(episode_id=args.episode, agent=args.agent, model=args.model, task=args.task)

    if args.checkpoint == "finalize":
        traj.checkpoint(
            "finalize",
            args.note or "agent believes the task is complete; requesting approval before ending the episode",
            approved=args.approved,
            auto=args.auto,
        )
        traj.save(out_dir)
        print("checkpoint recorded")
        return 0

    if args.finish:
        report = verify_workspace(workspace)
        traj.finish(report)
        traj.save(out_dir)
        print(json.dumps(report, indent=2))
        return 0

    if not args.tool:
        raise SystemExit("tool is required unless --finish or --checkpoint is given")
    if not args.note:
        raise SystemExit("--note is required: explain the reasoning for this step")

    kwargs = _parse_kv(args.kv)
    start = time.monotonic()
    try:
        result = asyncio.run(_call(workspace, args.tool, kwargs))
        error = None
    except Exception as exc:  # noqa: BLE001 - we want to record real tool failures too
        result = None
        error = str(exc)
    duration_s = time.monotonic() - start

    traj.step(
        args.tool,
        kwargs,
        error if error else result,
        args.note,
        retry_of=args.retry_of,
        success=error is None,
        duration_s=duration_s,
    )
    traj.save(out_dir)

    if error:
        print(f"ERROR: {error}")
        return 1
    print(json.dumps(result, indent=2) if not isinstance(result, str) else result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
