# Task: Empty inventory must not crash search

You are working in the same small inventory repository used by the
`bugfix_inventory` task.

## Requirement

`InventoryService.search()` must return an empty list (never raise) when
the inventory has no products, for any query.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Add a regression test that proves `search()` on an empty inventory
  returns `[]` instead of raising.

Note: this task exists as a fixture for `eval/reward_replication.py`, a
deterministic evaluator experiment (see RESEARCH.md and
TASK_SUITE_DESIGN.md C5) - it is not currently run against a live agent.
