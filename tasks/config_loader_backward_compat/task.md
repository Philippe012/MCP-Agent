# Task: old config files stopped working after the nested-format change

This config loader used to accept a flat shape (`{"timeout": 45}`). A
later change added support for a nested shape
(`{"network": {"timeout": 45}}`), and somewhere along the way the flat
shape stopped being read at all - old config files on disk still say
`{"timeout": 45}`, and they're now silently treated as if they said
nothing, falling back to the default instead of raising an error or
reading the real value.

## Requirements

1. A legacy flat config (e.g. `{"timeout": 45}`) must return `45` from
   `load_timeout`, not the default.
2. A legacy flat config (e.g. `{"retries": 5}`) must return `5` from
   `load_retries`, not the default.
3. The current nested format must continue to work exactly as it does
   today.
4. If a config has both the flat and nested keys, the nested (newer) value
   wins.
5. A config with neither key still returns the documented defaults (30 for
   timeout, 3 for retries).
6. Add a regression test proving a legacy flat-format config is read
   correctly by both functions.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Run the full test suite before declaring success.
