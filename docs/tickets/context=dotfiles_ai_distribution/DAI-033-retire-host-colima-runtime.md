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

## Execution Safety

Run the following sequence from the host. Any failed assertion stops retirement.

1. Prove both replacements before changing host state:

   ```sh
   workspace_a=${WORKSPACE_A:?}
   workspace_b=${WORKSPACE_B:?}
   sandbox-vm shell "$workspace_a" -- docker compose version
   sandbox-vm shell "$workspace_a" -- podman info --format '{{.Host.Security.Rootless}}'
   sandbox-vm shell "$workspace_b" -- docker compose version
   sandbox-vm shell "$workspace_b" -- podman info --format '{{.Host.Security.Rootless}}'
   curl -fsS http://127.0.0.1:8889/healthz
   ```

2. Require exactly the known idle Camplan database and Redis containers, no
   external database clients, no Redis client beyond the probe itself, and no
   established host-port connection:

   ```sh
   test "$(docker context show)" = colima
   test "$(docker ps --format '{{.Names}}' | sort)" = "$(printf '%s\n' camplan-consumer-001-db-1 camplan-consumer-001-redis-1 | sort)"
   test "$(docker exec camplan-consumer-001-db-1 psql -U postgres -d enterprise_seo_tools -Atc "select count(*) from pg_stat_activity where pid <> pg_backend_pid() and backend_type = 'client backend'")" = 0
   test "$(docker exec camplan-consumer-001-redis-1 redis-cli --raw client list | wc -l | tr -d ' ')" = 1
   ! lsof -nP -iTCP:5433 -iTCP:6380 -sTCP:ESTABLISHED
   ```

3. Prevent automatic restart, stop the exact project without a volume flag, and
   prove no container remains running:

   ```sh
   launchctl bootout "gui/$(id -u)/dev.dotfiles.colima-atuin"
   camplan_compose=$(docker inspect camplan-consumer-001-db-1 --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}')
   test -f "$camplan_compose"
   docker compose -f "$camplan_compose" -p camplan-consumer-001 down --remove-orphans
   test -z "$(docker ps -q)"
   ```

4. Remove only the host fallback. Both configured managed workspace directories
   must still exist before and after deletion:

   ```sh
   test -d "${LIMA_HOME:?}/${WORKSPACE_INSTANCE_A:?}"
   test -d "$LIMA_HOME/${WORKSPACE_INSTANCE_B:?}"
   docker context use default
   docker context rm colima
   colima delete --data --force
   rm -rf "$LIMA_HOME/colima" "${DOTFILES_AI_STATE_ROOT:?}/colima"
   rm -f "$HOME/.local/bin/start-colima-atuin" "$HOME/Library/LaunchAgents/dev.dotfiles.colima-atuin.plist" "$HOME/Library/Logs/colima-atuin.log"
   brew uninstall colima docker docker-compose docker-buildx docker-credential-helper
   ```

5. Verify no retired process, package, path, context, socket, or listener remains;
   then repeat the replacement and Atuin probes from step 1. The absence of host
   Docker is intentional. Do not remove Lima, Podman, QEMU, or either managed
   workspace.

## Review

Review must reject deletion before consumer and guest-runtime proof, removal of
historical evidence, changes to `enterprise-seo-tools`, or deletion of managed
Fedora workspace state.
