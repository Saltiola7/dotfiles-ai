---
schema_version: 1
id: "DAI-033"
slug: "retire-host-colima-runtime"
context: "dotfiles_ai_distribution"
title: "Retire the host Colima runtime"
kind: "task"
state: "done"
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
completed: "2026-08-28"
commits:
  - "9d7e750b5e96493696df14f08adc08e726434442"
  - "97ca69fd73f038e9a55ea6c592a25a86b3c8ebae"
  - "564d0337ec0d3a8740f8064f49d1d335e5a05e06"
  - "d021521305aa5d24f9892dd8e3366d18fc634f78"
  - "cc37c05798e6b866062dafc6b0a1a179ecbb2c38"
  - "205b620282d33a951bf57d2d2299c5d24af08966"
  - "0e8cfa33b2d8b0b16a88142203d9bf1521090200"
  - "80ccdd8d90ddd3a6520ac21042f321e1a159292c"
  - "9feb34d6cc611c0b5a0e7c4f85ca663c535b8fa9"
  - "e00ad538b488ce2650c3b5282201f6d8573c83c3"
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

## Evidence

- All 78 focused distribution and Lima tests, Ruff, ticket validation, and Git
  whitespace checks passed. Independent review found no remaining issue.
- Both configured guests resolved `docker compose` through runtime `$HOME`,
  reported Docker Compose v2.40.3 and rootless Podman `true`, and remained running.
- Immediately before teardown, only the expected Camplan database and Redis
  containers ran; PostgreSQL had zero client backends, Redis had only the probe
  client, and no process, scheduler, cron, or established port connection existed.
- The restart agent was disabled before the probes were repeated. The exact
  Compose project stopped cleanly with no volume flag, then all runtime data was
  deleted under the approved no-backup policy. The final gate found the
  plist-less job still cached with its old Colima process; an explicit `bootout`
  removed both before the gate was repeated.
- The host profile, context, startup artifacts, state paths, Docker CLI, Compose,
  Buildx, and credential helper are absent. Ports 5433, 6380, and 8888 have no
  listener; authoritative Atuin health on port 8889 remains healthy. The final
  expanded gate also found and removed inactive legacy state at `~/.colima`.
- Homebrew unexpectedly autoremoved Lima 2.2.0 and `usage` 6.1.0 with Colima.
  Lima 2.2.0 was restored immediately; `usage` was restored at current 6.5.0.
  Podman 6.1.0 and QEMU 11.1.0 remained installed.

## Execution Safety

Run the following as one strict-mode shell after setting the four workspace
variables from machine-local configuration. Any failed assertion stops the
sequence. An unexpected process, scheduler, container, client, path, or root is
an abort condition.

```sh
set -euo pipefail
: "${WORKSPACE_A:?}" "${WORKSPACE_B:?}"
: "${WORKSPACE_INSTANCE_A:?}" "${WORKSPACE_INSTANCE_B:?}"
: "${LIMA_HOME:?}" "${DOTFILES_AI_STATE_ROOT:?}"

abort() { printf 'retirement blocked: %s\n' "$1" >&2; exit 1; }
replacement_probes() {
    sandbox-vm shell "$WORKSPACE_A" -- docker compose version
    test "$(sandbox-vm shell "$WORKSPACE_A" -- podman info --format '{{.Host.Security.Rootless}}')" = true
    sandbox-vm shell "$WORKSPACE_B" -- docker compose version
    test "$(sandbox-vm shell "$WORKSPACE_B" -- podman info --format '{{.Host.Security.Rootless}}')" = true
    test "$(curl -fsS http://127.0.0.1:8889/healthz)" = '{"status":"healthy"}'
}
consumer_probes() {
    test "$(docker context show)" = colima
    expected=$(printf '%s\n' camplan-consumer-001-db-1 camplan-consumer-001-redis-1 | sort)
    test "$(docker ps --format '{{.Names}}' | sort)" = "$expected"
    clients=$(docker exec camplan-consumer-001-db-1 psql -U postgres \
        -d enterprise_seo_tools -Atc \
        "select count(*) from pg_stat_activity where pid <> pg_backend_pid() and backend_type = 'client backend'")
    test "$clients" = 0
    test "$(docker exec camplan-consumer-001-redis-1 redis-cli --raw client list | wc -l | tr -d ' ')" = 1
    ! lsof -nP -iTCP:5433 -iTCP:6380 -sTCP:ESTABLISHED
}

lima_home=$(cd "$LIMA_HOME" && pwd -P)
state_root=$(cd "$DOTFILES_AI_STATE_ROOT" && pwd -P)
test "$lima_home" != / && test "$state_root" != /
test "$lima_home" != "$HOME" && test "$state_root" != "$HOME"
test -f "$state_root/.dotfiles-ai-state"
colima_vm="$lima_home/colima"
colima_state="$state_root/colima"
protected_a="$lima_home/$WORKSPACE_INSTANCE_A"
protected_b="$lima_home/$WORKSPACE_INSTANCE_B"
test -d "$protected_a" && test -d "$protected_b"
for protected in "$protected_a" "$protected_b"; do
    case "$colima_vm" in "$protected"|"$protected"/*) abort "overlapping Lima path" ;; esac
    case "$colima_state" in "$protected"|"$protected"/*) abort "overlapping state path" ;; esac
done

replacement_probes
consumer_probes
pgrep -af '[C]AMPLAN-CONSUMER-001|[c]amplan-consumer-001' && abort "Camplan process found"
launchctl list | grep -qi camplan && abort "Camplan LaunchAgent found"
crontab -l 2>/dev/null | grep -qi camplan && abort "Camplan cron found"

launchctl disable "gui/$(id -u)/dev.dotfiles.colima-atuin"
launchctl print-disabled "gui/$(id -u)" | grep -q '"dev.dotfiles.colima-atuin" => true'
consumer_probes
pgrep -af '[C]AMPLAN-CONSUMER-001|[c]amplan-consumer-001' && abort "Camplan process found"
launchctl list | grep -qi camplan && abort "Camplan LaunchAgent found"
crontab -l 2>/dev/null | grep -qi camplan && abort "Camplan cron found"
camplan_compose=$(docker inspect camplan-consumer-001-db-1 \
    --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}')
test -f "$camplan_compose"
docker compose -f "$camplan_compose" -p camplan-consumer-001 down --remove-orphans
test -z "$(docker ps -q)"
if launchctl print "gui/$(id -u)/dev.dotfiles.colima-atuin" >/dev/null 2>&1; then
    launchctl bootout "gui/$(id -u)/dev.dotfiles.colima-atuin"
fi

docker context use default
colima delete --data --force
if docker context inspect colima >/dev/null 2>&1; then docker context rm colima; fi
! docker context inspect colima >/dev/null 2>&1
rm -rf "$colima_vm" "$colima_state" "$HOME/.colima"
rm -f "$HOME/.local/bin/start-colima-atuin" \
    "$HOME/Library/LaunchAgents/dev.dotfiles.colima-atuin.plist" \
    "$HOME/Library/Logs/colima-atuin.log"
HOMEBREW_NO_AUTOREMOVE=1 brew uninstall \
    colima docker docker-compose docker-buildx docker-credential-helper

! launchctl print "gui/$(id -u)/dev.dotfiles.colima-atuin" >/dev/null 2>&1
! pgrep -x colima
test ! -e "$colima_vm" && test ! -e "$colima_state"
test ! -e "$HOME/.local/bin/start-colima-atuin"
test ! -e "$HOME/Library/LaunchAgents/dev.dotfiles.colima-atuin.plist"
test ! -S /var/run/docker.sock && test ! -e "$HOME/.colima"
test ! -e "$HOME/.docker/cli-plugins/docker-compose"
! command -v colima && ! command -v docker && ! command -v docker-compose
! command -v docker-buildx && ! command -v docker-credential-osxkeychain
for formula in colima docker docker-compose docker-buildx docker-credential-helper; do
    ! brew list --formula "$formula" >/dev/null 2>&1
done
! limactl list --json | grep -q '"name":"colima"'
! lsof -nP -iTCP:5433 -iTCP:6380 -iTCP:8888 -sTCP:LISTEN
test -d "$protected_a" && test -d "$protected_b"
brew list --versions lima podman qemu usage
replacement_probes
```

The absence of host Docker is intentional. Do not remove Lima, Podman, QEMU, or
either managed workspace.

## Review

Review must reject deletion before consumer and guest-runtime proof, removal of
historical evidence, changes to `enterprise-seo-tools`, or deletion of managed
Fedora workspace state.
