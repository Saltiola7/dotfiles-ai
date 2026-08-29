# Atuin Podman Operations

The selected personal Fedora workspace runs Atuin as a rootless Podman Quadlet.
The public tailnet URL remains unchanged: macOS Tailscale Serve forwards it to
host loopback port `8889`, and Lima forwards that port to guest loopback `8888`.
SQLite stays in the guest's `atuin-data` named volume, never a VirtioFS mount.

## Configure

Set `atuin_workspace` to the personal workspace name in machine-local TOML,
render and validate both workspaces, then apply the stored port forward to the
existing selected instance:

```sh
sandbox-vm validate workspace1
sandbox-vm validate workspace2
sandbox-vm update workspace1
sandbox-vm configure-atuin
sandbox-vm shell workspace1 -- systemctl --user is-active atuin.service
curl -fsS http://127.0.0.1:8889/healthz
```

The selected VM is stopped only while `limactl edit` applies the source-owned
port forward, then restored to its prior running state. An edit failure also
restarts a previously running VM with its prior configuration. A guarded
LaunchAgent supplies the configured external `LIMA_HOME`; Lima's generated
autostart plist cannot represent that non-default home.

## Operate

The selected workspace is the only Atuin server authority. Verify its service,
host forwarding, and Tailscale backend without exposing account data:

```sh
tailscale serve --bg --https=443 http://127.0.0.1:8889
tailscale serve status
```

Verify closed registration after guest or Tailscale changes. Restart the selected
workspace and recheck host and tailnet health before declaring recovery complete.

Before selecting a different Atuin workspace, first clear `atuin_workspace` and
apply this source. Managed reconciliation disables the former guest service,
removes its exact owned forward and unit definitions, preserves its named volume
and prior VM running state, and unloads/removes host startup. Only then select and apply the new workspace. This prevents two
instances from claiming host port `8889`.

## Retire

Before retiring the selected workspace, complete client sync, stop Atuin, export
the stopped `atuin-data` Podman volume when retention is required, remove the
owned host forwarding, and verify the tailnet endpoint no longer routes to it.
Clients retain locally captured records while the service is unavailable and
reconcile after a replacement authority is healthy.
