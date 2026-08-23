---
schema_version: 1
id: "AUTH-012"
slug: "manage-native-herdr-with-process-preserving-upgrades"
context: "shell_auth_startup"
title: "Manage native Herdr with process-preserving upgrades"
kind: "task"
state: "done"
priority: "high"
points: null
depends_on: []
relations:
  - "related:AUTH-011"
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
completed: "2026-08-22"
commits:
  - "12f402a"
  - "9020e21"
jira_publications: []
migration: null
---

## Outcome

Chezmoi owns the pinned native Herdr installation and upgrades a running server
through live handoff without terminating pane processes.

## Context

The prior LaunchAgent handoff could preserve pane processes but did not keep the
replacement server durable after the initiating process exited.

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
- A managed LaunchAgent owner remains alive across handoff, tolerates transient probe failures, and makes unexpected server disappearance restartable.
- Focused tests and live migration evidence cover installation, rollback, pane count, process identity, and runtime health.

## Evidence

- Commits `12f402a` and `9020e21` define and implement the managed native handoff.
- The affected test suite and live process-preservation soak passed.

## Risks

- Live handoff is experimental and supports at most 64 pane file descriptors; deployment must verify the current pane count first.
- The handoff disconnects clients and transient API requests; clients must reconnect.
- An unmanaged handed-off replacement is detached until launchd starts it at a later natural login or reboot.
- Starting handoff outside the managed owner can leave the replacement exposed to the initiating process supervisor.

## Review

Implementation and focused tests pass. Initial live attempts preserved identities
through handoff but the replacements later shut down, forcing session restores.
The recovered native server retained 54 panes and exposed 46 unique session
identities; LaunchAgent owner PID `73813` and server PID `47444` remained stable
through a three-minute soak. All 75 affected tests passed and final independent
review reported no actionable findings. The Homebrew declaration is retired;
the installed keg remains temporarily available for rollback.
