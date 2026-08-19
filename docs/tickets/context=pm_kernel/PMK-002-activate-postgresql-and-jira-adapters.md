---
schema_version: 1
id: PMK-002
slug: activate-postgresql-and-jira-adapters
context: pm_kernel
title: Activate PostgreSQL and Jira adapters
kind: story
state: in_progress
priority: high
points: 8
depends_on:
  - PMK-001
relations: []
owns:
  - dot_local/bin/executable_pmctl
  - dot_local/bin/executable_sandbox-vm
  - private_dot_config/containers/systemd
  - docs/specs/pm_kernel
reads:
  - docs/tickets
  - dot_agents/skills/jira-ticket
parallel_safe: false
validation:
  - uv run --group test pytest
  - PostgreSQL backup and restore smoke
  - Jira preview and read-only reconciliation smoke
created: 2026-08-19
updated: 2026-08-19
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Activate the optional PostgreSQL projection and approval-gated Jira adapter while
keeping Git tickets authoritative.

## Context

PMK-001 delivered default-off service definitions and a fake Jira adapter. The
selected personal workspace now needs private host access, recoverable backups,
and bounded ACLI create/update behavior.

## Scope

Owned Lima loopback forwarding, stdin-only Podman secret provisioning,
1Password-backed host access, seven verified weekly dumps, ACLI create/update and
reconciliation receipts, machine-local project mapping, deployment, and runtime
evidence.

## Acceptance Criteria

- PostgreSQL listens on host loopback only and remains rebuildable from Git.
- Password material never enters source, arguments, logs, backups, or reports.
- Every retained dump passes scratch restore verification.
- Jira create/update requires an exact digest confirmation and matching project,
  issue type, publication label, and readback.
- Unknown Jira outcomes block retry until bounded reconciliation.
- Disablement removes runtime access while retaining the recovery volume.

## Evidence

Affected implementation validation passes 116 tests and canonical ticket checks.
Deployment, runtime recovery, and final review evidence remain pending.

## Risks

Prerelease PostgreSQL compatibility, credential leakage, backup loss, ambiguous
external writes, duplicate Jira mutation, and host-forward ownership drift.

## Review

Pending.
