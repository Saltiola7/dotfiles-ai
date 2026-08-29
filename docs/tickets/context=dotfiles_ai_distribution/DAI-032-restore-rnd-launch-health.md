---
schema_version: 1
id: "DAI-032"
slug: "restore-rnd-launch-health"
context: "dotfiles_ai_distribution"
title: "Restore R&D launch health"
kind: "bug"
state: "in_progress"
priority: "high"
points: 3
depends_on:
  - "DAI-031"
relations:
  - "related:DAI-021-F1"
owns:
  - "R&D launch retry state, readiness evidence compatibility, guarded Hermes health, moved-source cutover, focused tests, deployment, and operation proof"
reads:
  - "Machine-local review and backlog roots, authoritative scheduler schema 7, Hermes LaunchAgent, and sanitized launch outcomes"
parallel_safe: false
validation:
  - "Focused R&D tests, rendered runner and Hermes configuration, schema migration, targeted chezmoi deployment, guarded gateway readiness, and one live overdue-lens pass"
created: "2026-08-29"
updated: "2026-08-29"
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Autonomous R&D launches from the configured machine-local source, preserves its
external-state guard, and backs off repeated OpenCode launch failures without
advancing lens cadence or creating an unbounded retry storm.

## Context

The dotfiles source moved while the deployed runner and configured backlog root
still selected the old checkout. The five-minute Hermes job continued reserving
an overdue lens, but OpenCode returned the same server error hundreds of times.
Scheduler health showed releases but no retry state, and Hermes reported its
intentionally guarded LaunchAgent as stale because Hermes compares plists exactly.

## Scope

- Keep review and backlog roots machine-local and render both from configuration.
- Persist bounded launch-failure backoff without changing lens eligibility.
- Expose backoff through path-free read-only health and clear it after successful
  registration or explicit schedule reset.
- Validate the guarded Hermes plist and use launchd readiness as the managed macOS
  authority without weakening the external-state marker check.
- Deploy from an isolated cycle worktree and prove the overdue lens completes.

## Acceptance Criteria

- The deployed repository catalog selects the configured moved source and no
  checked-in artifact contains its private path.
- A failed OpenCode launch releases its reservation, increments the launch-failure
  count, and sets a bounded retry time without changing lens cadence.
- Reservations during backoff return `launch_backoff` and start no worker.
- Successful worker registration and `reset-schedule` clear launch backoff.
- Health schema 3 reports scheduler schema 8, launch-failure count, retry time,
  and active backoff without exposing a filesystem path or writing state.
- The guarded Hermes plist retains `state-root-exec`, exact generated inner argv,
  centralized state environment, and a running launchd service.
- Focused tests pass and one live Hermes run advances the pass count for every
  overdue lens before returning `no_lens_due`.

## Risks

An invalid migration can stall the scheduler, while an over-broad retry policy can
hide recovery. Deployment must preserve all passes and cadence, never write the
OpenCode history database, and never remove the external-state guard.

## Review

Review must reject hard-coded private paths, cadence advancement on launch failure,
unbounded retries, health writes, provider-error disclosure, weakened state-root
validation, and claims based on a partial federated history source set.
