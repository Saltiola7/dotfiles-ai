# Paced Startup And Failed-Restore Retention

## Domain And Evidence

Home: `shell_auth_startup`; owner: dotfiles maintainer. Use its Engineering
Profile with Python, Security and Cloud modules; risk: elevated. Existing
OpenCodeSession, HerdrPane, centralized state root and recovery manifest remain
the domain. Conversation persistence belongs to OpenCode; the manifest records
reopening intent and is not a history database.

The source wrapper retries shlock 200 times with 0.1-second sleeps while the
holder can sleep six seconds for launch spacing. Concurrent restoration can
exhaust the roughly twenty-second acquisition budget even while other launches
succeed. Every lock failure currently emits the same message and discards shlock
stderr. This proves a contention defect, not the precise cause of a past failure.

The recovery helper replaces its manifest with only currently running explicit
OpenCode session arguments. The owner starts its watcher even after restore
failure. Thus failed entries can disappear on the next capture while conversation
history remains intact. Current health and database existence checks do not prove
all pre-restart work was persisted or reconstruct the original failure.

## Startup Contract

Preserve at least five-second spacing and exact argument forwarding. A burst of
30 healthy concurrent session resumes must complete without false unavailable-
storage failures; allow the approximately three-minute paced queue to drain.
Retain bounded admission: distinguish a progressing queue from a stalled lock,
and fail a continuously stalled holder after twenty seconds without progress.
Bound total admission to five minutes. Use monotonic elapsed time for deadlines;
clock rollback, stale locks and interruption must not weaken exclusion.

Reuse the existing shlock coordination identity during transition so older and
newer wrappers cannot admit starts independently. Do not delete a live owner's
lock. Preserve stale-owner handling, timestamp validation, external-volume
preflight, no internal fallback, and non-Herdr behavior. Give sanitized distinct
diagnostics for stalled/busy admission and unsafe/unavailable state. Do not claim
that Herdr Host doctor diagnoses lock contention.

## Recovery Persistence Contract

The helper owns a versioned manifest, atomically replaced under one shared
exclusive lock for restore, capture and watch. Accept legacy schema 1 as pending
recovery intent. Write schema 2 with exact top-level fields `schema_version` and
`sessions`; each entry has `pane_id`, `directory`, `session_id`, and
`recovery_state` (`pending` or `observed`). Validate types, exact keys, identifier
syntax and uniqueness before any write or launch. The records remain private;
never publish their identifiers, directories or transcript contents.

At restore start persist all existing entries as pending before invoking any
launch, making interruption retryable. Clear pending only after observing the
exact session running. Capture preserves pending entries that are absent from the
current process inventory. An observed entry absent from a successful subsequent
inventory is an intentional closure and can be removed. A failed or partial
inventory cannot remove entries. Resolve a manually reopened pending session to
its verified current pane/directory without retaining a duplicate old mapping.

An occupied or missing pane, different session, missing directory or unknown
OpenCode identity leaves recovery pending and reports bounded failure. Never send
commands to a replacement/occupied pane or move a session automatically. Check
identity and recorded directory before launching. Conflicting pending mappings
must remain recoverable with a diagnostic rather than being silently discarded;
if representing them requires changing this schema, reopen readiness first.

`--check` remains read-only with respect to recovery intent. Interrupted writes
leave either the prior complete manifest or the new complete manifest. Reject
symlinks and unsafe state targets; do not follow links or clobber unrelated files.
Older helpers reject schema 2; rollback must preserve a private backup and must
not feed schema 2 into an old writer or silently discard pending entries.

## Visual Evidence

State and interaction: required transition table below. Review question: when may
a recovery entry be forgotten? Canonical source: Recovery Persistence Contract;
owner: maintainer; change trigger: capture/restore semantics or schema changes.

| Prior state | Verified event | Next state/action |
|---|---|---|
| Legacy entry or either state | Restore begins | Persist pending before launch |
| pending | Exact session observed, including manual reopen | observed at verified current location |
| pending | Session absent or restore fails | Retain pending |
| observed | Complete successful inventory no longer contains session | Remove closed entry |
| either | Inventory invalid, partial or unavailable | Preserve prior manifest; report failure |
| either | Collision, unsafe target or mismatched identity | Refuse launch/destructive reconciliation |

**Text Equivalent:** A missing session is forgotten only after it was previously
observed and a complete successful later inventory confirms absence. A restore
first marks every entry pending; a failed launch or inventory cannot erase it.
Exact observation permits later intentional closure. Conflicts never authorize
overwriting a pane or discarding unresolved intent.

Boundary, data/trust and dependency/deployment: not_applicable; existing private
local state and signed-host boundaries remain unchanged. Schema: not_applicable;
the flat versioned field contract above is clearer than an ER diagram.
Quantitative: not_applicable; the burst size and deadlines are acceptance limits,
not benchmark measurements.

## Acceptance And Rollback

Focused pytest checks must first fail against the old behavior, then pass for:
30 concurrent resumes with spacing; genuine stalled lock; dead owner; cancellation;
bad timestamp and state targets; legacy read; failed-restore plus capture plus
helper restart; manual reopen; observed-session closure; conflicting/occupied
panes; capture/restore concurrency; atomic-write failure; and read-only check.
Use simulated time where appropriate plus a bounded real-process lock probe.
Tests never target live sessions, manifests or the running Herdr server.

Update current README/operation guidance and context changelog, preserving
historical evidence. No live restart or deployment is authorized by this slice.
Targeted rollout owns private backup, installed-byte verification, loaded-watcher
proof and operator-approved exact-session recovery qualification.
