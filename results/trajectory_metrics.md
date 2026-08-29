# Trajectory-level metrics

Generated with `python -m eval.trajectory_metrics trajectories/**/*.json`.
These are read directly off the trajectory files (`harness/trajectory.py`
step records) - none of it is inferred about the model's internal
reasoning, only observable tool-call outcomes.

| Episode | Agent | Tool calls | Failed calls | Retries | Recovered | Checkpoints | Reward |
|---|---|---|---|---|---|---|---|
| manual-baseline-01 | baseline | 5 | 0 | 0 | n/a | 0 | 0.85 |
| manual-advanced-01 | advanced | 9 | 0 | 1 (re-running tests after adding the regression test, not a failure) | n/a | 1 | 1.00 |
| manual-recovery-01 | advanced | 10 | 1 | 3 | **yes** | 1 | 1.00 |

**Note on `total_tool_time_s`:** only `manual-recovery-01` has it populated
(10.03s across 10 calls). `duration_s` per-call timing was added to
`harness/trajectory.py` partway through this project (see CHANGELOG.md);
the two earlier episodes were recorded before that and have no per-call
timing data. Reporting it as unavailable for those two rather than
back-filling an estimate.

## What `manual-recovery-01` actually shows

This episode deliberately exercises the "robustness to tool failure"
research dimension with a genuine failure, not a staged one: step 1 is a
real `read_file` call against a guessed (wrong) path, which the real MCP
server genuinely rejects with `FileNotFoundError`. The agent then calls
`list_files` (step 2, marked `retry_of: 1`) to get the real repository
structure, and successfully retries `read_file` with the corrected path
(step 3). The episode still reaches full reward (1.00) with the correct
fix and a mutation-verified regression test - i.e., the recovery was
genuinely successful, not just attempted.

This is one recovered failure, not a statistical claim about recovery
rates - see [README.md](../README.md)'s Limitations section for why this
should not be read as "the advanced policy always recovers from tool
errors."
