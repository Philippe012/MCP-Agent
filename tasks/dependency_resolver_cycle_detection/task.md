# Task: circular dependencies aren't caught

`resolve_order()` is supposed to raise `ValueError` when the dependency
graph has a cycle (e.g. A depends on B, and B depends on A - there is no
valid build order for that). Someone built a project with an accidental
circular dependency and got a build order back with no error at all - and
the order was wrong, with a module built before something it actually
needs.

## Requirements

1. Any circular dependency (a direct A->B->A, or a longer cycle like
   A->B->C->A) must raise `ValueError`.
2. Every existing acyclic case (a simple chain, a diamond dependency) must
   keep producing a valid order - every dependency appears before the item
   that needs it.
3. A node with no dependencies must still appear in the result.
4. Add a regression test proving a circular dependency raises
   `ValueError` instead of silently returning an order.
5. Run the full test suite before declaring success.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Do not change `resolve_order`'s signature.
