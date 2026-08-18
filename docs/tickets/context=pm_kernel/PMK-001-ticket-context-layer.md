---
schema_version: 1
id: PMK-001
slug: ticket-context-layer
context: pm_kernel
title: Build the canonical ticket context layer and PM kernel
kind: epic
state: in_progress
priority: high
points: 8
depends_on: []
relations: []
owns:
  - docs/tickets
  - docs/specs/pm_kernel
  - dot_local/bin/executable_pmctl
reads:
  - docs/specs
  - dot_agents/skills/jira-ticket
parallel_safe: false
validation:
  - uv run --group test pytest
created: 2026-08-18
updated: 2026-08-18
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Replace table backlogs with independently readable local tickets, add an
evidence-gated PM workflow, and provide optional Jira and PostgreSQL projections.

## Context

Discovery, lifecycle audit, and Hermes currently depend on one rigid
`BACKLOG.md` table per bounded context. The format is hard for agents to enrich
and cannot represent Jira rollups or structured provenance without becoming
unreadable.

## Scope

Ticket schema and CLI; deterministic migration; Discovery, audit, Hermes, and
template cutover; PM and migration skills; Jira preview/publish adapter contract;
Sprint Review report contract; optional PostgreSQL 19 service and projection.

## Acceptance Criteria

- Every legacy Active and Completed row has exactly one traceable ticket file.
- No current lifecycle consumer requires `BACKLOG.md`.
- Ticket checks reject malformed identity, state, relations, and completion.
- Jira writes require an exact preview digest and explicit confirmation.
- PostgreSQL remains optional and rebuildable from canonical/sanitized sources.
- Affected QA, managed deployment, runtime smoke, review, and draft-PR delivery pass.

## Evidence

Pending implementation and gate evidence.

## Risks

Data-loss during migration, duplicate authority, private Jira leakage, ambiguous
external writes, and PostgreSQL beta incompatibility.

## Review

Pending.
