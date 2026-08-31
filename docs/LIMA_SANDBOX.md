# Lima Workspaces

`sandbox-vm` manages locally named Fedora workspaces from
`~/.config/dotfiles-ai/chezmoi.toml`. Names, instance IDs, host paths, guest
paths, and repository references remain machine-local.

## Configure

Add one `[[data.dotfiles_ai.sandbox.workspaces]]` table per VM and one nested
`mounts` table per directory mapping. Each mount declares `host`, `guest`, and
`writable`. Set `protect_git_submodules=true` only for a writable Git checkout
whose submodule worktrees and Git metadata must be remounted read-only before
OpenCode starts. Optional `reference_name` and `reference_description` expose a
mount, or its safe `reference_subpath`, as OpenCode reference context.
Set an optional unique `shell_alias` such as `workspace1sh` to install a
machine-local command equivalent to `sandbox-vm shell workspace1`.

Set `federate=false` to exclude a workspace from sanitized history review. Set
`data.dotfiles_ai.sandbox.build_workspace` to the local workspace name that
receives approved implementation handoffs. Enable sandbox management only after
all configured host paths exist.

Set `lima_home` only in machine-local data when VM state should live outside
Lima's native `~/.lima` default. The value must be absolute. Empty preserves an
inherited `LIMA_HOME`, then falls back to `~/.lima`:

```toml
[data.dotfiles_ai.sandbox]
lima_home = "/Volumes/external/state/lima"
```

Set `atuin_workspace` to exactly one configured personal workspace only when it
should host the rootless Atuin service. Empty is the portable default:

```toml
[data.dotfiles_ai.sandbox]
atuin_workspace = "workspace1"
```

Optional direct tailnet access is global and defaults off:

> [!WARNING]
> Enrollment creates an external tailnet peer identity. Disabling this setting
> prevents new enrollment but does not disconnect or revoke an existing peer;
> retirement must remove it from the Tailscale admin console.

```toml
[data.dotfiles_ai.tailscale]
enabled = false
ssh = false
```

Set both values to `true` only on a host whose configured workspaces should be
enrolled. Peer names come from the existing machine-local Lima hostnames. Tags,
tailnet policy, auth keys, and secret references remain outside this source and
outside local TOML.

## Operate

```sh
sandbox-vm validate workspace1
sandbox-vm create workspace1
sandbox-vm start workspace1
sandbox-vm stop workspace1
sandbox-vm shell workspace1
sandbox-vm status
sandbox-vm configure-atuin
sandbox-vm update workspace1
sandbox-vm update-all
sandbox-vm parity workspace1
sandbox-vm codex-version-parity workspace1
sandbox-vm install-make workspace1
workspace1sh
```

Every managed guest includes GNU Make and uses rootless Podman with
checksum-pinned Docker Compose v2.
The guest-only `docker` command routes `docker compose` to that provider over the
Podman engine, so existing project Make targets keep their normal interface.
Verify after create or update:

```sh
workspace1sh -- podman info --format '{{.Host.Security.Rootless}}'
workspace1sh -- docker compose version
workspace1sh -- make --version
```

`sandbox-vm update` requires the host to run the source-controlled OpenCode and
Codex versions. It repairs the guest's root-owned OpenCode binary, snapshots only
Codex-managed source, configuration, wrapper, projector, and executable state,
then applies the guest source and verifies both exact versions. Failure restores
the prior source revision and Codex-managed artifacts without reading or changing
guest authentication, sessions, logs, or unrelated state. An existing guest must
already provide rootless Podman. A legacy guest without Podman must be recreated
from the current rendered template; the restricted guest account cannot mutate
system packages.

`sandbox-vm update-all` applies the managed source and verifies OpenCode and
Codex for every configured workspace in order while preserving each VM's prior
running or stopped state. It fails before guest mutation if either host version
differs from its managed pin. A later guest failure restores every earlier guest
in reverse order from private content-bounded snapshots; failed rollback is
reported and retained for operator recovery.

`sandbox-vm parity WORKSPACE` reports exact host and direct guest OpenCode
versions, fails on any mismatch, and restores a stopped guest after probing it.
Typed VM handoff runs this check before creating a Herdr workspace.
`sandbox-vm codex-version-parity WORKSPACE` provides the equivalent version-only
Codex check. It does not claim session identity, authentication, worker, history,
recovery, federation, or complete runtime parity.

An existing guest created before GNU Make was added requires
`sandbox-vm install-make WORKSPACE`. The controller preserves prior running or
stopped state, appends one idempotent system provision, restarts only when the
package is missing, and verifies `make --version`. Do not grant the guest user
broader sudo or recreate the VM merely to add this package.

Enroll one workspace with a one-off, pre-authorized, tagged key supplied only on
stdin:

```sh
op read 'op://vault/item/credential' | sandbox-vm tailscale-enroll workspace1
```

Enrollment verifies and installs the pinned static arm64 client, enables a
rootless userspace systemd user service, and enables Tailscale SSH only when the
local `ssh` setting is true. Lima 2.1.4 enables lingering for its configured
guest user; enrollment verifies that contract before installation, so the user
manager keeps the daemon available without a login session. General guest sudo,
root SSH, kernel TUN, host routing, and DNS changes remain unavailable. Lima's
exact read of its non-secret cidata parameters is the sole sudo grant. Disabling the setting later prevents
new enrollment; it intentionally does not disconnect, uninstall, or delete an
existing peer.

After enrollment, obtain the private peer name from the Tailscale admin console
or `tailscale status`. Keep it in machine-local SSH configuration owned outside
this public source:

```sshconfig
Host workspace1-tailnet
    HostName peer-name.example.ts.net
    User guest-user
```

Both authorized macOS hosts can then use the same native interface:

```sh
ssh workspace1-tailnet herdr --version
herdr --remote workspace1-tailnet
herdr --remote workspace1-tailnet --session named-session
```

The alias, peer name, and Unix user are private workstation configuration. Do not
copy Lima's private key or localhost port to another host.

`validate` checks the rendered generic Lima template through the bounded
controller. `create` validates declared paths, creates the configured instance,
and starts it.
`start` and `stop` serialize with temporary federated-review transitions for the
same configured instance and use a 120-second command bound.
`configure-atuin` stops a running selected workspace, applies its exact private
Lima port forward with native `limactl edit`, and restores the prior running
state. It preserves unrelated forwards and rejects host-port conflicts. Use the
cold migration and rollback procedure in `docs/ATUIN_PODMAN.md`.
`shell` resolves the configured instance and defaults `TERM` to
`xterm-256color`; set `LIMA_TERM` to override it. `update` pulls the guest-owned
`dotfiles-ai` checkout with `--ff-only` and reapplies its guest configuration.
Guests use the personal Starship prompt, explicit OpenCode theme, and an isolated
Codex CLI home through a portable Bash profile. Host-only Homebrew, macOS path,
plugin, and credential startup remains outside the sandbox. No running process is
restarted automatically.

Every guest keeps isolated OpenCode, Codex CLI, Herdr, credentials, and session storage.
The guest account can use sudo only for Lima's exact cidata parameter read; all
other commands remain denied. A boot-time verifier waits for every
virtiofs mount, verifies the configured read/write mode, confirms a protected
Git manifest has not changed, reapplies read-only overlays, and only then marks
OpenCode ready.

Federated review reads sanitized bounded pages from the host and each workspace
with `federate=true`. A stopped VM is restored to stopped state after collection.
Raw databases, paths, transcripts, and credentials do not cross the boundary.

## Credentials

When 1Password integration is enabled, every workspace shell receives the
configured macOS Keychain service-account token through Lima environment
forwarding. The controller validates it first and forwards a minimal environment;
the token never enters arguments, templates, TOML, logs, or guest disk. Same-user
guest processes can use its full vault authority while the shell lives. This is
accepted risk `DAI-028-AR1`; review it before token rotation, vault-scope growth,
or guest auto-approval changes. Compose does not implicitly map the token into a
container.

Service-account vault access is immutable. To change scope, create a replacement
account, save its one-time token in 1Password, then update the existing Keychain
entry without printing the token. Keep automation vaults read-only unless writes
are required; the configured development vault may be read/write by explicit
operator decision. Confirm both host and guest identities with `op vault list`
before retiring the prior account; never paste a token into logs, arguments,
source, or chat.

Guests install `op`, so project commands may use `op run` normally. Vertex uses
the separate guest-private ADC at
`~/.config/dotfiles-ai/gcloud-vertex/application_default_credentials.json`.
Renew it through the hosted flow:

```sh
workspace1sh -- vertex-reauth
workspace1sh -- vertex-reauth --check
```

The ADC persists only on the Lima disk. Host ADC and service-account credential
files are neither mounted nor copied. Prefer repository-scoped provider
credentials. A broader provider credential remains accepted risk `DAI-007-AR1`
until 2026-08-18 or its next rotation, whichever comes first.

## Post-Merge Verification

After a source merge and workspace update, verify each configured workspace
without printing credential values:

```sh
sandbox-vm shell workspace1 -- podman info --format '{{.Host.Security.Rootless}}'
sandbox-vm shell workspace1 -- docker compose version
sandbox-vm shell workspace1 -- op vault list
sandbox-vm shell workspace1 -- vertex-reauth --check
```

The Podman result must be exactly `true`. Confirm the guest source checkout is at
the intended merge commit and inspect project containers to prove neither
`OP_SERVICE_ACCOUNT_TOKEN` nor ADC override variables were mapped. A later
unrelated chezmoi hook can fail after managed runtime targets apply; record that
hook separately, verify the DAI-owned files and probes directly, and do not claim
the full update command succeeded.

## Recovery And Retirement

Inspect `sandbox-vm status`, then use the configured instance name with native
Lima diagnostics when recovery requires it. Before retirement, rotate workspace
credentials, run socket-targeted `tailscale logout` inside the guest, disable
`tailscaled-userspace.service`, remove the peer
in the Tailscale admin console, verify it is absent, delete the private
`~/.local/state/tailscale` identity, then stop and delete the configured instance
and remove its local TOML entry. Disabling management does not delete VMs,
credentials, or external tailnet identity.

Before changing `lima_home`, stop every managed instance and copy the complete
Lima home with sparse-disk preservation. Validate each disk and start instances
from the new home before removing the old tree. Roll back by stopping instances,
restoring the prior `lima_home`, and restarting from the retained source copy.

Host container runtimes are unsupported. Run project Compose commands inside the
configured workspace, where the guest-only `docker` command targets rootless
Podman. Before deleting a workspace, stop project services and handle named-volume
data according to that project's retention contract.
