# ReliableMCP: does a coding agent's "done" actually match the spec?

A reproducible benchmark and two coding-agent policies (baseline and
advanced) that measure a real, common agent failure mode: **treating a
green test run as proof a task is finished, when the existing tests never
covered the new requirement in the first place.**

## Who this is for, and the bottleneck it addresses

The intended user is anyone evaluating or deploying a coding agent on
real engineering tickets - an engineering lead deciding whether an
agent's PR is trustworthy enough to merge, or a team building their own
agent harness who needs a cheap, deterministic way to catch this failure
mode before it ships. Their current bottleneck: a coding agent that
reports success and shows a green CI run *looks* done, but "the tests
pass" and "the spec is satisfied" are only the same statement when
something already made sure the tests actually cover the spec - and nothing
enforces that by default. Verifying this by hand means re-reading every
diff against the original ticket, which does not scale, and a single
end-to-end "did it work" grade collapses that whole judgment down to one
opaque pass/fail number. This project makes the failure visible,
reproducible, and measurable with a deterministic oracle that never trusts
the model's own opinion of its work, so an engineer can see exactly *why*
one agent policy is more trustworthy than another rather than taking it on
faith.

## What existed before this submission vs. what was added

**Before** (prior commits in this repo): a small MCP server
(`src/mcp_rl_env/server.py`) exposing six tools over an inventory-service
bugfix task, a single task statement (`tasks/bugfix_inventory/task.md`), a
golden reference patch, and a single-workspace `verify.py`. The bug the
task describes was already fixed in `src/mcp_rl_env/inventory.py` and the
regression test already existed - i.e. the repo held the *answer*, not a
runnable benchmark: there was no seeded buggy state for an agent to
actually fix, no isolation between episodes, and no baseline/advanced
comparison.

**Added in this submission** (everything else): the buggy seed state and
per-episode workspace isolation (`seed/`, `harness/workspace.py`); a
verifier and MCP-tool implementation shared by every consumer instead of
duplicated (`harness/verifier.py`, `src/mcp_rl_env/tools.py`), including a
mutation-based check that closes a real reward-hacking hole (see the hot
take below); a real MCP stdio client and trajectory recorder
(`harness/mcp_client.py`, `harness/trajectory.py`, `harness/mcp_call.py`)
that records each tool call's arguments, response, observable
success/failure, and wall-clock duration; the baseline and advanced agent
policies and an automated N-episode harness against the real Anthropic API
(`agents/`, `eval/`); three real, non-simulated reference episodes and
their full trajectories, including one genuine tool-failure-and-recovery
episode (`trajectories/`); the measured comparison and trajectory-level
metrics (`results/`); harness-level tests that don't need an API key
(`tests/test_harness.py`); and this documentation set
(`CHANGELOG.md`, `REPRODUCE.md`).

Coding-agent used throughout: **Claude Code** (`claude-sonnet-5`), used
both to build this repository and, for the two reference episodes, to
*play* the agent under test - see [trajectories/README.md](trajectories/README.md)
for exactly what that means and why.

## Architecture

```
task.md ──► agent (baseline or advanced policy)
                │
                ▼ real MCP tool calls, over real stdio transport
        list_files / read_file / search_code / write_file / run_tests / git_diff
                │
                ▼ operating on an isolated, single-use episode workspace
        (fresh copy of the seeded buggy repo; never the real repo on disk)
                │
                ▼ after the agent stops (or a human-approval checkpoint passes)
          verify.py  (deterministic oracle, never the model grading itself)
                │
                ▼
   reward = tests_passed × behavior_passed × regression_test_present
```

`regression_test_present` is not a text/keyword match on the test file -
it's checked by actually running the candidate test against the
benchmark's own known-buggy source in a scratch copy and requiring it to
fail there (`verify.py::_regression_test_proves_the_fix`). An earlier,
simpler version of this check was gameable; see the hot take.

Every tool call is recorded to a trajectory (`harness/trajectory.py`):
tool name, arguments, response, an explicit success/failure flag, this
call's own wall-clock duration, and a required human-authored note
explaining why the call was made. This is deliberately observable
behavior only - nothing about the model's hidden reasoning is recorded or
claimed.

## Task suite

`harness/task_registry.py` registers 15 tasks across 12 independent
domains (inventory, contacts, a ledger, a room-booking calendar, a config
loader, a batch processor, an LRU cache, a template renderer, a shopping
cart, a notes app, a shipping-rate calculator, and a dependency resolver) -
see [TASK_SUITE_DESIGN.md](TASK_SUITE_DESIGN.md) for the original 6-task
design review and [CHANGELOG.md](CHANGELOG.md)'s "Phase 5" entry for the
expansion to 15, including every candidate considered and rejected.

**14 of the 15 are agent-facing bugfix tasks**, each with its own
`golden/<task_id>/solution.patch` and `tests/test_task_<task_id>.py`
harness test, sharing the same non-negotiable properties: the agent's
workspace never contains `verify.py`, `golden/`, or another task's answer
material; the deterministic verifier always checks at least one
behavioral property the visible test suite could not have caught; and
every one ships a real, independently-verified golden fix. **The 15th,
`edge_case_coverage`, is deliberately not agent-facing** - its own
`task.md` says so explicitly - and exists solely as a second fixture for
`eval/reward_replication.py`, replicating the flagship reward-hacking
finding (below) on a different requirement and a different buggy seed
than `bugfix_inventory`'s, reusing the same registry and mutation-testing
machinery rather than a hand-rolled second copy of it. It is real,
reproducible infrastructure (`python -m eval.reward_replication`), not
filler added to inflate the task count to 15 - see TASK_SUITE_DESIGN.md's
"C5" for exactly why it exists and why it is scoped this way.

Two tasks are deliberately held out (`generalization_contact_index`,
`notes_tag_rename_generalization`): never referenced while iterating on
prompts or the other tasks, used only to measure whether a policy
transfers to an unseen domain or was tuned to the domains it was developed
against. They test two different transferred capabilities (multi-field
deduplication, and exact-vs-substring matching under an existing-test
self-correction trap) in two different unseen domains, rather than
repeating the same held-out check twice.

## Baseline vs. advanced

Both policies see the same task, the same tools, and the same seeded bug.
They differ only in *policy*:

| | Baseline | Advanced |
|---|---|---|
| System prompt | "use the tools, run tests before finishing" | explicit per-requirement checklist, read existing tests first, re-verify against every requirement before finishing |
| Stopping condition | existing test suite goes green | every checklist item independently confirmed |
| Tool-failure guidance | none | diagnose from tool output, retry with a corrected approach |
| Human-approval checkpoint | none | one, before the episode is allowed to finish |

Measured result (one real reference episode each - see
[results/results.md](results/results.md) for the full table and mechanism):

| | Baseline | Advanced |
|---|---|---|
| Reward | **0.85** | **1.00** |
| Regression test added | no | yes |

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate   
pip install -r requirements.txt
pytest -q                                            
python verify.py                                     
```

To run the live agents or regenerate the results table, see
[REPRODUCE.md](REPRODUCE.md) - it needs your own `ANTHROPIC_API_KEY`.

## Trajectory-level evidence, beyond the final reward

The final verifier score is authoritative for correctness, but it doesn't
show *how* an episode got there. `eval/trajectory_metrics.py` reads the
saved trajectories and reports tool-call counts, failures, retries, and
whether a failure was recovered from - see
[results/trajectory_metrics.md](results/trajectory_metrics.md). One
episode (`manual-recovery-01`) deliberately demonstrates a genuine tool
failure (a real `FileNotFoundError` from a guessed path) and a genuine
recovery (list the real structure, retry with the right path) - not staged,
just allowed to happen and then reported honestly either way.

## Improvement changelog

See [CHANGELOG.md](CHANGELOG.md) for every iteration, in order, each tied
to the evidence (a failing smoke test, a hung process, a wrong file list,
a leaked docstring, a gamed reward) that motivated the next decision.

## Main failure mode and hot take

See [RESEARCH.md](RESEARCH.md) for the formal, controlled version of the
finding below - research question, hypothesis, method, and results,
including why it is explicitly *not* a claim that any agent in this
project cheated.

**The main failure mode this project surfaces, at two levels:**

**1. The agent level:** an agent - or a human reviewer - that treats "the
test suite passes" as sufficient evidence a task is complete, when nothing
guarantees the test suite covers the new requirement being graded. The
baseline agent's fix was *correct*; it just stopped one step early because
its definition of "done" was too weak. This reproduced without being
engineered into the baseline prompt on purpose, using the same model as
the advanced agent.

**2. The evaluator level - the actual hot take:** the same failure mode
shows up one level up, in the thing grading the agent. This project's own
verifier initially scored a regression test as fully correct based on
whether its *text* contained the right keywords, not whether it *tested*
anything - and a completely vacuous test (`assert True`) scored full
reward under that check, confirmed by actually running it (see CHANGELOG
item 10). The fix - a mutation-style check that runs the candidate test
against a known-buggy implementation and requires it to fail there - is
the same idea as requirement #5 itself, applied to the grader instead of
the agent: **a check that can't be shown to fail on the thing it's
supposed to catch isn't a check.** Any automated grader that scores
"the right words appear" instead of "the right behavior is exercised" has
this hole by default, whether it's grading a coding agent's regression
test, a candidate's resume keywords, or a model's own eval harness - and
it will not announce itself, because a gamed check still returns green.

A secondary version of the same lesson: `git diff` only reports changes to
files git already tracks, so a newly created file - like the regression
test the advanced agent added - never appears in it. An agent or reviewer
that uses "let me check the diff" as its final sanity check will silently
miss every new file. Our advanced agent avoids this only because its
system prompt says so explicitly (see step `git_diff` and the finalize
checkpoint in
[trajectories/advanced/manual-advanced-01.md](trajectories/advanced/manual-advanced-01.md)).

A third, self-inflicted version of the same lesson surfaced during this
submission's own final audit, not in an agent: a commit that reformatted
`harness/task_registry.py`'s indentation for readability - genuinely
described as a "quality" pass, not written maliciously - silently turned
every task's behavioral check into an `IndentationError`, capping every
task's reward at 0.5 for anyone who ran the suite afterward, because the
commit was never re-run before being trusted. Running `pytest -q` caught
it immediately; reading the diff would not have, because the change
*looked* like a strict improvement. See CHANGELOG's "Phase 6" entry for
the full account, including two smaller, similarly unverified edits
(a corrupted fixture name, a hardcoded string that drifted from the file
it was supposed to mirror) found and fixed the same way.

Passing tests is not sufficient evidence of a reliable agent, a
clean-looking diff is not sufficient evidence of a complete change, a
keyword match is not sufficient evidence of a real regression test, and a
tidy-looking commit is not sufficient evidence it still runs - the common
thread is that a check which cannot fail is not a check.

## Limitations

- **N=1 per policy for the manual reference episodes.** `results/results.md`
  is a real, mechanism-level comparison, not a statistical sample - see
  REPRODUCE.md Part 3 to generate a real N-episode sample with your own
  `ANTHROPIC_API_KEY` via `eval/run_experiment.py`.
- **The automated harness (`agents/`, `eval/`) is untested end-to-end with
  a live model.** It's syntax-checked and its non-LLM parts (the MCP
  client, verifier, workspace isolation) are proven by the manual episodes
  that use the identical code paths, but the `while stop_reason ==
  "tool_use"` loop itself has not been run against a real API response in
  this build, because this sandbox has no `ANTHROPIC_API_KEY`.
- **One recovered failure is not a recovery-rate claim.** `manual-recovery-01`
  shows the advanced protocol *can* recover from a real tool error; it
  says nothing about how often it would, which needs the N-episode
  automated harness plus deliberately varied failure conditions to answer
  (see CHANGELOG's "considered and not built: fault injection").
- **Single task instance.** Both policies are compared on one bugfix task.
  See CHANGELOG's "considered and not built: task variants" for why
  generalization wasn't tested here.
- **The regression-test verifier has a second, unfixed exploit shape.**
  The mutation-testing fix (this project's own hot take, above) closes the
  *lexical-presence* gap (a test that asserts nothing) but not a
  *source-text-coupling* gap (a test that inspects the fix's source code
  for an incidental token instead of calling it) - found during this
  project's own final adversarial review, reproducible via
  `python -m eval.reward`'s `source_text_coupled_test` condition, and left
  open rather than patched with a same-shape blacklist. See RESEARCH.md's
  "A second, distinct exploit found in final review" section for the full
  writeup and why a principled fix wasn't built in this pass.

## What was deliberately not built, and why

Multi-agent orchestration, a configurable fault-injection layer, and a set
of task/environment variants were all considered and explicitly rejected
for this submission - each for a specific evidence-based reason, not
because they were out of scope in the abstract. See the "Considered and
not built" entries at the end of [CHANGELOG.md](CHANGELOG.md).
