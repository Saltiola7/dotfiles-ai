---
schema_version: 1
id: OCP-38
slug: migrate-client-opencode-history
context: opencode_control_plane
title: Migrate selected client OpenCode history into an isolated guest
kind: task
state: done
priority: high
points: null
depends_on:
  - OCP-32
  - OCP-35
relations: []
owns:
  - dot_local/bin/executable_opencode-history-migrate
  - tests/test_opencode_history_migrate.py
  - docs/specs/opencode_control_plane/README.md
  - docs/specs/opencode_control_plane/CHANGELOG.md
  - docs/tickets/context=opencode_control_plane/OCP-38-migrate-client-opencode-history.md
reads:
  - machine-local sandbox mount configuration
  - host OpenCode SQLite schema and aggregate counts
parallel_safe: false
validation:
  - focused migration tests
  - disposable live-data rehearsal
  - SQLite integrity and foreign-key checks
  - guest backup, startup, session, and rollback smoke
created: 2026-08-23
updated: 2026-08-24
completed: 2026-08-24
commits:
  - e60253a
jira_publications: []
migration: null
---

## Outcome

The client guest receives complete history for exactly selected private projects
without receiving unrelated host projects or host-global credentials.

## Context

The host database currently contains 3,053 sessions for the selected projects,
including 1,339 sessions in centralized DBSCTR worktrees and 1,053,124 matching
event rows. OpenCode JSON export/import omits todos and other session-owned state,
so a validated SQLite snapshot and exact prune is required.

## Scope

Add one fail-closed local migration command, rehearse it against a disposable
snapshot, correct any guest readiness blocker, back up the replaceable guest
database, deploy the validated candidate, and prove direct guest operation.
Bidirectional synchronization, automatic recurring migration, and unrelated
worktree cleanup are excluded.

## Acceptance Criteria

- The source opens read-only and the output must not already exist.
- Exactly three declared project roots and all related session records remain.
- Declared repository and centralized-worktree prefixes rebase to guest mounts.
- Host-global account and credential rows are absent.
- Unrelated session event streams are absent and retained streams remain valid.
- SQLite integrity, foreign keys, semantic relationships, and bounded count
  reconciliation pass before cutover.
- The guest database is backed up and restored on any failed startup or resume
  smoke; the host database remains unchanged.
- A MacBook can attach directly with `herdr --remote` through the guest Tailscale
  SSH address while the VM is running.

## Evidence

- A consistent read-only snapshot retained exactly three declared projects,
  3,054 sessions, 299,648 messages, 1,207,840 parts, and 1,055,756 events. The
  host database remained unchanged.
- The guest cutover retained all 1,413 child sessions with valid parents and 158
  sessions with todos. SQLite integrity and foreign-key checks passed, the
  database mode is `0600`, and pre-cutover and failed-cutover backups remain for
  rollback.
- The matching checksum-verified Herdr helper was installed in the guest user
  path. A MacBook attached directly through Tailscale SSH with `herdr --remote`
  and detached cleanly.
- All 56 affected tests, Python compilation, and Git whitespace validation
  passed. No transcript or credential content was used as evidence.

## Risks

Schema drift, WAL-incomplete copies, path leakage, stale worktree directories,
credential crossover, opaque event ownership, and insufficient guest disk space
can invalidate the migration. Every condition fails closed before replacement.

## Review

The migration is complete. The guest database remains replaceable, the retained
backups provide local rollback, and the unchanged host database remains the
authoritative source for any future one-time migration.
