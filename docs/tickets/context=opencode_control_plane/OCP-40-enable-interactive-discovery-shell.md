---
schema_version: 1
id: "OCP-40"
slug: "enable-interactive-discovery-shell"
context: "opencode_control_plane"
title: "Enable interactive Discovery Coordinator shell research"
kind: "task"
state: "done"
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
completed: "2026-08-28"
commits:
  - "71ae56454b7c7d22701288ced46e066cf1cc64f8"
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

- The focused regression first failed on the coordinator's missing `bash: allow`,
  then the lifecycle and control-plane suites passed 72 tests.
- Canonical ticket validation reports only the pre-existing duplicate `DAI-032`
  baseline; OCP-40 has no finding.
- Independent elevated-risk review found no remaining issue after the private-result
  boundary and explicit external-shell trust edge were added.
- Targeted chezmoi preview changed only the coordinator, apply completed, managed
  diff is empty, and deployed source identity matches the Gate Commit.
- A fresh OpenCode process resolved `bash: allow`, retained ordered `docs/**` edit
  rules and ask-gated Initiative launch, and executed a coordinator `pwd` shell smoke.
- Existing OpenCode processes require restart to load the changed agent definition.

## Review

Unrestricted Bash is deliberate and user-selected. The prompt cannot sandbox the
shell, so governed private bodies stay local, consequential effects retain explicit
confirmation policy, and least-privileged system controls remain authoritative.
