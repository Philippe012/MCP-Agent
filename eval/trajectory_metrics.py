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
    retry_targets = {s["retry_of"] for s in steps if s.get("retry_of") is not None}
    recovered_from_failure = any(f["index"] in retry_targets for f in failures)

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
        "recovered_from_failure": recovered_from_failure,
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
        try:
            trajectory = json.loads(path.read_text(encoding="utf-8"))
            print(json.dumps(compute(trajectory), indent=2))
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            print(json.dumps({"error": str(exc), "file": str(path)}))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
