---
schema_version: 1
id: "AUTH-014"
slug: "preserve-herdr-external-volume-access"
context: "shell_auth_startup"
title: "Preserve Herdr external-volume access"
kind: "bug"
state: "in_progress"
priority: "high"
points: null
depends_on: []
relations:
  - "related:AUTH-012"
  - "related:AUTH-013"
owns:
  - ".chezmoitemplates/herdr-launchagent-supervisor.c"
  - ".chezmoiignore"
  - "run_onchange_before_build-herdr-launchagent-supervisor.sh.tmpl"
  - "private_Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist.tmpl"
  - "run_onchange_load-herdr-launchagent.sh.tmpl"
  - "tests/test_herdr_launchagent.py"
  - "tests/test_portable_distribution.py"
reads:
  - "dot_local/bin/executable_state-root-exec"
  - "dot_local/bin/executable_herdr-server-owner.tmpl"
parallel_safe: false
validation:
  - "uv run --group test pytest tests/test_herdr_launchagent.py tests/test_portable_distribution.py"
created: "2026-08-24"
updated: "2026-08-24"
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Managed Herdr panes inherit a narrow, user-grantable macOS responsible process
identity and can access configured external state and project volumes.

## Context

Kernel and TCC evidence showed that launchd executed the shell-based state guard
as the responsible process. macOS therefore attributed Herdr and every new pane
to `/bin/sh`, denied removable-volume access, and could not prompt because the
responsible executable was a platform shell. The current Herdr binary already
has an exact allowed removable-volume grant, so Unix permissions, mount state,
and generic XDG routing are not the cause.

## Scope

- Build one native supervisor from reviewed source with the system compiler.
- Launch the supervisor directly while retaining the state guard, owner monitor,
  process-preserving live handoff, and paced exact-session recovery as children.
- Forward termination and preserve child status.
- Deploy managed files without replacing the active Herdr process ancestry.

## Acceptance Criteria

- The LaunchAgent's first program is a signed Mach-O supervisor, not a script or platform shell.
- The supervisor starts the existing state guard and owner, waits for it, forwards termination, and returns its status.
- Source changes rebuild the supervisor atomically; unchanged applies retain its binary identity.
- Managed code does not edit TCC or request Full Disk Access.
- Existing panes and the active server remain untouched until an explicit restart approval.
- After approval and removable-volume consent, a fresh Herdr pane can read and write the configured external volume.

## Evidence

- Pending focused tests, rendered plist validation, Mach-O signature inspection,
  independent review, managed-file deployment, and post-restart TCC probe.

## Risks

- Changing process responsibility requires a full server restart; live handoff
  cannot change inherited macOS responsibility because the old server spawns the
  replacement.
- A source change changes the ad-hoc code hash and may require renewed macOS consent.
- The supervisor must stay alive across Herdr live handoff so launchd does not race
  the detached replacement.

## Review

Pending.
