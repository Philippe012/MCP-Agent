# Task: tag rename affects notes it shouldn't

A user renamed the tag "work" to "job" in their notes app, expecting only
notes tagged exactly "work" to change. Afterward, notes tagged "workshop"
and "homework" had also been silently renamed - "workshop" became "job"
and "homework" became "homejob". Those are different tags that happen to
share letters with "work"; they are not the same tag and should not have
been touched.

Fix `NoteStore.rename_tag` so it only affects notes whose tag list
contains the *exact* string being renamed. Searching for notes by tag
(`find_by_tag`) is a different operation and is supposed to keep matching
by substring, the way it already does today - don't change that behavior
while you're in there, and run the whole suite, not just a new test, to
make sure nothing else moved.

Add a test proving that a rename no longer touches a tag that merely
contains the renamed word as a substring. Don't change the shape of the
`Note` record.

Constraints: use only the tools exposed through MCP.
