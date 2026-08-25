---
schema_version: 1
id: "OCP-39"
slug: "scope-centralized-xdg-to-opencode-runtime"
context: "opencode_control_plane"
title: "Scope centralized XDG state to OpenCode runtimes"
kind: "task"
state: "done"
priority: "high"
points: null
depends_on:
  - "OCP-32"
relations: []
owns:
  - "Herdr LaunchAgent environment, scoped state contract, regression evidence, and managed deployment"
reads:
  - "OpenCode wrapper and lifecycle-worker centralized-state routing"
parallel_safe: false
validation:
  - "Focused Herdr tests, rendered plist validation, targeted chezmoi preview/apply, and live no-restart health checks pass"
created: "2026-08-24"
updated: "2026-08-25"
completed: "2026-08-24"
commits:
  - "39e12a13f9dc191a6edc62559408f2e08c074fd0"
jira_publications: []
migration: null
---

## Outcome

Keep external OpenCode state portable without redirecting every tool launched in
a Herdr pane into OpenCode's XDG tree.

## Context

The Herdr LaunchAgent exported centralized `XDG_DATA_HOME` and `XDG_STATE_HOME`
server-wide. Every child pane inherited those generic paths, causing shell tools
such as ble.sh and plain personal chezmoi commands to use OpenCode-owned storage.

## Scope

Remove generic XDG variables only from the Herdr LaunchAgent. Preserve explicit
state, DBSCTR, Hermes, and worktree paths, plus the managed OpenCode wrapper and
lifecycle-worker XDG exports. Deploy without restarting active panes.

## Acceptance Criteria

- A rendered centralized-state Herdr plist has no generic XDG variables.
- OpenCode, DBSCTR spawner, and DBSCTR watchdog retain centralized XDG routing.
- Native-state rendering remains unchanged.
- Applying the managed plist does not interrupt the active Herdr server.
- The external state-root path remains per-machine and portable through existing config.

## Risks

Existing server and pane processes keep their inherited environment until their
next natural replacement. No data migration is required because OpenCode retains
the same wrapper-owned paths.

## Evidence

- Regression first failed because the rendered Herdr environment still contained
  `XDG_DATA_HOME`; the scoped implementation then passed all 25 Herdr tests.
- `uv run --group test pytest -q tests/test_herdr_launchagent.py tests/test_opencode_control_plane.py tests/test_portable_distribution.py`: 79 passed.
- Centralized and native rendered Herdr plists both passed `plutil -lint`.
- `git diff --check` passed.
- Targeted chezmoi preview showed only the two XDG key removals. Apply left no
  managed diff, and the deployed plist passed `plutil -lint` without either key.
- The guarded loader reported that LaunchAgent reload was deferred. Herdr stayed
  healthy on the same PID `2974`, version `0.8.2`, and protocol `20`.

## Review

The diff changes only the generic Herdr environment boundary. Explicit external
state paths and scoped OpenCode/lifecycle routing remain tested. No process,
session, data path, dependency, permission, or schema changed. The running
LaunchAgent retains its old in-memory environment until the next natural start.
