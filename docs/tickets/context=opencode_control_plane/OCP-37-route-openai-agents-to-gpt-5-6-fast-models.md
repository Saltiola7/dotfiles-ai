---
schema_version: 1
id: "OCP-37"
slug: "route-openai-agents-to-gpt-5-6-fast-models"
context: "opencode_control_plane"
title: "Route OpenAI agents to GPT-5.6 Fast models"
kind: "task"
state: "active"
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
  - "Rendered config, focused control-plane tests, live resolved models, and restart guidance pass"
created: "2026-08-22"
updated: "2026-08-22"
completed: null
commits: []
jira_publications: []
---

## Outcome

Use GPT-5.6 Sol Fast for OpenAI primary and review work, Luna Fast for exploration
and disposable small-model work, and Terra Fast for scouting and bounded builds.

## Acceptance Criteria

- Native Plan, native Build, `build-gpt`, Reviewer, and `/dbsctr-gpt` resolve to Sol Fast at medium effort.
- Explore resolves to Luna Fast at low effort; Scout and Builder resolve to Terra Fast at medium effort.
- Provider affinity, permissions, reasoning effort, and Claude routing remain unchanged.
- Managed deployment resolves the exact Fast model identities and documents the required OpenCode restart.

## Risks

Fast identities use OpenAI priority processing and published rates are twice the
standard token rates. Existing cost-report estimates do not yet include Fast IDs.
