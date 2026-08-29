---
schema_version: 1
id: "OCP-40"
slug: "enable-interactive-discovery-shell"
context: "opencode_control_plane"
title: "Enable interactive Discovery Coordinator shell research"
kind: "task"
state: "in_progress"
priority: "high"
points: null
depends_on: []
relations: []
owns:
  - "private_dot_config/opencode/agents/discovery-coordinator.md"
  - "docs/specs/opencode_control_plane/README.md"
  - "docs/specs/opencode_control_plane/CHANGELOG.md"
  - "tests/test_dbsctr_lifecycle.py"
reads:
  - "dot_agents/skills/discovery/SKILL.md"
parallel_safe: false
validation:
  - "Focused lifecycle and control-plane tests, resolved configuration, targeted chezmoi deployment, and a fresh coordinator shell smoke pass"
created: "2026-08-28"
updated: "2026-08-28"
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Discovery Coordinator can investigate through native local CLIs, APIs, notebook
kernels, and private systems in the same interactive workflow that persists
durable Discovery artifacts.

## Context

The coordinator could write `docs/**` and delegate repository or public research,
but denied Bash. Live metadata discovery therefore attempted to misuse browser
automation as a terminal proxy and could not use the direct Databricks CLI.

## Scope

Allow unrestricted Bash only for Discovery Coordinator and clarify its research
behavior. Keep Explore and Scout shell-denied, structured edits scoped to
`docs/**`, governed private result bodies outside hosted-model context, source
implementation out of role, and Initiative launch ask-gated.

## Acceptance Criteria

- Discovery Coordinator resolves with unrestricted Bash permission.
- Its structured edit permission remains limited to `docs/**`.
- It prefers native CLI/API or notebook-kernel access and never uses browser
  automation as a shell proxy when a direct interface exists.
- Explore and Scout remain shell-denied.
- Governed private result bodies stay local; only locally filtered, privacy-safe
  metadata or bounded typed-adapter output enters model context.
- External, destructive, costly, irreversible, and materially expanded effects
  retain explicit user confirmation policy despite unrestricted command matching.
- Focused tests, resolved configuration, targeted deployment, and a fresh shell
  smoke pass.

## Risks

Unrestricted Bash can mutate files and external systems, bypassing the structured
edit boundary. Agent instructions are not an OS sandbox; user confirmation,
least-privileged credentials, external-system controls, and review remain the
effective safeguards.

## Evidence

Pending implementation.

## Review

Pending implementation and deployment.
