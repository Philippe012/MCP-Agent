"""Compute trajectory-level metrics from a saved trajectory JSON file.

The verifier's reward is the authoritative correctness signal; this is
complementary evidence about *how* an episode got there - useful for
studying tool-use behavior (planning, retries, recovery) separately from
whether the final repository state happened to be correct. Every number
here is read directly off the trajectory file - nothing is estimated or
inferred about the model's internal reasoning.

Usage:
    python -m eval.trajectory_metrics trajectories/advanced/manual-advanced-01.json
    python -m eval.trajectory_metrics trajectories/**/*.json   # summarize several
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path


def compute(trajectory: dict) -> dict:
    steps = trajectory["steps"]
    tool_counts: dict[str, int] = {}
    for s in steps:
        tool_counts[s["tool"]] = tool_counts.get(s["tool"], 0) + 1

    failures = [s for s in steps if not s.get("success", True)]
    retries = [s for s in steps if s.get("retry_of") is not None]
    durations = [s["duration_s"] for s in steps if s.get("duration_s") is not None]

    return {
        "episode_id": trajectory["episode_id"],
        "agent": trajectory["agent"],
        "tool_call_count": len(steps),
        "tool_call_breakdown": tool_counts,
        "distinct_files_touched": sorted(
            {s["args"]["path"] for s in steps if "path" in s.get("args", {})}
        ),
        "failed_call_count": len(failures),
        "retry_count": len(retries),
        "recovered_from_failure": len(failures) > 0 and len(retries) > 0,
        "checkpoint_count": len(trajectory.get("checkpoints", [])),
        "total_tool_time_s": round(sum(durations), 3) if durations else None,
        "reward": (trajectory.get("verdict") or {}).get("reward"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="trajectory .json file(s) or glob pattern(s)")
    args = ap.parse_args()

    files: list[Path] = []
    for pattern in args.paths:
        matched = glob.glob(pattern, recursive=True)
        files.extend(Path(p) for p in (matched or [pattern]))

    for path in files:
        trajectory = json.loads(path.read_text(encoding="utf-8"))
        print(json.dumps(compute(trajectory), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
