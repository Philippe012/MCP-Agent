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
git clone <this repo> && cd mcp_rl_env_seed_export
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt      # installs mcp, pytest, anthropic; ~15s
pip install -e .                     # makes agents/, harness/, eval/, mcp_rl_env importable
                                      # from any cwd, e.g. `python agents/baseline_agent.py`
                                      # directly - see CHANGELOG's Phase 1 entry
pytest -q                            # 12 passed, ~10s
```

Expected output: `12 passed in ~10s`. These tests cover the original
inventory-service unit tests, `tests/test_harness.py` (episode
isolation, the seeded bug, the verifier's scoring in both directions
including its rejection of a vacuous regression test - see CHANGELOG item
10 - and trajectory recording), and `tests/test_tool_schema_parity.py`
(connects to the real MCP server and checks it against
`agents/tool_schemas.py` - see CHANGELOG's Phase 1 entry) - none need
network access.

```bash
python verify.py
```

Expected output: this repo's `src/` is the already-fixed reference state
(kept as-is from before this submission, see README's "what existed
before"), so this scores `REWARD=1.00`.

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

# 2. Make one real MCP tool call at a time (each prints the tool's response
#    and appends a step to the trajectory file):
python -m harness.mcp_call runs/my-episode read_file path=tasks/bugfix_inventory/task.md \
  --episode my-episode --agent baseline --model "your-name-or-model-here" \
  --task "Fix duplicate search results" --note "why this call"
python -m harness.mcp_call runs/my-episode list_files --episode my-episode --note "..."
python -m harness.mcp_call runs/my-episode read_file path=src/mcp_rl_env/inventory.py \
  --episode my-episode --note "..."
python -m harness.mcp_call runs/my-episode write_file path=src/mcp_rl_env/inventory.py \
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
export ANTHROPIC_API_KEY=sk-ant-...          # Windows PowerShell: $env:ANTHROPIC_API_KEY = "sk-ant-..."

# One episode of each policy:
python -m agents.baseline_agent --episode baseline-auto-01
python -m agents.advanced_agent --episode advanced-auto-01

# Or N of each, plus an aggregated comparison table:
python -m eval.run_experiment --n 5 --model claude-opus-5
cat results/results.md
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
