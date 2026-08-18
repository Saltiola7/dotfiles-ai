---
schema_version: 1
id: "OIC-007"
slug: "join-governed-outcome-values-for-roi-reporting"
context: "opencode_inference_cost"
title: "Join governed outcome values for ROI reporting"
kind: "task"
state: "intake"
priority: "P2"
points: null
depends_on:
  - "OIC-005"
relations: []
owns:
  - "Future cycle; ownership not assigned"
reads:
  - "separately governed benefit source"
parallel_safe: false
validation:
  - "Separate discovery and authority contract."
created: "2026-08-17"
updated: "2026-08-17"
completed: null
commits: []
jira_publications: []
migration: "docs/specs/opencode_inference_cost/BACKLOG.md:11:fdebb17bf76f61ffedd47efdbdd14065f75e878f0c867b8f94e9f2a45d131ca6"
---

## Outcome

Join governed outcome values for ROI reporting

## Context

Migrated from `docs/specs/opencode_inference_cost/BACKLOG.md` Active row 11 at `31d6c0c92d3dfd6db93af15f54e3919238ff788f`.

## Scope

Cost alone is not ROI and benefit semantics require another bounded context.

## Acceptance Criteria

Separate discovery and authority contract.

## Evidence

```json
{"depends_on": "OIC-005", "effort": "L", "id": "OIC-007", "owns": "Future cycle; ownership not assigned", "parallel_safe": "false", "priority": "P2", "reads": "separately governed benefit source", "reason": "Cost alone is not ROI and benefit semantics require another bounded context.", "status": "pending", "title": "Join governed outcome values for ROI reporting", "validation": "Separate discovery and authority contract."}
```

## Risks

Legacy values are preserved without inferred semantics.

## Review

Migrated deterministically; further refinement remains explicit.
