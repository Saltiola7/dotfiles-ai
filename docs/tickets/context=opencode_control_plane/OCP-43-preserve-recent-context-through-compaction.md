---
schema_version: 1
id: "OCP-43"
slug: "preserve-recent-context-through-compaction"
context: "opencode_control_plane"
title: "Preserve recent context through OpenCode compaction"
kind: "task"
state: "done"
priority: "high"
points: null
depends_on: []
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
  - "Rendered JSON, OpenCode parser, focused control-plane tests, and affected-scope QA"
created: "2026-08-29"
updated: "2026-08-29"
completed: "2026-08-29"
commits:
  - "4bb382bf3ae0df1fee6101c6cb3374a04cc8c4b0"
jira_publications: []
migration: null
---

## Outcome

Managed OpenCode sessions retain a substantially larger recent verbatim tail
after automatic compaction while keeping OpenCode's trigger and safety defaults.

## Context

OpenCode otherwise retains at most 15,000 recent tokens verbatim after
compaction, which is small relative to the normal Sol input window and can omit
active reasoning and recent tool evidence.

## Scope

Render `compaction.preserve_recent_tokens` as `65536`. Do not configure `auto`,
`prune`, `tail_turns`, or `reserved`; do not change model routing, reasoning
effort, model metadata, live configuration, or running OpenCode processes.

## Acceptance Criteria

- The rendered managed configuration contains exactly
  `{"preserve_recent_tokens": 65536}` under `compaction`.
- OpenCode's automatic trigger, pruning, turn-count, and reserve defaults remain
  inherited.
- The rendered document is valid JSON and passes the OpenCode parser.
- Focused control-plane tests and affected-scope QA pass.

## Risks

The global budget is optimized for the normal Sol route. Models with smaller
context windows may summarize more aggressively, and content older than the
recent tail remains dependent on compaction summaries or durable artifacts.

## Evidence

- The focused regression failed with `KeyError: 'compaction'` before the managed
  block was added.
- All 44 focused control-plane tests pass.
- Rendered JSON, OpenCode 1.18.25 resolved configuration, canonical validation
  of 178 tickets, and Git whitespace checks pass.
- No managed configuration was applied and no OpenCode process was restarted.

## Review

The diff adds one managed value plus its direct specification and regression
coverage. It deliberately leaves trigger, pruning, turn-count, reserve, model
routing, and live runtime behavior unchanged until a future managed apply.
