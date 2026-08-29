# Measured improvement: baseline vs. advanced

Task: [bugfix_inventory](../tasks/bugfix_inventory/task.md) - fix `InventoryService.search()` returning duplicate
products, and satisfy all 6 requirements in the task statement (including
adding a regression test).

These numbers come from manually-driven reference episodes (see
[trajectories/README.md](../trajectories/README.md) for exactly what
"manually-driven" means and why) - real tool calls against the real MCP
server and the real deterministic verifier, not a simulation. They are
evidence of a real, reproducible mechanism, not a statistical sample; run
`python -m eval.run_experiment --n 5` with `ANTHROPIC_API_KEY` set to
regenerate this table from N=5 autonomous LLM episodes per agent instead.
All rewards below are from the mutation-based regression check
(`verify.py`, CHANGELOG item 10) - see that entry if you're comparing
against an earlier snapshot of this repo, which used a gameable
keyword-based check instead.

| Metric | Baseline (manual-baseline-01) | Advanced (manual-advanced-01) |
|---|---|---|
| Reward (verify.py) | **0.85** | **1.00** |
| Tests pass (existing suite) | yes | yes |
| Behavior check (no duplicates) | pass | pass |
| Regression test added | **no** | **yes** |
| Tool calls | 5 | 9 |
| Human-approval checkpoint | none (protocol has no gate) | 1, explicitly approved before finishing |

A third episode, `manual-recovery-01` (also advanced protocol, reward
1.00, 10 tool calls), is not a separate comparison point - it uses the
same protocol as `manual-advanced-01` and exists to demonstrate genuine
tool-failure recovery instead (see
[trajectory_metrics.md](trajectory_metrics.md) and CHANGELOG item 12). It
is included in `results.json`'s advanced-agent summary (n=2) since it's a
real, independent advanced-policy episode, but the baseline/advanced
*comparison* below is about `manual-advanced-01` specifically, since that
one has no failed tool calls muddying the tool-call-count comparison.

## What actually produced the gap

Both agents diagnosed the same root cause and wrote the *same* correct
one-line-logic fix to `search()` - the fix itself was not the hard part of
this task. The gap came entirely from **what each protocol counted as
"done"**:

- The baseline protocol's only finishing condition was "run the tests
  before declaring success." The two pre-existing tests
  (`tests/test_inventory.py`) went green after the fix, and the agent
  stopped there - even though the task statement's requirement #5 ("add a
  regression test") was still unmet, because neither pre-existing test
  ever exercises a product matching more than one field.
- The advanced protocol required reading the existing tests *before*
  editing (to see what was and wasn't covered), and required an explicit
  pass back over every numbered requirement before finishing - which
  caught the missing regression test, added it, and re-ran the suite
  (2 -> 3 passing) before requesting the finalize checkpoint.

This is the failure mode named in [README.md](../README.md)'s hot take:
**a green test run is evidence the code didn't get worse, not evidence the
spec was satisfied** - the two are only the same thing if someone (or an
explicit checklist step) already made sure the test suite covers the
spec.
