from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import time


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Trajectory:
    episode_id: str
    agent: str  # "baseline" | "advanced"
    model: str  # e.g. "claude-sonnet-5 (manual, this session)" or "scripted-demo"
    task: str
    started_at: str = field(default_factory=_now)
    steps: list[dict] = field(default_factory=list)
    checkpoints: list[dict] = field(default_factory=list)
    # Distinguishes "the model decided it was done" (False) from "the loop
    # hit max_turns and cut the episode off" (True) - without this, both
    # look identical downstream and get silently conflated in any
    # success/failure statistics across episodes.
    truncated_by_max_turns: bool = False
    _t0: float = field(default_factory=time.monotonic, repr=False)

    def step(
        self,
        tool: str,
        args: dict,
        result,
        note: str,
        retry_of: int | None = None,
        success: bool = True,
        duration_s: float | None = None,
    ) -> None:
        """Record one tool call. `note` must explain the reasoning: what
        the previous result showed and why this call follows from it.

        `success` is the tool's own observable outcome (did the call raise
        / return an error), not a judgment about whether the call was a
        good idea - that distinction matters for studying tool-use
        reliability separately from task strategy. `duration_s`, when
        supplied, is this call's own wall-clock time (not the cumulative
        `t` below, which is time since the episode started).
        """
        if not note:
            raise ValueError("every trajectory step must carry a reasoning note")
        result_str = result if isinstance(result, str) else json.dumps(result, default=str)
        cap = 8000 if tool == "run_tests" else 2000  # pytest failure output easily exceeds 2000 chars
        self.steps.append(
            {
                "index": len(self.steps),
                "at": _now(),
                "t": round(time.monotonic() - self._t0, 3),
                "duration_s": round(duration_s, 3) if duration_s is not None else None,
                "tool": tool,
                "args": args,
                "success": success,
                "result_preview": result_str[:cap],
                "note": note,
                "retry_of": retry_of,
            }
        )

    def checkpoint(self, kind: str, message: str, approved: bool, auto: bool) -> None:
        """Record a human-approval checkpoint (Rule Book: consequential
        actions get a sandbox + human approval before they happen)."""
        self.checkpoints.append(
            {
                "t": round(time.monotonic() - self._t0, 3),
                "kind": kind,
                "message": message,
                "approved": approved,
                "auto_approved": auto,
                "at": _now(),
            }
        )

    def finish(self, verdict: dict) -> dict:
        self.verdict = verdict  
        self.finished_at = _now()  
        return self.to_dict()

    def to_dict(self) -> dict:
        d = {
            "episode_id": self.episode_id,
            "agent": self.agent,
            "model": self.model,
            "task": self.task,
            "started_at": self.started_at,
            "finished_at": getattr(self, "finished_at", None),
            "steps": self.steps,
            "checkpoints": self.checkpoints,
            "verdict": getattr(self, "verdict", None),
            "tool_call_count": len(self.steps),
            "retry_count": sum(1 for s in self.steps if s["retry_of"] is not None),
            "truncated_by_max_turns": self.truncated_by_max_turns,
        }
        return d

    @classmethod
    def load(cls, json_path: Path) -> "Trajectory":
        data = json.loads(json_path.read_text(encoding="utf-8"))
        t = cls(
            episode_id=data["episode_id"],
            agent=data["agent"],
            model=data["model"],
            task=data["task"],
            started_at=data["started_at"],
        )
        t.steps = data["steps"]
        t.checkpoints = data["checkpoints"]
        t.truncated_by_max_turns = data.get("truncated_by_max_turns", False)
        # _t0 otherwise resets to "now", making `t` jump backward on every
        # step recorded after a load() - mcp_call.py loads, appends one
        # step, saves, and exits per invocation, so this runs on every step
        # of every manually-driven episode. Anchoring to the last step's
        # `t` keeps it monotonically increasing across process boundaries.
        last_t = t.steps[-1]["t"] if t.steps else 0.0
        t._t0 = time.monotonic() - last_t
        if data.get("verdict") is not None:
            t.verdict = data["verdict"] 
        if data.get("finished_at") is not None:
            t.finished_at = data["finished_at"]  
        return t

    def save(self, out_dir: Path) -> tuple[Path, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / f"{self.episode_id}.json"
        md_path = out_dir / f"{self.episode_id}.md"
        json_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        md_path.write_text(self._render_markdown(), encoding="utf-8")
        return json_path, md_path

    def _render_markdown(self) -> str:
        lines = [
            f"# Trajectory: {self.episode_id} ({self.agent})",
            "",
            f"- **Agent**: {self.agent}",
            f"- **Model**: {self.model}",
            f"- **Task**: {self.task}",
            f"- **Started**: {self.started_at}",
            f"- **Finished**: {getattr(self, 'finished_at', None)}",
            f"- **Ended because**: {'hit max_turns (cut off)' if self.truncated_by_max_turns else 'model decided it was done'}",
            "",
            "## Steps",
            "",
        ]
        for s in self.steps:
            retry = f" (retry of step {s['retry_of']})" if s["retry_of"] is not None else ""
            status = "OK" if s.get("success", True) else "FAILED"
            duration = f", call took {s['duration_s']}s" if s.get("duration_s") is not None else ""
            lines.append(f"### Step {s['index']}: `{s['tool']}`{retry}  _t={s['t']}s{duration}, {status}_")
            lines.append("")
            lines.append(f"**Reasoning / feedback used:** {s['note']}")
            lines.append("")
            lines.append(f"**Args:** `{json.dumps(s['args'], default=str)}`")
            lines.append("")
            lines.append("**Tool response:**")
            lines.append("```")
            lines.append(s["result_preview"])
            lines.append("```")
            lines.append("")
        if self.checkpoints:
            lines.append("## Human-approval checkpoints")
            lines.append("")
            for c in self.checkpoints:
                approval = "auto-approved (batch mode)" if c["auto_approved"] else "approved by human reviewer"
                lines.append(f"- **{c['kind']}** at t={c['t']}s: {c['message']} -> {approval if c['approved'] else 'REJECTED'}")
            lines.append("")
        verdict = getattr(self, "verdict", None)
        if verdict:
            lines.append("## Final verdict (from the deterministic verifier)")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(verdict, indent=2))
            lines.append("```")
        return "\n".join(lines)
