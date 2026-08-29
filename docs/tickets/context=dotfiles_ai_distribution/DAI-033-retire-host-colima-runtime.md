---
schema_version: 1
id: "DAI-033"
slug: "retire-host-colima-runtime"
context: "dotfiles_ai_distribution"
title: "Retire the host Colima runtime"
kind: "chore"
state: "active"
priority: "high"
points: 3
depends_on:
  - "DAI-028"
relations: []
owns:
  - "Current host-runtime contracts, portable guest PATH, Colima deletion, host Docker package removal, tests, deployment, and operation evidence"
reads:
  - "Managed Fedora workspace runtime, Atuin health, host container consumers, historical migration records, and local package state"
parallel_safe: false
validation:
  - "Focused distribution tests, rendered guest profile, live rootless Podman/Compose probes, zero active host consumers, deleted runtime state, absent packages, and healthy Atuin"
created: "2026-08-28"
updated: "2026-08-28"
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Managed Fedora Lima workspaces with rootless Podman become the only supported
local container runtime, and the host Colima VM and Docker toolchain are removed.

## Context

The completed Podman migration retained Colima as a temporary rollback path. A
stale host LaunchAgent restarted that VM, and an idle Camplan database and Redis
stack subsequently used its Docker socket. The managed guest Compose shim also
resolved only by absolute path because its profile rendered the macOS home.

## Scope

- Derive portable user paths from runtime `$HOME`.
- Remove host-runtime fallback guidance from current distribution contracts.
- Preserve truthful completed tickets and changelog history.
- Verify no active Camplan consumer before stopping its idle services.
- Delete all Colima runtime data without backup, as explicitly approved.
- Remove the Colima LaunchAgent, context, state, package, and host Docker tools.

## Acceptance Criteria

- Normal managed guest shells resolve the Podman-backed `docker compose` command.
- Current configuration, operations, behavior, and maintenance contracts name no
  host container fallback; historical records remain unchanged.
- Deletion stops if PostgreSQL, Redis, port, or process probes find a consumer.
- Colima and host Docker tools, state, startup, sockets, and listeners are absent.
- Both managed Fedora workspaces remain healthy with rootless Podman, and Atuin
  remains healthy through host loopback port `8889`.

## Risks

The approved purge permanently deletes every Colima image, container, and volume.
Any consumer appearing after preflight blocks deletion. Lima, Podman, QEMU, and
managed workspace state are outside deletion scope.

## Review

Review must reject deletion before consumer and guest-runtime proof, removal of
historical evidence, changes to `enterprise-seo-tools`, or deletion of managed
Fedora workspace state.
