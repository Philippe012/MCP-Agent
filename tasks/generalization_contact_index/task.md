# Task: a support ticket about the contacts app

A user filed this ticket against the small contacts library in this
repository:

> "When I search for someone and their name AND one of their tags match
> what I typed, I see them twice in the results. Same thing if two of
> their tags both match - they show up once per match instead of once,
> total. Please fix so each person shows up a single time no matter how
> many things about them matched my search."

Look at how contacts are looked up today, confirm the bug for yourself,
and fix it properly - not just for the exact case in the ticket, but for
the underlying cause.

While you're in there, the rest of the lookup behavior should stay exactly
as it is: substring matching is intentional (a partial name or partial tag
should still match), results should come back in the same order the
contacts were originally given in, and an empty search is supposed to hand
back the whole list, once each. None of that should change - only the
duplication.

Before you consider this done:

- Prove it. Whatever test suite already exists here doesn't cover this
  scenario (that's why the bug shipped), so add a test that would have
  failed on the old behavior and passes now.
- Don't touch the shape of the public `Contact` record - other code
  outside this repository is assumed to depend on its current fields.
- Run everything, not just the new test, before you call it finished.

Only the tools exposed through MCP are available to you here.
