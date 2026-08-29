---
schema_version: 1
id: "OCP-41"
slug: "fix-initiative-launch-handoff"
context: "opencode_control_plane"
title: "Fix Initiative default-branch and Build handoff"
kind: "bug"
state: "done"
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
completed: "2026-08-29"
commits:
  - "43dda62b012d62a62bc5285eeaa3352a543a717a"
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

- The focused approval regression failed before implementation because the
  resolved base branch was absent, then the complete affected control-plane and
  lifecycle suites passed 72 tests.
- Canonical ticket validation reports only the pre-existing duplicate `DAI-032`
  baseline; OCP-41 has no finding.
- Independent elevated-risk review identified and verified removal of the unsafe
  caller branch override, then found no remaining high or medium issue.
- Targeted chezmoi preview changed exactly four managed files. Apply completed,
  the managed diff is empty, and deployed files are byte-identical to source.
- The deployed resolver returns `main` for this repository and a fresh Discovery
  Coordinator process successfully executed its Bash smoke in the cycle
  worktree. The current OpenCode process requires restart to load core revision
  `3.30`.
- Development Kernel Gate Commit: `43dda62b012d62a62bc5285eeaa3352a543a717a`.
  Gate Exceptions: none.

## Review

The coordinator remains outside Build evidence, the helper allowlist is
unchanged, and only the remote symbolic `HEAD` can select an Initiative protected
base. Real PPCD launch remains separately exact-approval-gated after restart.
