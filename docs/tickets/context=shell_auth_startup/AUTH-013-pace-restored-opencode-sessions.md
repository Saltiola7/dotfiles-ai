---
schema_version: 1
id: "AUTH-013"
slug: "pace-restored-opencode-sessions"
context: "shell_auth_startup"
title: "Pace restored OpenCode sessions"
kind: "bug"
state: "in_progress"
priority: "high"
points: null
depends_on: []
relations:
  - "AUTH-012"
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
completed: null
commits: []
jira_publications: []
---

## Outcome

Herdr restores exact OpenCode sessions at a bounded rate, with explicit automatic
permission approval, instead of launching every persisted session concurrently.

## Acceptance Criteria

- Every Herdr-launched OpenCode process receives one `--auto` flag; non-Herdr launches are unchanged.
- Herdr `--session` starts are serialized and begin at least five seconds apart.
- Stale startup locks do not permanently block later launches.
- Capture and identity checks recognize `--session` independently of argument order.
- The manifest watcher starts even when one restore entry fails.
- Deployment recovers stalled panes without replacing the active Herdr server or changing session identity.

## Risks

- `--auto` broadens OpenCode permission approval; explicit denied permissions remain the control boundary.
- Recovery must exclude the active operator pane and reject unsafe manifest identifiers.
- Serial recovery is intentionally slower than concurrent restore.
