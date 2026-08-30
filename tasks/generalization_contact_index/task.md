# Task: Duplicate entries in contact search

You are working in a small contact-directory library.

`Directory.find()` is reported to return the same contact more than once
when a search term matches both the contact's name and one of their
labels, or matches more than one of their labels.

## Requirements

1. A contact must appear at most once in the result.
2. Keep the existing case-insensitive substring matching behavior.
3. Preserve contact ordering based on the original directory order.
4. An empty query must still return every contact exactly once.
5. Add a regression test proving a contact matching more than one field
   is returned once.
6. Do not change the public `Contact` API.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Run the full test suite before declaring success.
