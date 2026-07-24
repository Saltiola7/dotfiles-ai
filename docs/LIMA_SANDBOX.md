# Lima OpenCode Sandboxes

## Model

The macOS OpenCode, Herdr, database, and scheduled R&D loop remain unchanged.
Each configured client gets one Fedora VM with its own OpenCode database,
credentials, Herdr server, and guest-owned `dotfiles-ai` clone. Only declared
host source roots are mounted writable.

The VM's `60GiB` disk is a sparse maximum. Host allocation grows with actual
guest files and does not shrink automatically.

## Prepare Paths

Keep repositories requiring different write policy outside the broad writable
client root. Configure the client root and protected repository in the private
chezmoi TOML; never add machine paths to shared defaults.

Before moving an existing checkout, verify its dirty files, linked worktrees,
submodules, and open Herdr panes. Preserve compatibility symlinks until old
OpenCode sessions are retired, and run `git worktree repair` after moving a main
checkout that owns linked worktrees.

## Create

Preview and apply the host configuration first:

```sh
chezmoi -S ~/.local/share/chezmoi-dotfiles-ai \
  -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -S ~/.local/share/chezmoi-dotfiles-ai \
  -c ~/.config/dotfiles-ai/chezmoi.toml apply
opencode-vm create mgm
opencode-vm status
```

Create MGM first when host storage is constrained. Measure real allocation and
retain adequate macOS free space before creating personal:

```sh
opencode-vm create personal
```

Creation fails closed unless every declared `seo-code-analysis` submodule path,
`.gitmodules`, and existing `.git/modules` metadata is read-only inside MGM, and
the VM agent user cannot run unrestricted sudo.

## Authenticate

Enter each VM and authenticate separately. Do not mount or copy host credential
stores.

```sh
limactl shell opencode-mgm
opencode auth login
gh auth login
```

Use repository-scoped credentials. MGM write credentials cover only approved
writable repositories; the protected parent and submodule repositories receive
read-only remote authority. Every credential supplied to a VM is readable by an
auto-approved agent and usable over unrestricted network egress.

## Daily Use

Either enter explicitly or use the host shortcut:

```sh
limactl shell opencode-mgm
herdr

herdr-mgm
herdr-personal
```

The shortcut starts the selected VM when necessary and attaches to its existing
Herdr session. Detaching leaves processes running. A clean VM stop kills guest
processes; on restart, Herdr restores its layout and eligible OpenCode session
IDs. The VM launcher reapplies auto approval to restored interactive sessions.

Host and VM Herdr workspaces are separate.

## Federated R&D

`dbsctr_review_federated` scans host history locally and invokes source-local
read-only exporters in personal and MGM sequentially. A stopped VM is started
only for export and returned to stopped state. The manifest reports unavailable
sources explicitly and transfers no database file, transcript, machine path, or
credential.

After explicit Discovery approval, `dbsctr_vm_handoff` launches a visible Build
session in personal VM Herdr. Its guest-owned `dotfiles-ai` checkout owns a new
DBSCTR cycle and draft pull request. The host claim is correlation only; Cycle
Records and private ledgers are never shared.

## Update

After an approved `dotfiles-ai` merge:

```sh
opencode-vm update mgm
opencode-vm update personal
opencode-vm status
```

Update uses `git pull --ff-only` in each guest-owned source and reapplies managed
Linux targets. Existing OpenCode processes keep their loaded configuration;
quit and restart those processes to receive config, agent, command, skill, or
plugin changes.

Changes to the Fedora image, Lima template, protected submodule manifest, sudo
boundary, or pinned binaries require VM recreation after preserving any needed
session exports and Git work.

## Recovery And Retirement

If a VM is corrupted, export required OpenCode sessions and push or patch needed
Git work before deletion. Deletion is explicit and irreversible for guest-local
databases and credentials:

```sh
limactl stop opencode-mgm
limactl delete opencode-mgm
```

Reapply the host source and recreate the VM from its rendered template. Remove
repository credentials before retiring a client, then remove compatibility
symlinks only after no host session or linked worktree depends on the old path.
