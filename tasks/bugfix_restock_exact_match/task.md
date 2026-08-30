# Task: Fix incorrect restock matching

You are working in the same small inventory repository used by the
`bugfix_inventory` task. `InventoryService` has a `restock(sku, qty)`
method meant to increase the stock of exactly one product.

## Bug report

Calling `restock("A1", 5)` also increases the stock of unrelated products
whose SKU merely contains "A1" as part of it (for example "A10"). SKU
matching for restocking must be exact, not the fuzzy substring matching
`search()` legitimately uses for text queries.

## Requirements

1. `restock(sku, qty)` must only affect the product whose SKU exactly
   equals `sku` (case-sensitive exact match).
2. `search()`'s existing substring-matching behavior must not change.
3. The full existing test suite must continue to pass.
4. Add a regression test proving that restocking one SKU does not affect
   a different product whose SKU contains it as a substring.
5. Do not change the public `Product` or `InventoryService.search` API.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Run the full test suite before declaring success - not just a new test
  you add.
