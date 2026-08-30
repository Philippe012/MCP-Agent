# Task: one bad record aborts an entire batch job

You're working in a small batch-processing library. When one item in a
batch makes the worker function raise (a malformed record, a validation
error - whatever the caller's `worker` does), the whole batch stops
immediately and every result already computed for the items before the
failure is lost, along with every item after it never getting a chance to
run.

## Requirements

1. If one item's `worker` call raises, `process_batch` must continue
   processing the remaining items instead of stopping.
2. Every item that succeeds must appear in `BatchResult.succeeded`, in
   original order, regardless of whether an earlier or later item failed.
3. Every item that raises must appear in `BatchResult.failed` as a
   `(item, error_message)` tuple.
4. A batch where every item succeeds must behave exactly as it does today.
5. Add a regression test proving that a batch with a failing item in the
   middle still processes the items that come after it, and keeps the
   results from the items before it.
6. Do not change the public `BatchResult` API.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Run the full test suite before declaring success.
