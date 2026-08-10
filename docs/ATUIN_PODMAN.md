# Atuin Podman Migration

The selected personal Fedora workspace runs Atuin as a rootless Podman Quadlet.
The public tailnet URL remains unchanged: macOS Tailscale Serve forwards it to
host loopback port `8889`, and Lima forwards that port to guest loopback `8888`.
SQLite stays in the guest's `atuin-data` named volume, never a VirtioFS mount.

## Prepare

Set `atuin_workspace` to the personal workspace name in machine-local TOML,
render and validate both workspaces, then apply the stored port forward to the
existing selected instance:

```sh
sandbox-vm validate personal
sandbox-vm validate mgm
sandbox-vm update personal
sandbox-vm configure-atuin
sandbox-vm shell personal -- systemctl --user is-active atuin.service
curl -fsS http://127.0.0.1:8889/healthz
```

The selected VM is stopped only while `limactl edit` applies the source-owned
port forward, then restored to its prior running state. An edit failure also
restarts a previously running VM with its prior configuration.

## Cold Cutover

Clients do not dual-write. Complete a final sync first, then keep the Colima
container stopped until rollback or retirement. Choose a new dated archive path
outside Git and preserve its checksum.

```sh
stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup="/Volumes/ext/archive/atuin-colima-final-$stamp.tgz"
test ! -e "$backup" && test ! -e "$backup.sha256"
docker compose -f ~/.config/atuin-server/compose.yaml stop
docker run --rm --entrypoint sh \
  -v atuin-server_atuin-data:/config:ro \
  -v /Volumes/ext/archive:/backup \
  -e BACKUP_FILE="$(basename "$backup")" \
  ghcr.io/atuinsh/atuin:18.17.1@sha256:b2567e0d80a5622dba8d6c5319b198a94ef5166003c2559b91a5406ac688aac7 \
  -c 'tar -czf "/backup/$BACKUP_FILE" -C /config .'
shasum -a 256 "$backup" > "$backup.sha256"
shasum -a 256 -c "$backup.sha256"
sandbox-vm shell personal -- systemctl --user stop atuin.service
sandbox-vm shell personal -- podman volume rm atuin-data
sandbox-vm shell personal -- podman volume create atuin-data
sandbox-vm shell personal -- podman volume import atuin-data - < "$backup"
sandbox-vm shell personal -- systemctl --user start atuin.service
curl -fsS http://127.0.0.1:8889/healthz
```

Abort before switching ingress if import, health, authentication, representative
decryption, or Mac/personal/MGM sync fails. After those pass, move only the
Tailscale backend:

```sh
tailscale serve --bg --https=443 http://127.0.0.1:8889
tailscale serve status
```

Verify closed registration, restart `personal-sandbox`, recheck host and tailnet
health, and take a stopped Podman volume export. Retain the Colima profile,
Compose file, original named volume, final archive, and checksum during the
confidence period.

Before selecting a different Atuin workspace, first clear `atuin_workspace` and
apply this source. Managed reconciliation disables the former guest service,
removes its owned forward, preserves its prior VM running state, and unloads host
startup. Only then select and apply the new workspace. This prevents two
instances from claiming host port `8889`.

## Roll Back

```sh
tailscale serve --bg --https=443 http://127.0.0.1:8888
sandbox-vm shell personal -- systemctl --user stop atuin.service
colima start
docker compose -f ~/.config/atuin-server/compose.yaml start
curl -fsS http://127.0.0.1:8888/healthz
```

Clients retain records captured while either server is unavailable and reconcile
after service returns. Never start both stores behind the production endpoint.
Before a later Colima retirement, take another cold Podman export and separately
verify that no project still requires the host Docker socket.
