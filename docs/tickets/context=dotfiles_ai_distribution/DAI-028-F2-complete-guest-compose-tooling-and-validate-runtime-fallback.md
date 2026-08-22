---
schema_version: 1
id: "DAI-028-F2"
slug: "complete-guest-compose-tooling-and-validate-runtime-fallback"
context: "dotfiles_ai_distribution"
title: "Complete guest Compose tooling and validate runtime fallback"
kind: "task"
state: "done"
priority: "historical"
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
completed: "2026-08-21"
commits:
  - "74daa67"
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
- Podman uses the pinned Compose provider and resolves both declared project mounts.
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

## Evidence

- Both managed Fedora guests report GNU Make 4.4.1, rootless Podman, and Docker
  Compose v2.40.3 after the exact idempotent package repair.
- The enterprise stack completed no-cache Podman and Colima builds. All five
  services started under each runtime; Postgres accepted connections, Redis
  returned `PONG`, Prefect returned HTTP 200, and Vite returned HTTP 302.
- Podman volume creation times remained
  `2026-08-14 18:50:44.605414689 -0600 CST` for Postgres and
  `2026-08-14 18:50:44.616470298 -0600 CST` for Redis across rebuild, fallback,
  and restoration. Retained Colima volumes likewise kept their original
  `2026-08-11T12:27:06-06:00` creation time.
- Both Podman guests were stopped before Colima started. Colima was stopped
  before both guests restarted; the personal Atuin service returned active and
  its authoritative host `/healthz` returned healthy after restoration.
- No running enterprise container mapped `OP_SERVICE_ACCOUNT_TOKEN`,
  `GOOGLE_APPLICATION_CREDENTIALS`, or
  `CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE`.
- Repeated Django health probes alternated HTTP 200/500 on Podman and returned
  HTTP 500 on Colima because the application reuses one module-level async Redis
  client across event loops. The first Colima build also exposed the downstream
  Dockerfile's collision with macOS GID 20; process-local `MY_GID=1000` proved
  the retained runtime fallback without changing application source.
