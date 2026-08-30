# Task: Fix duplicate search results

You are working in a small inventory repository.

The `InventoryService.search()` method is reported to return the same
product more than once when the search query matches multiple tags or
both the product name and a tag.

## Requirements

1. A product must appear at most once in the result.
2. Preserve the existing case-insensitive substring behavior.
3. Preserve product ordering based on the original inventory order.
4. Empty queries must still return all products exactly once.
5. Add a regression test that proves a product matching more than one
   field is returned once.
6. Do not change the public `Product` API.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Keep the implementation maintainable.
- Run the tests before declaring success.
