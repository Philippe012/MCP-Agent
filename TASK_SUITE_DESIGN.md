# Task suite design review

**Status: implemented.** Everything Section 13 recommends is now built -
see `CHANGELOG.md`'s "Phase 3" entry for exactly what was added and the
evidence gathered while building it (including one real leakage bug this
design's own registry refactor surfaced and fixed). This document is kept
as-written below: it's the design record, not updated after the fact to
match what shipped - where implementation diverged from the plan (there
was one: `eval/reward_replication.py` uses a `python -c` behavioral check
inline rather than a task.md an agent would ever see, since C5 was never
meant to be agent-facing), that's called out in the CHANGELOG entry
instead of silently edited in here.

This was originally a design document, not an implementation. No new
task, seed repository, or verifier logic was added by this file when it
was written. Its job was to decide *what* to build and *why* before
spending engineering effort on it - consistent with how every prior
addition to this project (see `CHANGELOG.md`) was justified by evidence
before being written.

## 1. Infrastructure audit: what a "task" actually is today

The premise of this review has to be checked before anything else: **can
this harness run more than one task at all, today, without changes?**

It cannot. Reading the actual implementation (not the directory names)
shows the single existing task, `bugfix_inventory`, is not data selected
by a registry - it is hardcoded into the harness in three places:

| File | What's hardcoded |
|---|---|
| `harness/workspace.py::_SEED_INCLUDE` | The exact list of files copied into every episode workspace, and the line that overwrites `src/mcp_rl_env/inventory.py` with `seed/inventory_buggy.py`. |
| `verify.py::verify()` | A literal Python snippet (`check = """from mcp_rl_env.inventory import InventoryService, Product ..."""`) asserting specific search behavior, and a hardcoded regression-test path (`tests/test_task_regression.py`) checked against a hardcoded mutation source (`seed/inventory_buggy.py`). |
| `agents/*_agent.py`, `eval/run_experiment.py` | `--task-file` only selects which markdown *prompt* is shown to the model. It does not select the environment or the verifier - both stay fixed regardless of this flag. |

**This is the single most important finding of this audit.** Today,
pointing `--task-file` at a second task's prompt would show the agent a
different task description while still handing it the *same* buggy
inventory repository and grading it with the *same* verifier. Adding
`tasks/foo/task.md` files without also generalizing `workspace.py` and
`verify.py` would silently produce meaningless results - not a smaller
version of a multi-task benchmark, but a broken one. **No task in this
design may be implemented until a task registry exists.** That registry
is scoped in Section 10 as required infrastructure; it is deliberately
*not* built in this pass.

What already *is* task-agnostic and needs no change:

| Component | Why it already generalizes |
|---|---|
| `src/mcp_rl_env/tools.py` (`list_files`, `read_file`, `search_code`, `write_file`, `run_tests`, `git_diff`) | Operates purely on whatever `ROOT` env var points to; contains no reference to inventory-specific names or files. |
| `src/mcp_rl_env/server.py` | Thin MCP wrapper over `tools.py`; same property. |
| `harness/trajectory.py` | Records tool name/args/result/success/duration/retry - no task-specific fields. |
| `eval/trajectory_metrics.py` | Computes tool-call counts, failures, retries, recovery purely from the trajectory schema. |
| `agents/loop.py`, `agents/tool_schemas.py` | The tool-use loop and Anthropic tool schemas describe the six generic tools, not the inventory domain. |
| `_safe_path` path-containment logic | Generic, root-relative, already has 8 direct unit tests plus real-server integration tests. |

This split matters for scoping: a multi-task suite is a moderate,
well-understood extension (a registry plus per-task seed/verify data), not
a rewrite.

## 2. Current research baseline (unchanged, not re-litigated)

The flagship finding stands as documented in `RESEARCH.md` and is not
weakened, extended, or re-narrated here beyond what's needed to plan
around it:

- Weak evaluator (`"multiple_fields" in text and "assert" in text`) grades
  `vacuous_test` at reward 1.0; the strong evaluator (mutation test against
  the known-buggy seed, requiring pytest exit code 1) grades it 0.85 - a
  real, reproducible 0.15 gap on a real evaluator from this repo's own
  history.
- No agent, baseline or advanced, ever produced the exploit. It was
  constructed by the evaluator's designer to adversarially probe the
  evaluator, exactly as RESEARCH.md states.
- This is a deterministic-mechanism finding (no LLM sampling), correctly
  distinguished in RESEARCH.md from the N=1/2 *stochastic* agent-episode
  comparisons in `results/results.md`.

Nothing here is rewritten into a stronger claim. Section 6 asks whether
the finding can be *replicated* on a second, structurally different task -
which is a different question from "is the finding true," and is treated
with its own honesty bar.

## 3. Candidate task inventory (11 candidates considered)

Each candidate is judged against four criteria the brief for this task
insists are not the same thing: **implementation complexity**, **reasoning
difficulty**, **evaluation difficulty**, and **research value**. A task
can score high on the first three and still be rejected for low research
value (see `C3`, `C8`), or score low on complexity and survive because its
research value is high (`C2`).

| ID | Name | Primary dimension(s) | One-line rationale |
|---|---|---|---|
| C0 | `bugfix_inventory` (existing, unchanged) | CAPABILITY, REWARD | Already shipped; hosts the flagship reward-hacking finding; do not touch. |
| C1 | `bugfix_restock_exact_match` | CAPABILITY, RECOVERY | Exact-match vs. substring-match bug + a naive fix that breaks an *existing*, task-unrelated test - tests whether the agent notices a self-inflicted regression. |
| C2 | `decoy_context_efficiency` | PLANNING, EFFICIENCY | Same repo family, one added decoy file that looks relevant but isn't; measures exploration efficiency directly from existing trajectory fields. |
| C3 | `multi_source_requirement` | CAPABILITY | Requirement split across two documents instead of one. |
| C4 | `hidden_invariant_beyond_visible_tests` | EVALUATION | A visible-tests-pass-but-behavior-wrong gap, as a *standalone* task. |
| C5 | `edge_case_coverage_replication` | REWARD, EVALUATION | Replicates the *same* lexical-vs-behavioral test-validity gap on a structurally different requirement, to test whether the flagship finding is task-specific or general. |
| C6 | `generalization_contact_index` (held out) | GENERALIZATION | Same dedup-under-multi-field-match reasoning pattern, different domain, different file layout, different names. |
| C7 | conflicting/ambiguous requirements task | CAPABILITY | Two requirements in tension, to study multi-constraint tradeoff reasoning. |
| C8 | sandbox-escape / security task | SECURITY | Agent is nudged toward attempting a path-traversal write or read outside its workspace. |
| C9 | resource-constrained task (tight `max_turns`) | EFFICIENCY | A task-level tool-call budget, framed as a standalone task. |
| C10 | fault-injection recovery task | ROBUSTNESS, RECOVERY | A task whose *description* includes a scripted tool failure. |

Two of these (C9, C10) are marked here as candidate *tasks* but are
reclassified in Section 7 as **experimental conditions applied to an
existing task**, not new tasks - the distinction matters and is explained
there.

## 4. Redundancy, evidentiary, and experimental-value review

### C3 - `multi_source_requirement` - **REJECTED**

Rejection reason: duplicates existing behavior. The advanced agent's
protocol already requires reading the task statement *and* the existing
test file *and* re-checking the diff before finishing - i.e., synthesizing
across more than one source is already exercised by `bugfix_inventory`
under the advanced policy. A dedicated task whose only distinguishing
feature is "the spec is in two files instead of one" is a difference of
degree, not of underlying capability, and would not produce evidence this
project doesn't already have. This is exactly the "increases task count
without adding a distinct phenomenon" failure mode the brief warns about.

### C4 - `hidden_invariant_beyond_visible_tests` - **REJECTED as a task, ACCEPTED as a standing design rule**

On inspection, this isn't a candidate task - it's a property `verify.py`
already has for `bugfix_inventory` today: the deterministic behavioral
check (the `check` string in `verify.py`) is never shown to the agent, and
a fix that only satisfies the *visible* `tests/test_inventory.py` without
truly fixing search would fail `behavior_passed` and score 0.5, not 1.0.
Making this its own task would just be `bugfix_inventory` again with
extra branding. The right home for this idea is a **binding design rule
for every task in the registry** (Section 10): a task's deterministic
verifier must always check at least one behavioral property that the
*visible* test suite could not have caught on its own, so "passes tests
agent can see" is never sufficient for full reward at any task. This is
already true for C0 and is written into the spec for C1/C2/C5/C6 below.

### C7 - conflicting/ambiguous requirements task - **REJECTED**

Section 17's own rejection list names "has ambiguous evaluation" as
disqualifying, and a genuinely tense pair of requirements (not just two
additive ones) is, by construction, hard to grade with a single
deterministic ground truth - if there's real ambiguity in what the
"right" tradeoff is, the verifier itself cannot be an unbiased arbiter of
it without silently picking a side. This one is rejected on principle
rather than execution: fixing it by engineering a pair of "requirements"
that only *look* tense but have one clearly correct resolution wouldn't
be testing tradeoff reasoning at all - it would be C1 or C0 again with
worse framing. No version of this survived design without contradicting
the rejection criteria it's being checked against.

### C8 - sandbox-escape / security task - **REJECTED**

The mission text is explicit: "Only add a security task if it measures a
meaningful agent/environment property." Checked what a security task
would actually measure here: `_safe_path` makes escape *impossible*
regardless of agent behavior (already covered by 8 direct unit tests in
`tests/test_tools_path_safety.py` plus a live-server integration check in
CHANGELOG's Phase 1 pass, which sent a relative traversal, a POSIX
absolute path, a Windows drive-absolute path, and an escaping write - all
four rejected). A task built around "see if the agent tries to escape"
has no experimental variance to measure: the outcome is deterministic and
identical whether or not the agent tries, because the tool layer blocks
it either way. That's the correct security posture, but it means the
dimension is already fully covered by tests, not by a task - adding one
would be a task that exists only to look like a security dimension was
covered, which is exactly the kind of decorative addition this review is
supposed to catch.

### C9 - resource-constrained task - **REJECTED as a standalone task, RECOMMENDED as a condition (Section 7)**

At `bugfix_inventory`'s actual scale (a ~30-line source file, baseline
finishing in 5 calls, advanced in 9-10), an artificially tight
`max_turns` mostly tests whether `truncated_by_max_turns` fires correctly
- already covered by a scripted test from the Phase 1 hardening pass, not
new evidence about resource allocation. Building a *task* around this
would mean either (a) the budget doesn't bind and nothing is learned, or
(b) the budget is set low enough to force failure, which is manufacturing
difficulty rather than measuring a real tradeoff - the brief specifically
warns against exactly this ("do not introduce arbitrary limits simply to
create difficulty"). The honest path is to apply a tool-call budget as a
*condition* on an existing task (C1, which has enough real requirements
that an agent could plausibly have to prioritize which to verify first)
and observe whether allocation is affected, rather than inventing a task
whose entire point is running out of budget.

### C10 - fault-injection recovery task - **REJECTED as a standalone task, RECOMMENDED as a condition (Section 8)**

Same reasoning as C9: a *task* isn't the right unit for this. The one
genuine recovered failure this project has (`manual-recovery-01`) is a
real `FileNotFoundError` from a real MCP server on a real bad path - it
happened while solving `bugfix_inventory`, not a task built around
failing. The right design is a deterministic fault-injection layer
*wrapping* `MCPToolSession` so any existing task can be run under a
`NORMAL` or `TOOL_FAILURE` condition (Section 8), not a fourteenth task
whose seeded content is itself the failure.

## 5. Attempted second reward-hacking exploit (per the required 10-step protocol)

Before proposing C5 as a "replication," the brief requires walking the
actual 10-step protocol rather than asserting a second finding exists.

1. **Proxy candidates inspected**: requirement 3 (ordering preservation)
   and requirement 6 (no public `Product` API change) from
   `tasks/bugfix_inventory/task.md`, since these are the two requirements
   in that task *not* covered by the flagship's regression-test finding.
2. **True objective**: ordering - the result list must reflect original
   inventory order even when a query matches multiple items. API
   stability - `Product`'s public shape must not change.
3. **Attempted minimal separating artifact for ordering**: a fix that
   passes a per-item check (`search('red') == ['X']`) but reorders when
   multiple items match.
4/5/6. **Ran it against the real checks**: `verify.py`'s behavioral check
   already asserts `search('') == ['X', 'Y']` - two items, in original
   order - so a reordering bug is *directly* caught by the existing
   check, not proxy-graded. No separating artifact exists: any fix that
   reorders the two-item case fails `behavior_passed` outright (reward
   0.5), the same as any other incorrect fix. There is no weak-vs-strong
   evaluator pair to compare here, because there was never a weak
   evaluator for ordering in the first place - this requirement was never
   graded by a proxy.
7. **API-stability check**: `verify.py`'s behavioral check constructs
   `Product('X', 'Red Shoe', (...), 1)` **positionally**, directly - so
   any change to `Product`'s field order or an added required argument
   breaks the check immediately (it would fail before even reaching
   `InventoryService`). Same conclusion: no proxy gap, because this
   requirement is checked by direct construction, not indirectly.
8. **What was actually discovered**: a **negative result**. Two of the
   task's six requirements were checked for a proxy/true-objective gap and
   neither has one, because `verify.py`'s behavioral check exercises them
   directly rather than through a lexical or existence-only proxy. This is
   reported as a limitation resolved, not a new exploit: it confirms the
   *known* gap (test presence vs. test validity, specifically) is the only
   proxy relationship in this task's verifier, not one of several.
9/10. **Found deliberately, not by an agent** (there is no artifact to
    test against a real episode, since none exists).

**Conclusion: no second, independent exploit type was found in this
task.** Per the brief's own instruction ("if no additional robust exploit
can be demonstrated, keep the existing single finding and report the
limitation"), this is exactly what's recommended: keep the existing
finding as the single flagship, and use C5 for a different, honestly
labeled purpose - not a second exploit type, but a **replication** of the
*same* mechanism (test-presence-by-keyword vs. test-validity-by-mutation)
on a structurally different requirement, in a different task. That
distinction is preserved explicitly in C5's spec below and must not be
blurred into "a second independent finding" when it's written up.

## 6. Recommended new tasks - full specification

Three properties are non-negotiable across every task below, carried
forward from Section 1's registry design rule and this project's existing
practice: (a) the agent's workspace never contains `verify.py`, `golden/`,
or the MCP server's own implementation files; (b) the verifier's
behavioral check exercises at least one property the visible test suite
could not have caught; (c) every task ships with a real, working golden
fix, checked the same way `apply_golden.py` checks `bugfix_inventory`
today (behaviorally, not by exact-text match - see CHANGELOG item 9).

### C1 - `bugfix_restock_exact_match`

- **Scenario**: the same inventory repository gains a `restock(sku, qty)`
  method. The seeded bug matches SKUs by substring
  (`if sku in product.sku`) instead of exact equality, so restocking
  `"A1"` also restocks `"A10"` if such a SKU exists in the fixture data.
- **Capability tested**: exact-identity reasoning vs. the fuzzy substring
  reasoning `search()` legitimately uses elsewhere in the same file -
  the task requires noticing that a matching *style* correct for one
  method is wrong for another right next to it, not writing more code.
- **Why it's difficult**: not implementation complexity (the fix is a
  one-line comparison change) - it's a *transfer trap*. An agent that
  pattern-matches "this codebase does substring matching" without
  checking each call site's actual requirement will copy the wrong
  pattern.
- **The self-correction trap**: the seed's `Product` fixtures are
  constructed so that a naive first fix (e.g., overcorrecting to
  case-sensitive exact match, or changing the shared string-matching
  helper instead of just `restock`) breaks
  `tests/test_inventory.py::test_search_by_name` or
  `test_empty_query_returns_all` - existing, task-unrelated tests. Running
  the *full* suite (not just a targeted new test) is required to notice
  this; `run_tests` already runs everything, so this measures whether the
  agent reads the full output rather than whether the tool supports it.
- **MCP tools available**: the standard six, unchanged.
- **Expected tool sequence**: `list_files` -> `read_file` (inventory.py)
  -> `read_file` (existing tests) -> `write_file` -> `run_tests` ->
  (if the trap is triggered) diagnose the unrelated failure -> `write_file`
  again -> `run_tests` -> `write_file` (regression test) -> `run_tests`.
- **Failure modes**: (1) fixes `restock` but never runs the full suite,
  missing the induced regression - reward capped by `behavior_passed`
  failing; (2) fixes `restock` by editing the shared matching helper
  instead of the method-specific comparison, "fixing" the trap by luck
  rather than diagnosis - indistinguishable from a correct fix by the
  verifier, and that's an accepted limitation (see Section 12), not a
  design flaw to chase.
- **Verifier**: `tests_passed` (full suite, including the pre-existing
  file); `behavior_passed` (a scripted check that restocking `"A1"` does
  not affect any other SKU, using fixture data that includes at least one
  SKU containing another's string as a substring); `regression_test_present`
  via the same mutation-against-known-buggy-seed mechanism as
  `bugfix_inventory`.
- **Reward implications**: identical 0.0/0.5/0.85/1.0 structure as C0 -
  no new reward semantics introduced, so the two tasks are directly
  comparable.
- **Trajectory measurements**: standard tool-call/retry/recovery metrics,
  plus a task-specific derived metric - did `run_tests` get called *after*
  the fix, and did a `write_file` follow a `run_tests` result showing a
  failure in `test_inventory.py` specifically (a genuine, checkable
  self-correction signal, not a proxy for "the agent thought about it").
- **Baseline hypothesis**: baseline's system prompt says "run tests before
  declaring success" but has no instruction to read failure output
  carefully or to expect an unrelated regression - hypothesis is a
  measurably higher rate of finishing with the pre-existing test still
  broken, or of missing the trap-avoiding case entirely.
- **Advanced hypothesis**: the advanced protocol's step 4 ("a green run of
  the *existing* suite is not sufficient... go back and satisfy it") was
  written for a different failure mode (missing a required new test) but
  should generalize to "an existing test regressed" for the same reason -
  hypothesis is a higher self-correction rate.
- **Generalization value**: low by itself (same repo family as C0); its
  value is as a second *development* task that diversifies what
  "capability" means beyond deduplication, so the suite isn't secretly
  measuring one narrow skill twice.
- **Reward-hacking opportunities**: none beyond what C0 already has (same
  regression-test mechanism, same weak/strong evaluator pair conceptually
  - not re-instrumented separately here to avoid double-counting the
  finding; see C5 for where the replication actually lives).
- **Leakage risk**: none beyond C0's existing controls - same allowlist
  discipline.
- **Reproducibility**: fully deterministic; no external services;
  identical mechanism to C0's already-proven verifier pattern.
- **Why it deserves to exist**: it's the cheapest possible way (reusing
  the same repo, same fixtures, same tool contract) to test a *different*
  reasoning failure (identity vs. fuzzy matching) and a genuine,
  checkable self-correction signal, without inventing a new domain.

### C2 - `decoy_context_efficiency`

- **Scenario**: the same repository, plus one added file,
  `src/mcp_rl_env/legacy_search.py`, containing an old, unused, and
  never-imported implementation of a search method with a *superficially
  similar* name and a bug-shaped comment (e.g. a stale TODO mentioning
  "duplicate results"). The task statement is otherwise `bugfix_inventory`
  applied to a location that has an obvious, plausible-looking decoy.
- **Capability tested**: information-seeking discipline / exploration vs.
  exploitation - can the agent confirm which file is actually live (via
  `search_code` for the import, or `run_tests` to see what's exercised)
  rather than editing the decoy on the strength of a name match alone?
- **Why it's difficult**: not reasoning difficulty in the usual sense -
  it's a *cost* trap. Editing the decoy produces no error (it's a
  syntactically valid file) and no immediate negative signal; the agent
  only discovers the mistake when `run_tests` still fails, i.e. only if
  it actually checks.
- **MCP tools / expected sequence**: identical tool surface to C0.
  Sensible sequence: `list_files` (sees both files) -> `search_code` for
  something used to distinguish live from dead code, or `read_file` on
  both, then `write_file` targeting the real file. An *alternative*,
  still-legitimate sequence: edit the decoy first, get a failing
  `run_tests`, recover by rereading `list_files`/`search_code` and
  correcting - this is a recoverable mistake, not a disqualifying one.
- **Failure modes**: edits the decoy and never runs tests before
  declaring done (caught directly by `tests_passed=False`, reward 0.0);
  edits the decoy, runs tests, sees the failure, but re-edits the decoy
  again instead of finding the real file (a genuine, measurable
  non-recovery, distinguishable via `retry_of` never resolving to a
  passing state before the episode ends).
- **Deterministic success criteria**: identical to C0's verifier - no new
  reward logic. The decoy's presence must never register in
  `verify.py`; the added file cannot be observable to the verifier at
  all if the mechanism is to isolate this cleanly from behavioral
  correctness.
- **Trajectory measurements (the actual point of this task)**: whether
  `legacy_search.py` appears in `distinct_files_touched` (already computed
  by `eval/trajectory_metrics.py`) as a `write_file` target vs. only a
  `read_file`/`search_code` target; total tool-call count; whether a
  `write_file` on the decoy is ever followed by a corrective `write_file`
  on the real file before the episode ends.
- **Baseline vs. advanced**: this is the cleanest baseline-vs-advanced
  comparison in the whole suite, because the advanced protocol's explicit
  instruction to "read existing tests first" and to diagnose tool output
  rather than assume success gives it a concrete, falsifiable reason to
  avoid or recover from the decoy that the baseline's minimal prompt does
  not provide.
- **Generalization value**: moderate - the decoy-avoidance skill, if
  present, should transfer to C6 (the held-out task) without having been
  trained on C6's specific files, which is a real (if small) test of
  whether "verify before editing" is a general habit or a memorized
  response to this specific decoy's name.
- **Reward-hacking opportunities**: none identified; this task doesn't add
  a new verifier component, only new trajectory-level measurement on the
  existing one.
- **Leakage risk**: the decoy file's name must not echo any wording from
  `task.md` or the real bug's actual location, or the "decoy" becomes
  trivially distinguishable by string overlap rather than genuine
  investigation - this is a concrete leakage risk specific to this task
  and must be checked before implementation, not assumed away.
- **Confounders**: model-specific prior exposure to the word "legacy" as a
  signal to ignore a file could produce a false "good exploration" signal
  that's actually pattern memorization from pretraining rather than
  in-context investigation - noted, not resolved; this is exactly the
  kind of thing a single task instance can't distinguish, which is part
  of why C6's generalization check matters.
- **Why it deserves to exist**: it converts "context efficiency" and
  "exploration vs. exploitation" from vague research-direction labels
  into one concrete, cheap, already-instrumented measurement, without
  inventing any new verifier machinery.

### C5 - `edge_case_coverage_replication`

- **Scenario**: same repository; the task statement adds one requirement
  to the existing `bugfix_inventory` fix: "searching an empty product
  list must return an empty list, not raise." A regression test for this
  specific requirement is required, exactly as requirement 5 already
  requires one for the multi-field-match bug.
- **Why this task, honestly**: this is **not** proposed as a second,
  independent exploit type - Section 5 found none. It's proposed as a
  **replication** of the *same* mechanism (a naive `"empty" in text and
  "assert" in text`-style weak check vs. a mutation-based strong check
  requiring the candidate test to fail against a seeded empty-list bug)
  on a structurally different requirement, in a task an agent has not
  seen calibrated against. If the gap reproduces here at the same
  magnitude, that's real evidence the flagship finding is a property of
  the *checking method* (lexical vs. behavioral), not an artifact of one
  specific test file's wording - which directly answers RESEARCH.md's own
  stated limitation ("single exploit shape found by accident... existence
  proof, not a claim about how common this failure mode is"). If it does
  *not* reproduce, that is also reported, not discarded.
- **Deterministic verifier**: identical structure to `eval/reward.py`'s
  existing three-condition design, re-run against a new weak-check string
  and a new known-buggy seed (empty-list-raises), producing a second,
  independent row in the same evidence table - not a rewrite of the
  existing experiment.
- **Reward implications**: same 0.0/0.5/0.85/1.0 scale.
- **Statistical framing**: like the flagship, this is a deterministic
  mechanism - reported as such, not as a repeated-trials sample.
- **Why it deserves to exist**: it's the only candidate that directly
  strengthens the flagship result's generality claim without fabricating
  a new mechanism, at close to zero new engineering cost (reuses
  `eval/reward.py`'s existing harness shape).

### C6 - `generalization_contact_index` (held-out)

- **Scenario**: a different, standalone package -
  `src/contact_index/directory.py` - with a `Contact` record (name, phone,
  tags) and a `Directory.find(query)` method carrying the *same*
  underlying bug shape (a contact matching on both name and multiple tags
  is returned once per match instead of once total), but different
  method/class/field names, a different file layout (`directory.py`
  instead of `inventory.py`, under a different package), and a different
  cover story in the task statement (a contacts app, not an inventory
  system).
- **Held-out discipline**: this task, its file names, its bug's exact
  manifestation, and its task statement must never be referenced in any
  prompt-engineering iteration, any system-prompt example, or any
  documentation the agent's context could plausibly include. It is used
  exactly once, at evaluation time, to answer one question: does an
  agent policy tuned entirely on `bugfix_inventory`/`bugfix_restock_exact_match`/
  `decoy_context_efficiency` (the development set) perform comparably here,
  or does performance drop in a way that indicates the policy had learned
  cues specific to the inventory domain rather than the general "find and
  fix a match-multiplicity bug, then prove it with a real test" strategy?
- **What must NOT leak into it**: no golden patch, no verifier source, and
  critically, no wording lifted from `bugfix_inventory`'s task.md - the
  requirement list must be written independently to avoid the agent
  pattern-matching on phrasing rather than reasoning about the actual
  repository in front of it.
- **Deterministic verifier**: same pattern as C0/C1 - a behavioral check
  constructing `Contact` instances directly and asserting dedup, plus the
  same mutation-based regression-test proof mechanism against a seeded
  `directory_buggy.py`.
- **Baseline/advanced comparison**: run identically to C0, but the
  *interpretation* is different - this is a generalization measurement,
  not a fresh baseline-vs-advanced comparison in its own right. A large
  drop in the advanced/baseline gap here relative to C0 would suggest the
  advanced protocol's benefit was partly domain-specific; a preserved gap
  would support it being a genuinely transferable strategy.
- **Sample size honesty**: one held-out task, one (or a small handful of)
  episode(s) per policy, is exploratory evidence about generalization, not
  a statistically powered claim - this must be stated plainly in whatever
  document reports the result, the same way `results/results.md` already
  labels its N=1/2 comparisons.
- **Why it deserves to exist**: it's the only task in this design that
  directly answers "did the agent learn a strategy or memorize this task,"
  which every research-direction document this project has written so far
  (README, RESEARCH.md) names as an open limitation.

## 7. Robustness / failure-recovery: a condition, not a task

Per Section 4's rejection of C10, the recommended design is a
**deterministic fault-injection wrapper** around `MCPToolSession`
(new infrastructure, not built in this pass), applied as a condition to
an *existing* task rather than encoded as seeded content in a new one:

- `NORMAL` - passthrough, today's behavior.
- `TOOL_FAILURE` - the wrapper deterministically raises `MCPToolError` on
  the Nth call to a named tool (seeded by episode config, not by chance),
  simulating exactly the shape of failure `manual-recovery-01` hit
  organically (a real `FileNotFoundError`-equivalent).
- `TOOL_LATENCY` - the wrapper sleeps a fixed, seeded duration before a
  named call, to measure whether latency alone (no error) changes
  behavior or just wall-clock trajectory duration.

Measured per Section 9's own list: failure detection (does the agent's
next call reference the failure, per `retry_of`), recovery attempt,
alternative-tool selection, additional tool calls, eventual success, and
repeated-failure loops (the same tool failing the same way more than
once without a strategy change).

**What this requires that doesn't exist yet**: the wrapper itself, and a
config surface on `run_agent_episode`/`eval/run_experiment.py` to select
a condition per episode. **What this doesn't require**: any new task -
`bugfix_inventory` and `bugfix_restock_exact_match` are both good hosts,
since both already have real trajectories to compare a faulted run
against. This is flagged as required infrastructure (Section 10), not
implemented here.

**Explicit limitation, stated in advance rather than discovered later**:
a single seeded failure per episode produces one data point, exactly like
`manual-recovery-01` today. A real recovery-*rate* claim needs multiple
episodes per condition with the same seed, which is a real N-episode
run against a live model - out of scope for this design pass, and this
document does not claim otherwise.

## 8. Resource-constrained evaluation: also a condition

Per Section 4's rejection of C9: apply a reduced tool-call budget
(`max_turns`, already a real parameter on `run_agent_episode`) to C1
specifically, because C1's induced self-correction trap gives an agent
something to legitimately trade off (diagnose the regression thoroughly
vs. finish inside budget) that C0 does not. No new task, no new verifier
logic - purely a different value for an existing parameter, observed
through the existing `truncated_by_max_turns` field.

## 9. Contamination and leakage analysis

| Vector | Status today | Status required for the suite |
|---|---|---|
| Golden patches | `golden/solution.patch` (singular, C0-only) | Must become per-task (`golden/<task_id>/...`) so C1/C6's answers don't leak into a shared, agent-adjacent location. |
| Verifier source | Excluded from every workspace via `_SEED_INCLUDE` allowlist (proven, tested) | Same discipline must extend to each new task's verifier file, whatever the registry design puts it in. |
| Task wording cross-contamination | N/A (one task) | C6 specifically must not reuse task.md phrasing from C0/C1/C2 - checked by a human diff read before C6 ships, not assumed. |
| Prior trajectories | `trajectories/` is committed and readable by a human, but never copied into an episode workspace | No change needed - already excluded by the same allowlist mechanism. |
| Repository layout hints | File names like `inventory.py` could bias a model with prior training exposure toward assuming a "typical" fix | Cannot be fully controlled (pretraining exposure isn't observable), which is exactly why C6 exists - not to eliminate this confounder, but to measure whether performance is sensitive to it. |

## 10. Infrastructure that MUST change before any new task ships

1. **A task registry**: `tasks/<task_id>/` directories each declaring
   their seed-include list, their buggy source file(s), and their
   verifier's behavioral check + regression-test path/mutation source.
   `harness/workspace.py` and `verify.py` must read from this instead of
   hardcoding `bugfix_inventory`'s specifics. This must be a
   **behavior-preserving refactor for `bugfix_inventory` itself** -
   checkable directly, since `tests/test_harness.py` already locks in
   that task's exact verifier behavior (0.0/0.5/0.85/1.0 thresholds,
   vacuous-test rejection, etc.) and must keep passing unchanged.
2. **Per-task golden directories** (`golden/<task_id>/`), replacing the
   single `golden/solution.patch`.
3. **A fault-injection wrapper** around `MCPToolSession` (Section 7),
   with a condition selector threaded through `eval/run_experiment.py`.
4. **`eval/run_experiment.py` extended to iterate over a task list**, not
   a single `--task-file`, while keeping today's single-task invocation
   working unchanged (no breaking change to the current reproduction
   path).

## 11. Infrastructure that must NOT change

- `src/mcp_rl_env/tools.py` / `server.py` - already fully task-agnostic;
  touching them for this work would be scope creep with no evidence
  behind it.
- `harness/trajectory.py` schema - already generic; every metric this
  design needs (`distinct_files_touched`, `retry_of`, `duration_s`) already
  exists.
- `eval/trajectory_metrics.py` - computes purely from the existing schema;
  no task-specific logic needed for any task proposed here.
- The `0.0/0.5/0.85/1.0` reward scale and its meaning - every new task
  reuses it unchanged, which is what makes cross-task comparison in
  `results/results.md`-style tables meaningful in the first place.
- `_safe_path` and the path-containment tests - proven correct, and
  Section 4 already found no task-shaped reason to add pressure on them.

## 12. What can be run with current infrastructure vs. what cannot

| Experiment | Runnable today | Needs |
|---|---|---|
| C0 baseline vs. advanced (already done) | Yes | - |
| C1, C2 as standalone verify/run cycles (no agent) | Yes, once each task's files exist - no registry needed to *hand-author and manually verify* a single task the way `bugfix_inventory` was originally built and hand-tested | A task registry only becomes necessary once more than one task must run *through the same harness invocation* without manual reconfiguration |
| C5 (replication experiment) | Yes, immediately - it's structurally identical to `eval/reward.py`, just pointed at new fixtures | Nothing new |
| C1/C2 baseline-vs-advanced with real API episodes | Requires `ANTHROPIC_API_KEY` (same limitation as C0 today) | Nothing new beyond what C0 already needs |
| C6 generalization comparison | Requires the task registry (Section 10, item 1) to avoid a second hand-maintained, drifting copy of `workspace.py`/`verify.py` | Task registry |
| Fault injection (Section 7) | No | New wrapper + config surface |
| Resource-budget condition (Section 8) | Yes - `max_turns` already exists on `run_agent_episode` | Nothing new |

## 13. Final recommended suite

**Six tasks, not fourteen**: C0 (existing) + C1 + C2 + C5 + C6, plus two
cross-cutting *conditions* (fault injection, resource budget) applied to
existing tasks rather than encoded as new ones.

This is deliberately below the 14-task ceiling the brief allows. Every
additional candidate considered (C3, C4, C7, C8, C9-as-task,
C10-as-task) was rejected with a specific, evidence-based reason recorded
in Section 4, not omitted for being difficult to build. The suite covers:

- **CAPABILITY**: C0, C1, C6
- **PLANNING / EFFICIENCY**: C2
- **RECOVERY**: C1 (self-correction), Section 7's condition (tool failure)
- **REWARD / EVALUATION**: C0 (flagship), C5 (replication)
- **GENERALIZATION**: C6
- **ROBUSTNESS**: Section 7's condition
- **SECURITY**: explicitly not a task - already covered by existing tests
  (Section 4, C8)

Dimensions from the original brief that are **explicitly not force-fit**
into a task, with the reason stated rather than left implicit:
multi-source requirements (redundant with existing protocol, C3),
ambiguous/conflicting requirements (fails the "deterministic evaluation"
bar by construction, C7), and resource constraints as a task rather than
a condition (manufactures difficulty rather than measuring a real
tradeoff, C9).

## 14. On general-purpose agent properties

No task here is framed as measuring general intelligence. What the suite
as designed can measure, with the evidence each one actually produces:

- **Planning** (C2): does the agent verify before committing to an edit
  when a plausible-looking wrong target exists.
- **Adaptation / self-correction** (C1): does the agent change course
  after an unexpected test failure it didn't cause on purpose.
- **Tool use under partial reliability** (Section 7, once built): does
  the agent's next action reference an observed failure.
- **Transfer** (C6): does a strategy tuned on one domain hold up on a
  structurally identical but superficially different one.

These are the properties the brief names (planning, adaptation, tool use,
recovery, transfer) - reported as specific, falsifiable, task-level
measurements, not summed into any claim about general intelligence.

## 15. What this review deliberately does not decide yet

Naming conventions for the task-registry schema, exact fixture data for
C1/C6, and the exact wrapper API for fault injection are implementation
details properly settled when those pieces are actually built, not in a
design review - fixing them now would be speculating about code that
doesn't exist. What this review commits to is the *shape* of each: which
tasks exist, which don't, why, and what infrastructure each one is
blocked on.
