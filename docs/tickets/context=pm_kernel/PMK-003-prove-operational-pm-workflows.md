---
schema_version: 1
id: PMK-003
slug: prove-operational-pm-workflows
context: pm_kernel
title: Prove operational PM workflows
kind: epic
state: done
priority: high
points: 8
depends_on:
  - PMK-002
relations: []
owns:
  - docs/specs/pm_kernel
  - docs/tickets/context=pm_kernel
  - dot_local/bin/executable_pmctl
  - .chezmoitemplates/opencode.json.tmpl
  - private_dot_config/opencode/modify_private_opencode.json
  - private_dot_config/opencode/commands/sprint-review.md
  - dot_local/bin/executable_pm-postgres-backup.tmpl
  - run_onchange_after_configure-pm-postgres.sh.tmpl
  - run_onchange_after_enable-pm-postgres.sh.tmpl
reads:
  - docs/tickets
  - private DBSCTR sanitized-source APIs
  - machine-local Jira and PostgreSQL configuration
  - official PostgreSQL 19 release and upgrade guidance
parallel_safe: false
validation:
  - uv run --group test pytest tests/test_pm_kernel.py tests/test_portable_distribution.py tests/test_opencode_control_plane.py
  - python3 dot_local/bin/executable_pmctl tickets check --root . --json
  - scoped chezmoi diff and apply preserve unrelated OpenCode values and mode
  - personal workspace restart recovers PostgreSQL and exact-head ticket projection
  - logical backup and scratch restore pass before restart
  - exact-digest Jira canary create, readback, receipt, and publication provenance pass
  - approved bounded JQL produces one private factual Sprint Review report
created: 2026-08-19
updated: 2026-08-19
completed: 2026-08-19
commits:
  - "9471ddd"
  - "0c18524"
  - "a2fc4f4"
jira_publications:
  - "pmk-003-private-workflows"
migration: null
---

## Outcome

Prove the remaining PM Kernel journeys against the merged local deployment while
preserving Git authority, machine-local policy, private data, and explicit
external-write approval.

## Context

PMK-002 activated PostgreSQL and the ACLI adapter, but accepted local OpenCode
drift and performed no live Jira mutation. PostgreSQL is healthy and contains 146
ticket payloads, revisions, and graph vertices, but its checkpoint remains at
pre-merge commit `79bd60c`; publication, envelope, and lease tables are empty.
The Sprint Review implementation accepts prepared JSON although its public
contract requires an approved bounded JQL read. PostgreSQL 19 Beta 3 remains the
current prerelease, with GA planned but not yet available.

## Scope

Reconcile the managed PM permission fragment into the existing private OpenCode
target; back up and restart the personal workspace; reproject the exact merged
ticket tree; classify and project available sanitized DBSCTR envelopes; create
complete ticket frontmatter and Markdown evidence bodies in the projection; create
one standalone Jira rollup from exact PMK-001 and PMK-002 revisions after a new
digest confirmation; persist successful publication provenance; implement and
exercise one approved bounded JQL Sprint Review read; and record a safe deferred
PostgreSQL prerelease/GA migration procedure without changing the Beta 3 pin.

## Acceptance Criteria

- OpenCode retains unrelated providers, references, external-directory grants,
  and mode `0600` while PM provisioning and Jira publication commands remain
  approval-gated and broad ACLI mutation remains denied.
- A verified logical backup exists before disruption; workspace and service
  restart retain data, health, loopback-only access, and host authentication.
- Ticket projection advances to the exact PMK-003 committed head and relational,
  revision, relation, checkpoint, and graph counts reconcile with canonical Git.
- Each projected ticket payload contains its validated frontmatter and canonical
  Markdown evidence body; source commit/blob identity still binds the Git authority.
- Every currently available supported sanitized envelope selected through an
  authorized bounded source is validated and projected; unavailable source types
  are reported, not fabricated. Raw transcripts, secrets, and paths remain out.
- Jira preview selects exact committed PMK-001 and PMK-002 blobs and produces one
  deterministic publication label. The live create occurs only after the user
  separately confirms that exact current digest.
- Successful Jira readback, private receipt, PostgreSQL publication rows, and
  canonical ticket publication references agree. Ambiguity blocks retry and uses
  bounded reconciliation.
- One separately approved project-scoped JQL read returns no more than 200 Done
  issues and writes one Git-ignored report with JQL, issue-key, and snapshot
  provenance. No Jira mutation is available through the report path.
- Beta 3 remains pinned. The upgrade procedure cites official guidance and
  requires logical backup, scratch restore, migration check, rollback-preserved
  old cluster, application SQL tests, and a later exact-image approval.
- Affected tests, canonical ticket validation, deployment/operation evidence,
  independent review, and draft-PR delivery readiness pass. Actual draft-PR
  delivery follows gate closure.

## Parallel Execution

- The primary alone owns this ticket, PM specifications, integration, commits,
  external-write confirmation, and final delivery.
- OpenCode lane owns only the OpenCode managed template, its modify source, and
  `tests/test_opencode_control_plane.py`.
- PostgreSQL lane owns only backup/configure/enable templates and
  `tests/test_portable_distribution.py`.
- Jira/report lane serially owns only `dot_local/bin/executable_pmctl`, the Sprint
  Review command, and `tests/test_pm_kernel.py`.
- Release research and runtime inventories are read-only. No two write lanes may
  edit the same path; the primary reconciles their outputs before gate commits.

## Evidence

Affected validation passed 120 tests and canonical ticket checks. Scoped OpenCode
apply preserved unrelated machine-local values and mode `0600` with an empty
post-apply diff. A new logical backup passed checksum and scratch restore before
the personal workspace restarted; the generated Quadlet recovered automatically,
passed health, and remained host-loopback-only. The exact committed projection
contains 147 tickets, current revisions, Markdown bodies, and graph vertices plus
11 relations. Nine sanitized source envelopes record one available cycle source
and eight explicit unavailable identities. One separately confirmed ACLI-test-only
canary passed create, readback, private receipt, PostgreSQL publication/member
projection, and opaque Git provenance. One separately confirmed bounded JQL read
produced a private report over eight completed items with query, key, and snapshot
digests. Beta 3 remains pinned; official major-style migration and rollback steps
are recorded for a later approved image.

## Risks

Unrelated OpenCode policy loss, workspace disruption, stale projection claims,
private Jira leakage, duplicate or ambiguous Jira creation, unsafe query scope,
untrusted report content, and prerelease database incompatibility.

## Review

Accepted. External writes and reads used exact user-confirmed digests; private
deployment identities remain outside portable source. No PostgreSQL image changed.
