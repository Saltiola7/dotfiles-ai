---
schema_version: 1
id: "DAI-030"
slug: "managed-runtime-parity-handoff"
context: "dotfiles_ai_distribution"
title: "Enforce managed OpenCode parity for VM handoff"
kind: "bug"
state: "done"
priority: "high"
points: 3
depends_on:
  - "DAI-029"
relations:
  - "related:OCP-26"
owns:
  - "Managed guest OpenCode pin, repair/update commands, VM handoff identity, tests, deployment, and operation evidence"
reads:
  - "Host Homebrew OpenCode version, Lima instance provisions, configured workspace order, and typed handoff contract"
parallel_safe: false
validation:
  - "Focused sandbox/control-plane tests, rendered Lima validation, exact host/guest version probes, live two-workspace update, and handoff smoke"
created: "2026-08-25"
updated: "2026-08-25"
completed: "2026-08-25"
commits:
  - "796096117787858d23d89510aba6b9e086c6eee3"
  - "57b138cdaa3fda14339f091ff62eac03836ddbb0"
jira_publications: []
migration: null
---

## Outcome

Managed host and guest OpenCode runtimes advance through one checksum-pinned
update path, and typed VM handoff launches through a valid lowercase Herdr agent.

## Context

The host advanced beyond the guest template's pinned OpenCode 1.18.4. That guest
parsed the managed interactive `run` invocation through an incompatible command
surface, while Herdr rejected the uppercase `DBSCTR Handoff` agent identity.

## Scope

- Make the current host OpenCode version and its Linux arm64 release digest authoritative once.
- Repair existing root-owned guest binaries without recreating VMs or widening sudo.
- Add one ordered all-workspace update command that restores prior VM states.
- Preserve hard-coded Build authority and use a valid lowercase Herdr identity.
- Deploy and verify both configured workspaces after source delivery is safe.

## Acceptance Criteria

- New and existing guests install the exact managed OpenCode release only after
  SHA-256 verification and atomic replacement.
- Single-workspace update fails closed on host or guest version mismatch.
- `sandbox-vm update-all` updates every configured workspace and restores mixed
  running/stopped states.
- Existing guest Chezmoi state accepts the regenerated explicit guest machine type.
- Handoff uses `dbsctr-handoff` and `run --agent build --interactive`; callers
  cannot select another agent.
- Focused tests, rendered template validation, live parity probes, and an approved
  handoff smoke pass without exposing credentials or changing mounted data.

## Evidence

The parity and lowercase-agent regression checks failed before implementation and
passed after the minimum managed-provision and adapter changes. All 97 affected
tests passed. The checksum-pinned 1.18.23 runtime deployed to both configured
guests; exact parity, interactive Build argv parsing, state restoration, and
zero targeted host drift passed without model inference.

## Risks

System provisioning restarts a VM when repair is required. Failure must restore
its prior state, and checksum or version ambiguity must stop before user updates.

## Review

Review must reject ambient latest-version downloads, caller-controlled agent
selection, guest sudo expansion, VM recreation, and false parity based on wrappers.
