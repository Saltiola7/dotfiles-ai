---
schema_version: 1
id: "DAI-028"
slug: "make-lima-the-primary-podman-development-runtime"
context: "dotfiles_ai_distribution"
title: "Make Lima the rootless Podman development runtime"
kind: "task"
state: "done"
priority: "high"
points: null
depends_on:
  - "DAI-024"
  - "DAI-027"
relations: []
owns:
  - "Guest Podman/Compose tooling, Docker shim, in-memory 1Password forwarding, guest Vertex profile, migration docs and tests"
reads:
  - "Existing Lima controller, host Keychain selectors, portable auth helpers, enterprise Compose contract"
parallel_safe: false
validation:
  - "60 focused tests; both guest runtime/auth probes; 14 locally migrated development-vault references awaiting owning-repository delivery; valid isolated ADC and live Claude Vertex response; five-service enterprise Compose smoke"
created: "2026-08-17"
updated: "2026-08-18"
completed: "2026-08-17"
commits:
  - "9056a17"
jira_publications: []
migration: "docs/specs/dotfiles_ai_distribution/BACKLOG.md:7:4858c4bc9c38368d6daff84d0d2fc15253482c86d7bf983e5caf5f9676dd1245"
---

## Outcome

Make Lima the primary Podman development runtime

## Context

Migrated from `docs/specs/dotfiles_ai_distribution/BACKLOG.md` Active row 7 at `31d6c0c92d3dfd6db93af15f54e3919238ff788f`.

## Scope

Runtime, credential boundary, and live two-workspace deployment share one controller and must be serialized

## Acceptance Criteria

60 focused tests; both guest runtime/auth probes; 14 locally migrated development-vault references awaiting owning-repository delivery; valid isolated ADC and live Claude Vertex response; five-service enterprise Compose smoke

## Evidence

```json
{"depends_on": "DAI-024, DAI-027", "effort": "L", "id": "DAI-028", "owns": "Guest Podman/Compose tooling, Docker shim, in-memory 1Password forwarding, guest Vertex profile, migration docs and tests", "parallel_safe": "no", "priority": "high", "reads": "Existing Lima controller, host Keychain selectors, portable auth helpers, enterprise Compose contract", "reason": "Runtime, credential boundary, and live two-workspace deployment share one controller and must be serialized", "status": "active", "title": "Make Lima the primary Podman development runtime", "validation": "60 focused tests; both guest runtime/auth probes; 14 locally migrated development-vault references awaiting owning-repository delivery; valid isolated ADC and live Claude Vertex response; five-service enterprise Compose smoke"}
```

Upstream reconciliation records merge commit `9056a17` and completed rollout
evidence through DAI-028 closure commit `ef45768`.

## Risks

Legacy values are preserved without inferred semantics.

## Review

Completed upstream and reconciled into the canonical ticket during PMK-001.
