# Task: placeholders with spaces aren't being substituted

You're working in a small template-rendering library used to build email
bodies. `render("Hello {{ name }}!", {"name": "Mugisha"})` is supposed to
produce `"Hello Mugisha!"`, but it's currently returning
`"Hello {{ name }}!"` unchanged - the placeholder isn't being substituted
whenever there's a space next to the key name inside the braces.

## Requirements

1. `render()` must substitute a `{{ key }}` placeholder whether or not
   there's whitespace around the key name.
2. The unspaced form `{{key}}` must keep working exactly as it does today.
3. A placeholder naming a key that isn't in the context must still be left
   untouched in the output (unchanged behavior).
4. Confirm which module the application actually imports and uses before
   changing anything - not every file in this repository is live code.
5. Add a regression test proving a placeholder with surrounding whitespace
   is correctly substituted.
6. Run the full test suite before declaring success.

## Constraints

- Use only the repository and the tools exposed through MCP.
