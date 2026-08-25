# MCP Software-Engineering RL Environment (Mini Project)

A reproducible benchmark environment for evaluating an AI coding agent through Model Context Protocol (MCP).

The agent receives a task, discovers repository information through MCP tools, edits code, and runs deterministic verification. The benchmark records whether the agent used the tools correctly and whether the final repository satisfies the specification.

## Scenario

The repository contains a small inventory service. `InventoryService.search()` is intentionally buggy: when a product has multiple matching tags, it can appear more than once. The agent must diagnose the bug, implement a feature-safe fix, and add a regression test.

## Environment contract

The agent can use these MCP tools:

- `list_files()` - inspect repository structure
- `read_file(path)` - read repository files
- `search_code(query)` - search source code
- `write_file(path, content)` - modify/create files
- `run_tests()` - run deterministic tests
- `git_diff()` - inspect changes

The environment itself verifies the result with `verify.py`. The golden solution is stored separately in `golden/solution.patch`.

## Run

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt

python -m mcp_rl_env.server
```

In another terminal:

```bash
python verify.py
```

Run the reference solution:

```bash
python apply_golden.py
python verify.py
```

## Benchmark idea

An evaluation episode is:

1. Reset repository to the task seed.
2. Give the agent only the task statement.
3. Start the MCP server.
4. Agent discovers files using MCP.
5. Agent diagnoses and edits code.
6. Agent runs tests.
7. Deterministic verifier computes reward.

A simple reward can be:

`reward = 0.50 * tests + 0.20 * regression_test + 0.15 * tool_use + 0.15 * patch_quality`

The important point is that verification is deterministic; the model does not grade itself.
