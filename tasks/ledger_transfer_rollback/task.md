# Task: a transfer to a bad account number is destroying money

You're working in a small ledger library. A support ticket: a customer
tried to transfer funds to a mistyped account number, got an error (which
is correct - the destination doesn't exist), but the money still left
their account and vanished. It should have stayed put.

## Requirements

1. `Ledger.transfer()` must still raise an error when the destination
   account doesn't exist.
2. When that error is raised, the source account's balance must be
   completely unchanged - the transfer either happens in full or not at
   all, never partially.
3. A successful transfer between two known accounts must keep working
   exactly as before.
4. `Ledger.total_balance()` (the sum of every account's balance) must be
   the same before and after any failed transfer attempt.
5. Add a regression test proving that a failed transfer to an unknown
   account leaves the source account's balance - and the ledger's total
   balance - unchanged.
6. Do not change the public `Account` API.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Run the full test suite before declaring success.
