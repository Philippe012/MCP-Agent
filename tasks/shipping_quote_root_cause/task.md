# Task: shipping quotes are too low for odd weights

Customer support reports that a 1.5kg "standard" package is being quoted
as if it weighs exactly 1kg. `quote_cents()` in this repository computes
the quote - look at everything it depends on, not only the function whose
name matches the symptom, and confirm exactly where the miscalculation
happens before changing anything.

## Requirements

1. Any package that weighs more than a whole number of kilograms must be
   billed for the next full kilogram up (couriers don't do partial-kg
   billing).
2. A package that weighs an exact multiple of 1000g must be unaffected.
3. `quote_cents()`'s existing behavior for unknown services (raises
   `ValueError`) must be unchanged.
4. Add a regression test proving a non-exact weight (e.g. 1500g) is billed
   at the next full kilogram, not truncated down.
5. Run the full test suite before declaring success.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Do not change either module's public function signatures.
