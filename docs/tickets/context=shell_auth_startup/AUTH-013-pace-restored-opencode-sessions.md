---
schema_version: 1
id: "AUTH-013"
slug: "pace-restored-opencode-sessions"
context: "shell_auth_startup"
title: "Pace restored OpenCode sessions"
kind: "bug"
state: "done"
priority: "high"
points: null
depends_on: []
relations:
  - "related:AUTH-012"
owns:
  - "dot_local/bin/executable_opencode.tmpl"
  - "dot_local/bin/executable_herdr-opencode-restore"
  - "dot_local/bin/executable_herdr-server-owner.tmpl"
  - "tests/test_herdr_launchagent.py"
reads:
  - "private_dot_config/herdr/config.toml.tmpl"
parallel_safe: false
validation:
  - "uv run --group test pytest tests/test_herdr_launchagent.py"
created: "2026-08-23"
updated: "2026-08-23"
completed: "2026-08-23"
commits:
  - "01ef8fa"
  - "828c539"
  - "36715c4"
  - "1980b9b"
jira_publications: []
migration: null
---

## Outcome

Herdr restores exact OpenCode sessions at a bounded rate, with explicit automatic
permission approval, instead of launching every persisted session concurrently.

## Context

Concurrent restoration overloaded startup and left recovered sessions without the
explicit automatic permission mode expected for unattended Herdr processes.

## Scope

Pace exact session restoration and add `--auto` only to interactive, run, and
resume starts; administrative `session list` calls remain unchanged.

## Acceptance Criteria

- Every Herdr-launched OpenCode process receives one `--auto` flag; non-Herdr launches are unchanged.
- Herdr `--session` starts are serialized and begin at least five seconds apart.
- Stale startup locks do not permanently block later launches.
- Capture and identity checks recognize `--session` independently of argument order.
- The manifest watcher starts even when one restore entry fails.
- Deployment recovers stalled panes without replacing the active Herdr server or changing session identity.

## Evidence

- The affected Herdr and distribution suites pass with rendered shell syntax.
- Live recovery retained session identities while pacing restored starts.

## Risks

- `--auto` broadens OpenCode permission approval; explicit denied permissions remain the control boundary.
- Recovery must exclude the active operator pane and reject unsafe manifest identifiers.
- Serial recovery is intentionally slower than concurrent restore.

## Review

All 78 affected tests and rendered syntax checks pass, and independent review
reported no actionable findings. Targeted deployment recovered 45 stalled exact
sessions and verified 46 unique rendered `--auto` sessions without restarting
Herdr. The stale duplicate of the active session was stopped at its existing pane,
which remains open at a shell while the active pane retains the exact identity.
