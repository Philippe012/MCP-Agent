"""Trajectory recording shared by every episode (manual or automated).

The hackathon submission requirements ask for trajectories that are "easy
to follow from the agent instructions through to the final result",
showing what each tool returned, the feedback that shaped the next step,
and any retries or human checkpoints. A raw chat/tool-call dump does not
satisfy that on its own, so every recorded step carries a short `note`
explaining *why* the agent took it and what the previous tool response
told it - the recorder enforces this by making `note` a required field.
"""

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
        self.steps.append(
            {
                "index": len(self.steps),
                "at": _now(),
                "t": round(time.monotonic() - self._t0, 3),
                "duration_s": round(duration_s, 3) if duration_s is not None else None,
                "tool": tool,
                "args": args,
                "success": success,
                "result_preview": result_str[:2000],
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
        self.verdict = verdict  # type: ignore[attr-defined]
        self.finished_at = _now()  # type: ignore[attr-defined]
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
        if data.get("verdict") is not None:
            t.verdict = data["verdict"]  # type: ignore[attr-defined]
        if data.get("finished_at") is not None:
            t.finished_at = data["finished_at"]  # type: ignore[attr-defined]
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
