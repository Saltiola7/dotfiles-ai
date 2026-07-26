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

## Operate

```sh
sandbox-vm validate workspace1
sandbox-vm create workspace1
sandbox-vm shell workspace1
sandbox-vm status
sandbox-vm update workspace1
workspace1sh
```

`validate` checks the rendered generic Lima template through the bounded
controller. `create` validates declared paths, creates the configured instance,
and starts it.
`shell` resolves the configured instance and defaults `TERM` to
`xterm-256color`; set `LIMA_TERM` to override it. `update` pulls the guest-owned
`dotfiles-ai` checkout with `--ff-only` and reapplies its guest configuration.
Guests use the personal Starship prompt and explicit OpenCode theme through a
portable Bash profile. Host-only Homebrew, macOS path, plugin, and credential
startup remains outside the sandbox. Restart OpenCode after an update because it
does not reload its theme while running.

Every guest keeps isolated OpenCode, Herdr, credentials, and session storage.
The guest account cannot execute `sudo`. A boot-time verifier waits for every
virtiofs mount, verifies the configured read/write mode, confirms a protected
Git manifest has not changed, reapplies read-only overlays, and only then marks
OpenCode ready.

Federated review reads sanitized bounded pages from the host and each workspace
with `federate=true`. A stopped VM is restored to stopped state after collection.
Raw databases, paths, transcripts, and credentials do not cross the boundary.

## Credentials

Authenticate separately inside each workspace and prefer repository-scoped
credentials. A broader provider credential remains accepted risk `DAI-007-AR1`
until 2026-08-18 or its next rotation, whichever comes first.

## Recovery And Retirement

Inspect `sandbox-vm status`, then use the configured instance name with native
Lima diagnostics when recovery requires it. Before retirement, rotate workspace
credentials, stop and delete the configured instance, and remove its local TOML
entry. Disabling management does not delete VMs or credentials.
