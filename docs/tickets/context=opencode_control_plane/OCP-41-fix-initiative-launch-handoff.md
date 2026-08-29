---
schema_version: 1
id: "OCP-41"
slug: "fix-initiative-launch-handoff"
context: "opencode_control_plane"
title: "Fix Initiative default-branch and Build handoff"
kind: "bug"
state: "in_progress"
priority: "high"
points: null
depends_on: []
relations: []
owns:
  - "private_dot_config/opencode/lib/dbsctr-runtime.ts"
  - "private_dot_config/opencode/tools/dbsctr.ts"
  - "private_dot_config/opencode/agents/discovery-coordinator.md"
  - "dot_agents/skills/discovery/SKILL.md"
  - "tests/test_opencode_control_plane.py"
  - "tests/test_dbsctr_lifecycle.py"
  - "docs/specs/opencode_control_plane/README.md"
  - "docs/specs/opencode_control_plane/CHANGELOG.md"
  - "docs/specs/dbsctr_v3_lifecycle/features/initiative-discovery.md"
  - "docs/specs/dbsctr_v3_lifecycle/CHANGELOG.md"
reads:
  - "dot_local/bin/executable_dbsctrctl"
parallel_safe: false
validation:
  - "Focused control-plane and lifecycle tests, resolved configuration, targeted deployment, and fresh Initiative launch smoke"
created: "2026-08-29"
updated: "2026-08-29"
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Initiative launch discovers non-`main` protected bases and starts a validated
Build primary without attributing Discovery Coordinator as Build evidence.

## Context

Launching a ready slice in a repository whose protected base is `master` used
the helper's `main` default. A same-repository retry then attached the
`discovery-coordinator` message during cycle creation, which correctly failed the
Build-harness allowlist before Herdr could start the worker.

## Scope

Resolve and exact-approval-bind the target origin's default branch, keep the
coordinator outside cycle runtime evidence, explicitly select `build` for fork
and fresh fallback, and preserve delivery intent during recovery. Do not broaden
the harness allowlist or grant Build authority to Discovery.

## Acceptance Criteria

- A target whose symbolic remote `HEAD` names `master` launches with
  `--base-branch master` without user-supplied branch metadata.
- Exact approval binds the resolved protected base branch.
- Same-repository Initiative begin excludes coordinator runtime arguments.
- Fork and fresh fallback explicitly select `--agent build`.
- Ordinary typed Build begin still records its current validated runtime.
- Failed recovery cannot silently substitute a different delivery intent.
- Affected tests, deployment, and fresh loaded-runtime smoke pass.

## Risks

Remote default-branch discovery requires authenticated Git read access already
needed by cycle fetch. Choosing the neutral Build primary preserves provider
selection but intentionally excludes provider-specific primary overlays.

## Evidence

Pending implementation and gate evidence.

## Review

Pending.
