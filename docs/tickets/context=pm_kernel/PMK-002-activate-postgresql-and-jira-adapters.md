---
schema_version: 1
id: PMK-002
slug: activate-postgresql-and-jira-adapters
context: pm_kernel
title: Activate PostgreSQL and Jira adapters
kind: story
state: done
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
completed: 2026-08-19
commits:
  - "998214e"
  - "79bd60c"
  - "0d5a3fc"
  - "5eadd94"
jira_publications:
  - "pmk-003-private-workflows"
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

Affected validation passed 116 tests and canonical ticket checks. PostgreSQL 19
Beta 3 is healthy in the selected rootless guest, host access listens only on
`127.0.0.1:55432`, and relational plus `GRAPH_TABLE` counts match all 146
projected tickets. A real custom-format backup passed isolated scratch restore,
and its weekly seven-generation LaunchAgent is loaded. Jira authentication,
project/type/ADF reads, and exact preview passed with `written:false`; no Jira
mutation was performed. Independent review ended clean after remediation.

## Risks

Prerelease PostgreSQL compatibility, credential leakage, backup loss, ambiguous
external writes, duplicate Jira mutation, and host-forward ownership drift.

## Review

Accepted. The OpenCode permission source is ready, but its local target retained
unrelated user drift and was not overwritten; reconcile that target before the
next full chezmoi apply. Live Jira create/update remains separately approval-gated.
