---
schema_version: 1
id: "DAI-031"
slug: "restore-rnd-state-authority-and-health"
context: "dotfiles_ai_distribution"
title: "Restore R&D state authority and health"
kind: "bug"
state: "done"
priority: "high"
points: 2
depends_on:
  - "DAI-021-F2"
relations:
  - "related:DAI-021-F1"
owns:
  - "R&D scheduler state resolution, read-only health output, regression evidence, deployment, and six-lens operation proof"
reads:
  - "Centralized state root, Hermes gateway environment, scheduler schema 7, and retained lens cadence"
parallel_safe: false
validation:
  - "Focused R&D tests, rendered runner, centralized-state health probe, Hermes cron execution, and six-lens exhaustion"
created: "2026-08-25"
updated: "2026-08-26"
completed: "2026-08-26"
commits:
  - "79ff5fe711d2a905a73e72336f884dc5ee8d218f"
  - "0ab16f892a745fbb38dcc87978f00754e5f8414d"
jira_publications: []
migration: null
---

## Outcome

Hermes and interactive OpenCode use one authoritative R&D scheduler database,
and read-only health reports whether dispatch is halted and which lenses are due.

## Context

Hermes inherited `DOTFILES_AI_STATE_ROOT` but not `DBSCTR_RND_STATE`. The runner
ignored the centralized root and silently opened a local shadow scheduler. Its
safety circuit halted while the authoritative scheduler retained 19 passes and
six overdue daily lenses. The existing health envelope omitted halt and per-lens
eligibility, so a healthy cron heartbeat hid the stopped dispatcher.

## Scope

- Resolve scheduler state and receipts from the explicit variables first, then
  the centralized state root, then the existing local default.
- Keep state paths private while reporting the selected authority class.
- Version the health envelope and expose halt plus bounded per-lens cadence,
  eligibility, and active-attempt state without opening a write transaction.
- Keep later reservations in an active parallel batch independent of the global
  review lock held by an already-running lens history scan.
- Deploy the runner and prove Hermes drains every eligible lens to a bounded no-op.

## Acceptance Criteria

- A Hermes-like process with only `DOTFILES_AI_STATE_ROOT` uses
  `dbsctr/rnd/dbsctr-rnd.sqlite3` and `dbsctr/rnd/receipts` beneath that root.
- Explicit scheduler variables retain precedence and installations without a
  centralized root retain the current local default.
- Health schema 2 reports `state_authority`, `halt_reason`, and exactly six
  validated lens records without exposing a filesystem path.
- Halted state and overdue lenses are visible before a reservation attempt.
- A fresh batch reconciles authoritative worker state, while a registered active
  batch can reserve its remaining due lenses from scheduler-local state and
  reconciles again before reporting exhaustion.
- Focused tests pass and one live Hermes run reaches `no_lens_due` after all
  eligible lenses register.

## Evidence

All 40 focused tests passed, the rendered and deployed runner had zero targeted
drift, and independent review found no remaining correctness or safety issue.
Hermes completed all six lenses, raised retained passes from 19 to 25, reached
`no_lens_due`, and retained zero active attempts without changing shadow state.

## Risks

Selecting the wrong database can duplicate workers or abandon retained cadence.
Deployment must preserve the centralized database unchanged and must not merge,
delete, or reset the shadow database automatically.

## Review

Review must reject path disclosure, implicit state migration, health writes,
schema ambiguity, and caller-specific environment duplication.
