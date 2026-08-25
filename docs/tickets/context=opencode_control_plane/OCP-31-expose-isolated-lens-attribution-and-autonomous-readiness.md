---
schema_version: 1
id: "OCP-31"
slug: "expose-isolated-lens-attribution-and-autonomous-readiness"
context: "opencode_control_plane"
title: "Expose isolated lens attribution and autonomous readiness"
kind: "task"
state: "done"
priority: "high"
points: null
depends_on:
  - "DAI-021"
relations: []
owns:
  - "Worker command, typed autonomous transition, federation candidate classification, lens-audit skill"
reads:
  - "Improvement ledger, federated history, DBSCTR delivery"
parallel_safe: false
validation:
  - "Command contract, adapter validation, transition tests, parser and affected QA"
created: "2026-08-17"
updated: "2026-08-25"
completed: "2026-08-02"
commits:
  - "560650d8"
  - "784d646d"
jira_publications: []
migration: "docs/specs/opencode_control_plane/BACKLOG.md:8:f13acbbacf124628d2bcbcdeb1333e3df7de093a543fe3e212054afd051bda65"
---

## Outcome

Expose isolated lens attribution and autonomous readiness

## Context

Migrated from `docs/specs/opencode_control_plane/BACKLOG.md` Active row 8 at `31d6c0c92d3dfd6db93af15f54e3919238ff788f`.

## Scope

Continuous workers need one-lens scope and deterministic review-session exclusion

## Acceptance Criteria

Command contract, adapter validation, transition tests, parser and affected QA

## Evidence

```json
{"depends_on": "DAI-021", "effort": "M", "id": "OCP-31", "owns": "Worker command, typed autonomous transition, federation candidate classification, lens-audit skill", "parallel_safe": "no", "priority": "high", "reads": "Improvement ledger, federated history, DBSCTR delivery", "reason": "Continuous workers need one-lens scope and deterministic review-session exclusion", "status": "in_progress", "title": "Expose isolated lens attribution and autonomous readiness", "validation": "Command contract, adapter validation, transition tests, parser and affected QA"}
```

## Risks

Legacy values are preserved without inferred semantics.

## Review

Reconciled against the delivered one-lens worker, readiness, attribution, and
linked-worktree evidence retained in the control-plane changelog and source.
