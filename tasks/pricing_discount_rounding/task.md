# Task: discounted cart totals are occasionally a cent too high

Finance flagged that `Cart.total_with_discount_cents()` sometimes produces
a total that's a cent or two higher than a hand calculation, specifically
on baskets with several line items. Run the existing test suite first -
one of the tests already demonstrates the discrepancy with concrete
numbers and is currently failing.

## Requirements

1. Diagnose the actual root cause from the failing test's numbers - don't
   just tweak the formula until that one test happens to pass.
2. `total_with_discount_cents()` must apply the discount and round to the
   nearest cent exactly once, on the cart's subtotal - never once per line
   item.
3. `subtotal_cents()` and `line_totals_cents()` must be unchanged.
4. A 0% discount must return exactly `subtotal_cents()`.
5. Add a regression test - using a different multi-item basket and a
   different discount percentage than the one already in the test suite -
   that would fail under per-line rounding and passes under round-once.
6. Do not change the public `LineItem` or `Cart` constructor signatures.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Run the full test suite before declaring success.
