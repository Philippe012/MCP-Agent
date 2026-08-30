# Task: reading a cached value doesn't protect it from eviction

You're working in a small LRU (least-recently-used) cache. It's supposed
to evict whichever key hasn't been touched - by either a read or a write -
for the longest time. Right now, reading a key with `get()` doesn't count
as "touching" it, so a key you just read a moment ago can still be evicted
as if you'd never looked at it.

## Requirements

1. `capacity` must never be exceeded.
2. Calling `get()` on a key must mark it as most-recently-used, exactly
   the way `put()` already does.
3. When the cache is full and a new key is inserted, the key that was
   least-recently touched (by either `get` or `put`) must be the one
   evicted.
4. The existing write-order eviction behavior (evicting whichever key
   hasn't been *written* recently, when nothing has been read) must be
   unchanged.
5. Add a regression test proving that reading a key with `get()` protects
   it from being the next eviction victim.
6. Do not change the public method signatures (`get`, `put`,
   `keys_by_recency`).

## Constraints

- Use only the repository and the tools exposed through MCP.
- Run the full test suite before declaring success.
