---
schema_version: 1
id: "OCP-45"
slug: "correct-sol-context-metadata"
context: "opencode_control_plane"
title: "Correct GPT-5.6 Sol context metadata"
kind: "task"
state: "in_progress"
priority: "high"
points: null
depends_on:
  - "OCP-43"
relations: []
owns:
  - ".chezmoitemplates/opencode.json.tmpl"
  - "docs/specs/opencode_control_plane/README.md"
  - "docs/specs/opencode_control_plane/CHANGELOG.md"
  - "tests/test_opencode_control_plane.py"
reads:
  - "docs/specs/opencode_control_plane/PROFILE.md"
parallel_safe: false
validation:
  - "Rendered JSON, resolved Sol model metadata, focused control-plane tests, targeted deployment smoke, and affected-scope QA"
created: "2026-08-29"
updated: "2026-08-29"
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Managed OpenCode base and Fast GPT-5.6 Sol routes use the provider's current
input and output partition instead of stale catalog limits, delaying automatic
compaction while retaining the existing recent verbatim tail.

## Context

OpenCode 1.18.25 currently resolves both Sol routes to 400,000 context, 272,000
input, and 128,000 output tokens. Its inherited 20,000-token reserve therefore
starts automatic compaction near 252,000 input tokens despite GPT-5.6 Sol
supporting a 1,050,000-token context with up to 922,000 input tokens.

## Acceptance Criteria

- Base and Fast GPT-5.6 Sol render and resolve context `1050000`, input `922000`,
  and output `128000`.
- `compaction` remains exactly `{"preserve_recent_tokens": 65536}` and no
  explicit reserve, trigger, pruning, or turn-count value is introduced.
- Model routing, priority processing, and reasoning variants remain unchanged.
- The targeted managed apply changes only reviewed OpenCode configuration, and
  a restarted runtime resolves the corrected limits.

## Risks

Sessions can consume substantially more input before compaction, increasing
latency and premium long-context token cost. Provider limit reductions require
updating or retiring the override before affected requests are sent.
