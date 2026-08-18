---
schema_version: 1
id: "OIC-008"
slug: "replaced-lossy-session-attribution-with-reconciled-step-finish-usage-tim"
context: "opencode_inference_cost"
title: "Replaced lossy session attribution with reconciled step-finish usage, timestamped context intervals, and explicit legacy quarantine."
kind: "task"
state: "done"
priority: "historical"
points: null
depends_on: []
relations: []
owns: []
reads: []
parallel_safe: false
validation: []
created: "2026-07-31"
updated: "2026-08-17"
completed: "2026-07-31"
commits:
  - "0315f15"
jira_publications: []
migration: "docs/specs/opencode_inference_cost/BACKLOG.md:25:144991091d9d28ad8ec4db5a38aedcfb20b8a43a6526c0eb3da78c962f1896ff"
---

## Outcome

Replaced lossy session attribution with reconciled step-finish usage, timestamped context intervals, and explicit legacy quarantine.

## Context

Migrated from `docs/specs/opencode_inference_cost/BACKLOG.md` Completed row 25 at `31d6c0c92d3dfd6db93af15f54e3919238ff788f`.

## Scope

Historical completed work.

## Acceptance Criteria

Completion evidence retained from the legacy backlog.

## Evidence

```json
{"commit": "0315f15", "completed": "2026-07-31", "id": "OIC-008", "outcome": "Replaced lossy session attribution with reconciled step-finish usage, timestamped context intervals, and explicit legacy quarantine."}
```

## Risks

Legacy values are preserved without inferred semantics.

## Review

Migrated deterministically; further refinement remains explicit.
