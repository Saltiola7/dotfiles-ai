---
schema_version: 1
id: "AUTH-012"
slug: "manage-native-herdr-with-process-preserving-upgrades"
context: "shell_auth_startup"
title: "Manage native Herdr with process-preserving upgrades"
kind: "task"
state: "in_progress"
priority: "high"
points: null
depends_on: []
relations:
  - "AUTH-011"
owns:
  - ".chezmoidata.toml"
  - "config.example.toml"
  - "run_onchange_before_install-herdr.sh.tmpl"
  - "run_onchange_load-herdr-launchagent.sh.tmpl"
  - "dot_local/bin/executable_herdr-server-owner.tmpl"
  - "tests/test_herdr_launchagent.py"
reads:
  - "private_Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist.tmpl"
parallel_safe: false
validation:
  - "uv run --group test pytest tests/test_herdr_launchagent.py tests/test_portable_distribution.py tests/test_opencode_control_plane.py"
created: "2026-08-22"
updated: "2026-08-22"
completed: null
commits: []
jira_publications: []
---

## Outcome

Chezmoi owns the pinned native Herdr installation and upgrades a running server
through live handoff without terminating pane processes.

## Scope

- Pin the native macOS release identity and checksum in dotfiles data.
- Install the native executable under `~/.local/bin`.
- Replace running compatible servers only through live handoff.
- Defer LaunchAgent reload while any server owns live panes.
- Retire the separate Homebrew declaration after the native path is verified.

## Acceptance Criteria

- A missing native executable is downloaded, checksum-verified, version-checked, and installed atomically.
- A version change requests `server live-handoff` with the pinned protocol and version.
- A failed handoff preserves the running server and never calls `server stop`.
- Active servers defer LaunchAgent reconciliation until a natural login or reboot.
- Focused tests and live migration evidence cover installation, rollback, pane count, process identity, and runtime health.

## Risks

- Live handoff is experimental and supports at most 64 pane file descriptors; deployment must verify the current pane count first.
- The handoff disconnects clients and transient API requests; clients must reconnect.
- The handed-off replacement is detached until launchd starts it at a later natural login or reboot.

## Review

Pending implementation and live deployment evidence.
