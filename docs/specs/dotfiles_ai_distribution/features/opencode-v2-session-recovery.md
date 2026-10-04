# Native V2 session recovery admission

Status: source contract. Risk: critical. Owner: project maintainers.
Profile: ../PROFILE.md. Product Intent: ../PRODUCT.md.
Authority: opencode-rolling-stable INT-012, INT-013, INT-015 and INT-033.
Modules: Python, Security, Cloud. No production restart in this source slice.

## Problem and behavior

The existing restoration helper accepts IDs from the legacy `session` table.
V2 retains that table after conversion, and `--session` can create an absent
session. A legacy row therefore cannot authorize a V2 restoration attempt.

Given a selected managed V2 runtime, restore only IDs positively verified in the
current V2 database, with the expected native directory. Given an incomplete,
malformed or unavailable schema/conversion, refuse before launching anything.
Given retained V1 rows without matching V2 identities, never fall back to V1.
Given a verified V1 runtime, preserve existing V1 behavior. Unknown runtime
versions and version-probe failure refuse recovery rather than guessing.

## Interface and ownership

Update `herdr-opencode-restore` and its existing session-recovery tests. Preserve
capture, manifest serialization, pacing, locks, pane checks and existing native
argv handling. Use the selected managed wrapper's bounded `--version` result to
select V1 or V2; accept observed bare stable V1 and `opencode v2.x.y` forms only.
Do not invoke an alternate binary, enumerate message bodies, change provider
selection, manufacture actor identity or introduce continuation orchestration.

SQLite reads use read-only URI mode, bounded busy timeout/progress deadline and
one consistent read transaction. Require actual tables rather than views.
V2 requires `session_v2` with `id` and `directory`, plus native `session_message`
with identity/association fields. If legacy `session` exists, require the native
`kv` marker `migration.v1-v2` to be exactly `{"phase":"completed"}`. Reject
duplicate JSON keys, extra fields, malformed or oversized marker data. No V1
fallback on a V2 failure. A V1 runtime refuses a database with V2 schema present.
No schema query or helper writes to the native database.

For each manifest entry, compare its canonical directory with the native session
directory before inspecting/launching the pane. Missing IDs or directory mismatch
remain pending failures; report bounded generic reasons, never private transcript
content. Existing occupied-pane and duplicate-running-session guards still apply.
Do not claim provider-affinity qualification from checking ID and directory alone;
that remains part of controlled live resume.

## Acceptance

- V1 fixture recovery remains compatible; V2 fixture IDs/directories restore.
- V1-only ID in a V2-selected runtime refuses with no pane launch.
- Mixed database requires completed native conversion; malformed/duplicate/extra
  marker fields and schema views refuse without launch.
- Wrong native directory, missing database, unknown version and bounded query
  failure refuse safely. Native fixture checks do not qualify live history.
- Existing capture, pacing, lock serialization and preservation tests pass.

Project authorities: pytest, selected shell/native fixtures and git diff checks.
Development Kernel, Refactor, Review/Integrate and Maintain/Retire required.
Release, Deploy and Operate not applicable to this source-only change. Deployment,
Desktop integration, guest history admission and exact live resume remain in the
fleet cutover slice. No exceptions. Publish a PR and merge after passing checks
under the operator's approval; no direct main push.

## Visual Evidence

State and interaction: required, canonical selection table below. Boundary and
data/trust: required, reuse V2-MIGRATION.md's recovery flow and Text Equivalent.
Schema: not_applicable, native upstream schema and explicit column checks above
are sufficient. Deployment: not_applicable, no topology change. Quantitative:
not_applicable, no comparative claim. Owner: distribution maintainer; update on
native schema, version selection or restoration precondition change.

| Runtime | Database evidence | Recovery decision |
|---|---|---|
| Verified V1 | Legacy schema only, matching ID/directory | Existing pane checks then restore |
| Verified V2 | V2 identity/directory; completed marker when V1 retained | Existing pane checks then restore |
| V2 | Only V1 identity, incomplete conversion or directory mismatch | Refuse, never fall back |
| Unknown | Any database | Refuse before launch |

**Text Equivalent:** Runtime identity selects the database contract. Only a matching
session and directory in that contract can reach existing pane checks. Unknown,
incomplete and mismatched evidence stops recovery without creating a conversation.
