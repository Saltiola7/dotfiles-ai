# Try Omarchy AI workstation

Use `config.omarchy-try.example.toml` for the native Linux ARM guest. Change `you` to the guest account and set the repository path. Keep this private configuration outside source control. The personal dotfiles source owns the shell, Hyprland, Kitty, Finnish layout, PyCharm, RustDesk and Podman. This source owns coding-agent configuration, native Codex/OpenCode installers, Worktrunk, Herdr TUI and the optional Linux Herdr Desktop/Core installation. Neither source should copy host credentials or overwrite the other's targets.

Create `~/.config/dotfiles-ai/chezmoi.toml` from the example and review the destination diff. First install only the bootstrap command, without running scripts:

```bash
chezmoi --source "$HOME/Projects/dotfiles-ai" \
  --config "$HOME/.config/dotfiles-ai/chezmoi.toml" \
  apply --exclude scripts "$HOME/.local/bin/dotfiles-ai-omarchy-setup"
"$HOME/.local/bin/dotfiles-ai-omarchy-setup"
```

Run the bootstrap in an interactive guest terminal for sudo. It validates `/var/lib/dotfiles-ai/<guest-user>` before package changes, creates owner-only private state, and exports its XDG paths before applying installers. With the worktree root declared as `~/.local/state/worktrees`, it also creates that directory and `~/.cache/dotfiles-ai/dvc` when they are missing: it creates only missing directories, never another root, refuses a symbolic link or a foreign owner anywhere in either path before creating anything, and leaves an existing directory's mode alone. If another config filename is needed, use `DOTFILES_AI_CHEZMOI_CONFIG=/absolute/config.toml`. Provider sign-in stays local: use `codex login` and `opencode auth login`; do not copy the Mac's private state or keys into the guest.

Worktrunk installs before consumers of `wt`, and Linux workstation profiles support both aarch64 and x86_64. Existing PATH providers are inspected before installation: qualified native Worktrunk is reused, while other versions or a separately owned Herdr require an explicit ownership review. Newer native tools are never silently shadowed or downgraded, and an active native Herdr server blocks replacement. Set `dotfiles_ai.herdr.executable` to a reviewed native provider when reusing it. The older remote-user environment remains x86_64-only. Current Codex and native OpenCode V2 owners remain unchanged; the October Parallels branch is not applied wholesale.

## Herdr Desktop qualification

The legacy Herdr TUI and the new app/Core are separate upstream programs. Existing TUI agents do not appear in the Desktop app. The app/Core installer is opt-in through `dotfiles_ai.herdr_linux_desktop.enabled` and defaults off. The Try example enables it for evaluation. It installs missing native, versioned, checksum-verified releases into user-owned paths. Existing working installations and running cores retain their owner and version. An `hc` command already on the system is preserved. No core is started during installation. Executable bundles, launcher entries and icons intentionally live under `~/.local/share`, independently of the bootstrap process's private `XDG_DATA_HOME`, so the normal Omarchy desktop discovers them. Herdr keeps its own runtime state in the guest user session's directories; Codex/OpenCode retain their managed private state paths. None of this state is copied to a host share.

The initial pins are Herdr Desktop 0.1.15 and Core 0.1.21, resolved from official release manifests on 2026-11-14. App and core updates after installation belong to Herdr's updater; this hook does not downgrade them on reapply. Legacy Herdr TUI remains pinned to 0.9.5. Update pins only after reviewing the artifacts and testing them in the guest.

**Linux Herdr Desktop requires Vulkan.** Try Omarchy v1.2 documents no Vulkan support, so installing the ARM binary does not establish a usable desktop. Test actual launch, rendering, clipboard and terminal latency. Software Vulkan, if attempted, is an explicit performance experiment and is not equivalent to hardware acceleration. Herdr TUI and Core do not need the Desktop graphics pipeline. Do not claim the requested daily workflow is complete until the operator accepts the result.

Sources: [Herdr installation and Vulkan requirement](https://github.com/herdrdev/herdr-app#install), [app release manifest](https://releases.herdr.dev/app/latest.json), [Core release manifest](https://releases.herdr.dev/core/latest.json), and [Try Omarchy v1.2 graphics limitations](https://github.com/omacom/try-omarchy/blob/v1.2.0/manual/omarchy-on-a-mac.md).

## Verification and recovery

Check native tool versions, run a real Herdr TUI session and a Desktop/Core session separately, launch Neovim and PyCharm, run the project's notebook/data workload, and exercise an ARM Podman container. CLI version checks alone are not workflow qualification. Check that AI and personal chezmoi managed-target inventories are disjoint.

Back up private guest state and take a stopped-VM backup before changing installer ownership or upgrading the guest. Rollback of source does not uninstall apps or restore credentials. Guest snapshots do not roll back files in host shared folders. Preserve the Parallels VM and HP settings while evaluating this guest.

## Migration completed (2026-11-18)

The cutover finished: the Try Omarchy VM owns the full workstation stack
(herdr layout and sessions, opencode state, the self-hosted atuin fleet
server, PM/DBSCTR PostgreSQL quadlets) and the mac-mini retired to a thin
host applying only the personal dotfiles. The darwin workstation stack and
lima sandbox were removed from source in the
[macos-workstation-retirement](initiatives/macos-workstation-retirement/README.md)
initiative. Herdr Desktop's installed binary remains on the mini pending
operator-gated removal. This document is the migration record; the VM is the
current truth for daily operation.
