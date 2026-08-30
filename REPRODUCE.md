# Reproduction guide

Written for someone starting from a clean checkout with nothing installed.
Every command below was actually run during this submission's build
(except the `ANTHROPIC_API_KEY`-gated ones in Part 3, which need a key this
build session does not have - see [trajectories/README.md](trajectories/README.md)
for why the committed evidence in `trajectories/` and `results/` is real,
manually-driven episodes rather than automated ones).

## Versions used

- Python 3.12.3 (Windows; any CPython >= 3.10 should work - `mcp` requires 3.10+)
- `mcp` 1.29.1, `pytest` 8.4.2, `anthropic` >= 0.68, < 1 (pinned ranges in
  `requirements.txt`; `anthropic` is only exercised by Part 3, but is now
  installed alongside the rest by `pip install -r requirements.txt`)
- Model for the live agent harness: `claude-opus-5` (default in `agents/*.py`;
  the two committed reference trajectories were produced by `claude-sonnet-5`
  acting as a manually-driven agent - see trajectories/README.md)

## Part 1 - the environment itself (no API key needed)

```bash
git clone <this repo> && cd mcp-agent-benchmark
python -m venv .venv
source .venv/bin/activate   
pip install -r requirements.txt
pip install -e .      
pytest -q                     
```

Expected output: `134 passed in ~3 min`. These tests cover the original
inventory-service unit tests, `tests/test_harness.py` (episode
isolation, the seeded bug, the verifier's scoring in both directions
including its rejection of a vacuous regression test - see CHANGELOG item
10 - and trajectory recording, plus item 13's Windows workspace-reuse
regression test), `tests/test_tool_schema_parity.py` (connects to the real
MCP server and checks it against `agents/tool_schemas.py`),
`tests/test_tools_path_safety.py` (direct tests of the path-containment
property), `tests/test_fault_injection.py` / `test_loop_integration.py`
(the deterministic fault-injection wrapper and its end-to-end wiring
through the agent loop - see TASK_SUITE_DESIGN.md and CHANGELOG's Phase
3), and one `test_task_<id>.py` file per registered task beyond
`bugfix_inventory` - 4 from the original suite
(`test_task_bugfix_restock_exact_match.py`,
`test_task_decoy_context_efficiency.py`,
`test_task_generalization_contact_index.py`) plus 10 from the Phase 5
expansion (`test_task_ledger_transfer_rollback.py`,
`test_task_calendar_booking_overlap.py`,
`test_task_config_loader_backward_compat.py`,
`test_task_batch_partial_failure_recovery.py`,
`test_task_lru_cache_eviction_invariant.py`,
`test_task_template_render_decoy.py`,
`test_task_pricing_discount_rounding.py`,
`test_task_notes_tag_rename_generalization.py`,
`test_task_shipping_quote_root_cause.py`,
`test_task_dependency_resolver_cycle_detection.py`), each independently
checking that task's seed contents, seeded bug, unfixed-seed scoring,
fixed-plus-regression scoring, and vacuous-test rejection - none need
network access.

```bash
python -m eval.reward              
python -m eval.reward_replication   # the same finding, replicated on a different requirement/task
```

Expected output: a JSON report (also saved to
`experiments/reward_hacking/results.json` and `replication_results.json`
respectively) showing the weak evaluator crediting a vacuous test with
full reward while the strong evaluator denies it, with the genuine
regression test fully credited under both. Deterministic - no API key, no
randomness, same result every run.

```bash
VERIFY_TASK_ID=bugfix_restock_exact_match VERIFY_ROOT=<a workspace for that task> python verify.py
```

`verify.py` and `harness/workspace.py::make_episode_workspace` both take a
`task_id` (`VERIFY_TASK_ID` env var for the CLI; a keyword argument
everywhere else) - see `harness/task_registry.py` for the full list of
task IDs. Every command below defaults to `bugfix_inventory` unless a
`--task-id` is given.

```bash
python verify.py
```

Expected output: this repo's `src/` is the already-fixed reference state
(kept as-is from before this submission, see README's "what existed
before"), so this scores `REWARD=1.00`. With no `VERIFY_ROOT` set, this
runs against the repo root itself, not a small isolated task workspace -
its `tests_passed` step therefore runs the *entire* 134-test repo suite
(~3 minutes on the machine this was verified on), not just the handful of
tests a real episode workspace would have. This is expected and correct,
not a hang - `VERIFY_ROOT=<a small workspace>` (see the task-specific
invocation below) finishes in a couple of seconds because that workspace
only contains one task's own tests.

```bash
python apply_golden.py
```

Expected output: `Golden solution is already applied.` (it's a no-op
here, confirming `src/` matches the reference fix - useful mainly when
pointed at a fresh, unfixed checkout).

## Part 2 - run the two manually-driven reference episodes yourself

This regenerates exactly what's committed under `trajectories/baseline/`
and `trajectories/advanced/` and `results/`, using the real MCP server and
real deterministic verifier (no API key needed - you play the agent role,
or read the existing trajectories instead of re-running this).

```bash
# 1. Materialize a fresh, isolated, buggy episode workspace:
python -c "
from pathlib import Path
from harness.workspace import make_episode_workspace
print(make_episode_workspace(base_dir=Path('runs'), episode_id='my-episode'))
"

# 2. Make one real MCP tool call at a time (each prints the tool's response and appends a step to the trajectory file):
python -m harness.mcp_call runs/my-episode read_file path=tasks/bugfix_inventory/task.md \
  --episode my-episode --agent baseline --model "your-name-or-model-here" \
  --task "Fix duplicate search results" --note "why this call"
python -m harness.mcp_call runs/my-episode list_files --episode my-episode --note "..."
python -m harness.mcp_call runs/my-episode read_file path=src/mcp_agent_benchmark/inventory.py \
  --episode my-episode --note "..."
python -m harness.mcp_call runs/my-episode write_file path=src/mcp_agent_benchmark/inventory.py \
  "content=<your fixed source>" --episode my-episode --note "..."
python -m harness.mcp_call runs/my-episode run_tests --episode my-episode --note "..."

# 3. Score it:
python -m harness.mcp_call runs/my-episode --finish --episode my-episode
```

Expected: a `trajectories/<agent-dir>/my-episode.json` and `.md` appear
(default `--out-dir` is `trajectories/`; pass `--out-dir trajectories/baseline`
or `trajectories/advanced` to match the existing layout), and the final
`--finish` call prints a JSON report ending in `"reward": <0.0-1.0>`.
Runtime: each `mcp_call` invocation spins up a fresh MCP server subprocess,
~1-2s; a full episode (5-10 calls) takes well under a minute. The final
`--finish` call is slightly slower than a plain `verify.py` run because a
full reward of 1.0 requires the mutation check (a second, scratch-copy
pytest run against the known-buggy source - see CHANGELOG item 10), adding
roughly another second. No API cost - nothing here calls Claude or any LLM.

To reduce a trajectory to structured metrics instead of reading the
prose transcript:

```bash
python -m eval.trajectory_metrics trajectories/advanced/my-episode.json
```

## Part 3 - run the automated N-episode harness (needs `ANTHROPIC_API_KEY`)

`anthropic` is already installed from Part 1's `pip install -r requirements.txt`
(it now covers `agents`/`eval` too, not just the environment itself) - all
this part needs is the key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...          

# One episode of each policy:
python -m agents.baseline_agent --episode baseline-auto-01
python -m agents.advanced_agent --episode advanced-auto-01

# Or N of each, plus an aggregated comparison table:
python -m eval.run_experiment --n 5 --model claude-opus-5
cat results/results.md

# Against a different task in harness/task_registry.py (e.g. the C1 task):
python -m eval.run_experiment --n 5 --task-id bugfix_restock_exact_match

python -m eval.run_experiment --n 3 --task-id generalization_contact_index --run-id generalization-check
python -m eval.run_experiment --n 3 --task-id notes_tag_rename_generalization --run-id generalization-check-2

python -m eval.run_experiment --n 5 --task-id ledger_transfer_rollback
```

Expected: `results/results.json` and `results/results.md` are overwritten
with a real N-episode comparison (this replaces the current N=1 manual
reference numbers with a statistical sample). New trajectory files appear
under `trajectories/baseline/` and `trajectories/advanced/` named
`baseline-auto-NN` / `advanced-auto-NN`.

**Approximate cost and runtime** (not independently measured by this build
session, since it has no API key - estimated from typical `claude-opus-5`
pricing and this task's size): each episode is roughly 5-15 tool-call
turns over a ~200-line codebase and a ~200-word task statement, well under
10K input/output tokens total; at Opus 5 pricing ($5/$25 per MTok) that's
well under $0.05/episode, and `--n 5` (10 episodes total) should complete
in a few minutes and cost under $1. Treat this as an estimate to verify,
not a guarantee - report your actually observed numbers if they differ
meaningfully.

## Troubleshooting

- **A `run_tests`/`git_diff` MCP call hangs forever, then times out:** this
  was a real bug we hit and fixed (`CHANGELOG.md` item 3) - make sure
  you're running the code in this repo (not an older checkout), which
  passes `stdin=subprocess.DEVNULL` on every tool-spawned subprocess.
- **`list_files`/`search_code` returns only one entry:** same vintage
  issue, fixed in `harness/mcp_client.py` (`CHANGELOG.md` item 4) -
  `MCPToolSession.call` must collect every MCP content block, not just
  the first.
- **`pytest -q` from the repo root fails with "import file mismatch"
  after you've run some episodes:** make sure `runs/` is excluded from
  collection - `pyproject.toml`'s `norecursedirs` should already list it;
  if you renamed the runs directory via `base_dir=`, add that name too.
- **A regression test scores `regression_test_present: false` even though
  it looks reasonable:** the check is not a keyword match - it requires
  the test to actually fail when run against the benchmark's known-buggy
  `seed/inventory_buggy.py` (see CHANGELOG item 10). A test that would
  pass regardless of the bug (e.g. one that never calls
  `InventoryService.search()`, or asserts something true independent of
  deduplication) is correctly scored as not proving anything, even if it's
  named `test_multiple_fields` or similar.
