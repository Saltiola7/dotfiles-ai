---
schema_version: 1
id: "OCP-37"
slug: "route-openai-agents-to-gpt-5-6-fast-models"
context: "opencode_control_plane"
title: "Route OpenAI agents to GPT-5.6 Fast models"
kind: "task"
state: "done"
priority: "high"
points: null
depends_on:
  - "OCP-33"
relations: []
owns:
  - "Managed OpenAI primary, subagent, command, default, tests, deployment, and restart evidence"
reads:
  - "OpenCode model registry and existing provider-affine routing contract"
parallel_safe: false
validation:
  - "Rendered config, 53 focused tests, targeted deployment, live resolved models, and restart guidance pass"
created: "2026-08-22"
updated: "2026-08-25"
completed: "2026-08-22"
commits:
  - "d49c9b48359f715de04b3fac470d7d2f5287a5f0"
jira_publications: []
migration: null
---

## Outcome

Use GPT-5.6 Sol Fast for OpenAI primary and review work, Luna Fast for exploration
and disposable small-model work, and Terra Fast for scouting and bounded builds.

## Context

OpenAI-affine agents previously used standard GPT-5.6 identities rather than the
configured priority-processing variants.

## Scope

Update only managed OpenAI model identities and their focused routing evidence;
preserve provider affinity, permissions, and Claude routes.

## Acceptance Criteria

- Native Plan, native Build, `build-gpt`, Reviewer, and `/dbsctr-gpt` resolve to Sol Fast at medium effort.
- Explore resolves to Luna Fast at low effort; Scout and Builder resolve to Terra Fast at medium effort.
- Provider affinity, permissions, reasoning effort, and Claude routing remain unchanged.
- Managed deployment resolves the exact Fast model identities and documents the required OpenCode restart.

## Risks

Fast identities use OpenAI priority processing and published rates are twice the
standard token rates. Existing cost-report estimates do not yet include Fast IDs.

## Evidence

- The routing regression check failed on four old-ID paths before implementation.
- `uv run --group test pytest -q tests/test_opencode_control_plane.py tests/test_portable_distribution.py`: 53 passed.
- Targeted `chezmoi` deployment produced no remaining diff for managed OpenCode routing targets.
- Fresh `opencode debug config` and `opencode debug agent` calls resolved the exact Fast identities and preserved efforts.

## Review

Focused tests and deployed model-resolution checks passed with no routing changes
outside the owned OpenAI identities.
