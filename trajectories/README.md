# Agent trajectories

This directory holds the trajectory record for every episode run against
the `bugfix_inventory` task, in the shared format written by
[harness/trajectory.py](../harness/trajectory.py): a `.json` (machine
format, also used by `harness/verifier.py` and `eval/run_experiment.py`)
and a matching `.md` (human-readable transcript) per episode.

## What produced these

Coding-agent use for this submission is **Claude Code** (model
`claude-sonnet-5`), disclosed per the hackathon rules. Two kinds of episode
live in this repo, and every trajectory file states which kind it is via
its `model` field:

1. **Manually-driven reference episodes**
   (`trajectories/baseline/manual-baseline-01.*`,
   `trajectories/advanced/manual-advanced-01.*`,
   `trajectories/advanced/manual-recovery-01.*`) - Claude (this coding
   session) played the coding-agent role directly: reading the task,
   diagnosing the bug, and issuing real MCP tool calls one at a time
   through [harness/mcp_call.py](../harness/mcp_call.py) against a freshly
   seeded, isolated workspace, exactly as an autonomous agent turn would.
   Each call goes through the real `mcp.client.stdio` transport into the
   real `server.py` - nothing about the tool execution path is mocked or
   shortcut. The only thing that differs from an unattended run is that
   the tool-call sequence was driven turn-by-turn by this session rather
   than by an unattended `while stop_reason == "tool_use"` loop calling
   the Anthropic API. This was a deliberate choice, not a workaround for a
   missing capability: this sandboxed session has no outbound
   `ANTHROPIC_API_KEY` of its own to spend (see REPRODUCE.md), and driving
   the episode manually produces genuine, verifiable trajectories against
   the real environment without needing one.
2. **Automated episodes** (file names like `baseline-auto-01.*`,
   `advanced-auto-01.*`, produced by `python -m eval.run_experiment`) - an
   unattended Anthropic-API tool-use loop
   ([agents/loop.py](../agents/loop.py)) drives the same real MCP tools
   against a fresh workspace with no human turn-by-turn involvement, using
   your own `ANTHROPIC_API_KEY`. This is the harness a judge (or you) reruns
   to extend the N=1 reference episodes into a real statistical sample -
   see REPRODUCE.md. None are committed yet in this snapshot because doing
   so requires an API key this session does not have; running
   `eval/run_experiment.py` populates these directories with real ones.
   A later pre-submission audit (CHANGELOG "Phase 7") re-confirmed no key
   is available and, rather than simulate one, ran a separate,
   model-free evaluation across all 15 tasks instead - see
   [results/task_verifier_sweep.md](../results/task_verifier_sweep.md).
   That sweep produces no trajectories (no agent runs), so this directory
   is unchanged by it.

Both kinds share one property that matters for grading: the **tool
implementations, the seeded bug, and the deterministic verifier are
identical** in both cases (`src/mcp_agent_benchmark/tools.py`, `seed/`, and
`verify.py` respectively) - only the thing deciding *which* tool to call
next differs (a human-driven Claude Code turn vs. an unattended API loop).
A reward number means the same thing regardless of which produced it.

**A note on package names in the transcripts below:** the three manual
episodes were recorded while the sandboxed application package was still
named `mcp_rl_env`; it was later renamed to `mcp_agent_benchmark` (a
cosmetic housekeeping change, not a behavioral one - see CHANGELOG's
rename entry) after these trajectories were committed. The `.md`/`.json`
files below are left exactly as recorded - editing an evidentiary
transcript after the fact to match a later rename would misrepresent what
the agent actually saw and did. Every current path, import, and command in
this README and elsewhere in the repo uses the current name;
`src/mcp_rl_env/...` appearing inside a trajectory transcript is expected
and correct for that historical record, not a leftover bug.

## Reading a trajectory

Open the `.md` file. Each step shows, in order: the tool called, the
arguments, whether it succeeded, how long the call took (where recorded -
see the note on `duration_s` in `results/trajectory_metrics.md`), the
**reasoning note** explaining what the previous tool result showed and why
this call follows from it, and the tool's response. Human-approval
checkpoints (advanced agent only) appear in their own section near the
end, followed by the final verdict from `verify.py`.

`python -m eval.trajectory_metrics trajectories/**/*.json` reduces any of
these files to structured tool-call/failure/retry counts instead of prose
- see [results/trajectory_metrics.md](../results/trajectory_metrics.md)
for the numbers already computed from these three.

Three real findings surfaced by these specific episodes (not staged) are
worth reading for directly:

- `manual-baseline-01.md` - the baseline protocol's fix is behaviorally
  correct but it stops as soon as the *pre-existing* test suite is green,
  missing the task's explicit requirement to add a regression test. See
  [results/results.md](../results/results.md) for the full comparison.
- `manual-advanced-01.md`, step `git_diff` and the finalize checkpoint -
  `git diff` only shows changes to files git already tracks, so it never
  surfaced the newly created regression test file. An agent (or reviewer)
  that trusts `git_diff` alone to summarize "what changed" will silently
  miss every new file. See [CHANGELOG.md](../CHANGELOG.md) and the hot
  take in [README.md](../README.md).
- `manual-recovery-01.md`, steps 1-3 - a real `read_file` call against a
  guessed path fails with a genuine `FileNotFoundError`; the next two
  steps recover by listing the real repository structure and retrying with
  the corrected path. This is a genuine failure and recovery, not staged -
  see CHANGELOG item 12 for why it was produced this way instead of being
  simulated.
