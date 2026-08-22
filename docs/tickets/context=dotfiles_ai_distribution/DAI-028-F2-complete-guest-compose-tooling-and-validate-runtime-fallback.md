---
schema_version: 1
id: "DAI-028-F2"
slug: "complete-guest-compose-tooling-and-validate-runtime-fallback"
context: "dotfiles_ai_distribution"
title: "Complete guest Compose tooling and validate runtime fallback"
kind: "task"
state: "active"
priority: "high"
points: null
depends_on:
  - "DAI-028-F1"
relations: []
owns:
  - "Shared Fedora guest package provisioning and Podman/Colima runtime validation"
reads:
  - "enterprise-seo-tools Compose, Make, mounts, health endpoints, and retained runtime state"
parallel_safe: false
validation:
  - "Focused rendering tests, live guest tooling probes, clean Podman image build, five-service operation, named-volume identity, serialized Colima fallback, and restored Podman health"
created: "2026-08-21"
updated: "2026-08-21"
completed: null
commits: []
jira_publications: []
---

## Outcome

Managed Fedora guests provide the complete existing project command surface, and
the enterprise Compose stack is validated on rootless Podman and retained Colima
without deleting persistent data or conflating application defects with runtime
failures.

## Context

DAI-028 deployed rootless Podman, pinned Docker Compose, and a guest `docker`
shim, but the Fedora image omitted `make`. Live investigation also found that
the enterprise project hard-codes container UID/GID defaults, uses a guest-only
dependency path on the host, and intermittently reuses one async Redis health
client across event loops. Those application concerns are outside this ticket.

## Scope

- Install `make` in every newly provisioned managed Fedora guest.
- Repair the exact existing managed guests without recreation.
- Rebuild enterprise application images without cache while retaining volumes.
- Run and inspect all five services under rootless Podman.
- Stop Podman before proving retained Colima build and startup.
- Stop Colima and restore the original Podman service authority.
- Record application-owned portability and health blockers for a separate handoff.

## Acceptance Criteria

- The rendered Fedora template installs both `podman` and `make`.
- Both configured guests report GNU Make and rootless Podman after deployment.
- Podman uses the pinned Compose provider and resolves both declared MGM mounts.
- A no-cache build and `up -d` preserve the named Postgres and Redis volumes.
- Postgres and Redis answer direct health probes, Prefect returns HTTP 200, and
  Vite is reachable; repeated Django health results are recorded truthfully.
- Podman services are stopped before Colima starts, the enterprise stack builds
  and starts with process-local host overrides, and the Colima Atuin service does
  not become authoritative.
- Colima is stopped and Podman is restored with the original named volumes.
- Containers receive neither `OP_SERVICE_ACCOUNT_TOKEN` nor ambient Vertex ADC.

## Risks

- Runtime switching can bind the same host ports from two engines.
- Incorrect Compose flags can delete named data.
- A root package repair must remain exact and cannot widen guest sudo authority.
- Application-owned UID, path, and asynchronous health behavior can fail a
  runtime smoke even when Podman and Colima are healthy.

## Review

Review must distinguish distribution behavior from downstream application
behavior and reject any claim based on one transient HTTP response.
