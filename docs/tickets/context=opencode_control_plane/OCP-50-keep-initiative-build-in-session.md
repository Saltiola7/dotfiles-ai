---
schema_version: 1
id: "OCP-50"
slug: "keep-initiative-build-in-session"
context: "opencode_control_plane"
title: "Keep Build-led Initiative work in the current session"
kind: "task"
state: "in_progress"
priority: "high"
points: null
depends_on: []
relations: []
owns:
  - ".chezmoitemplates/opencode.json.tmpl"
  - "private_dot_config/opencode/tools/dbsctr.ts"
  - "private_dot_config/opencode/lib/dbsctr-runtime.ts"
  - "private_dot_config/opencode/agents/build-gpt.md"
  - "private_dot_config/opencode/agents/build-claude.md"
  - "private_dot_config/opencode/AGENTS.md"
  - "dot_agents/skills/discovery/SKILL.md"
  - "dot_agents/skills/dbsctr/SKILL.md"
  - "docs/specs/opencode_control_plane/README.md"
  - "docs/specs/opencode_control_plane/features/initiative-launch-atomicity.md"
  - "docs/specs/opencode_control_plane/CHANGELOG.md"
  - "tests/test_opencode_control_plane.py"
  - "tests/test_dbsctr_lifecycle.py"
reads:
  - "docs/specs/opencode_control_plane/PROFILE.md"
parallel_safe: false
validation:
  - "Focused and affected control-plane/lifecycle pytest, independent boundary review, rendered permissions, and targeted deployment smoke"
created: "2026-08-31"
updated: "2026-08-31"
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Build-led Discovery begins an approved Initiative slice in its current
same-repository OpenCode session. Only Discovery Coordinator may create the
isolated Herdr child session.

## Acceptance Criteria

- Native Build, Build-GPT, and Build-Claude deny `dbsctr_initiative_launch` and
  ask only for explicit Initiative Begin.
- Discovery Coordinator retains child launch; Plan and subagents deny both paths.
- Initiative Begin preserves fresh receipt, cycle availability, repository,
  protected branch, plan digest, ownership, and post-approval mutation checks.
- Initiative Begin attaches the current runtime and emits no Herdr command.
- Ordinary Begin remains prompt-free.

## Evidence

- Pending.
