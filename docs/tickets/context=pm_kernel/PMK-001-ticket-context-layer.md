---
schema_version: 1
id: PMK-001
slug: ticket-context-layer
context: pm_kernel
title: Build the canonical ticket context layer and PM kernel
kind: epic
state: done
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
completed: 2026-08-18
commits:
  - "31d6c0c"
  - "7a43c51"
  - "b872a08"
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

Migration produced 143 traceable legacy tickets plus this PM cycle ticket. The
complete suite passed 339 tests with one expected skip before review remediation;
focused final evidence passed 23 PM/distribution tests. Deployed source identity,
chezmoi idempotence, OpenCode command resolution, 144-ticket validation, and the
typed fixed-commit audit passed with zero findings. Independent review ended with
no material findings.

## Risks

Data-loss during migration, duplicate authority, private Jira leakage, ambiguous
external writes, and PostgreSQL beta incompatibility.

## Review

Accepted. Jira remains fake-only until a machine-local project mapping and
explicit publication confirmation are supplied. PostgreSQL remains disabled
until an exact PostgreSQL 19 beta image digest and workspace are configured.
