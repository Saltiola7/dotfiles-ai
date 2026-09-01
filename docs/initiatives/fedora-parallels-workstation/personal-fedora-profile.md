# Personal Fedora Profile Slice

## Outcome

The personal source gains a deny-by-default Fedora workstation profile. It owns
shell and terminal behavior, desktop and developer packages, guest storage
mounts, native cache placement, manual updates, Tailscale, 1Password, and Atuin.

## Contracts

- The profile applies only on Fedora ARM64 with the explicit workstation role.
- The root system and normal home configuration remain internal. Bulky state
  uses supported native path controls on the validated data mount.
- Downloads, package and tool caches, rootless container storage, external
  Flatpak installations, and JetBrains install/system paths use the data disk.
- 1Password, Tailscale, and Atuin installation requires no credential at render
  time. Enrollment and login remain explicit and guest-local.
- Atuin uses the existing service, account, and encryption key but creates a
  distinct local database and host identity.
- Tailnet SSH is enabled only by explicit interactive enrollment.
- The manual update command performs one full Fedora upgrade, never reboots,
  reports whether reboot is required, and directs the operator to integration
  verification after reboot.
- Cache reset commands name one supported rebuildable group and never include AI
  auth, sessions, Atuin history, downloads, container volumes, or IDE local
  history implicitly.
- Both chezmoi sources use independent guest checkouts. Personal applies first.
- Shared project worktrees are used by one operating system at a time, and native
  dependency/build artifacts are rebuilt when switching.

## Package Boundary

The initial profile includes Kitty, Zen, JetBrains Toolbox, 1Password desktop
and CLI integration, Tailscale, Git, GitHub CLI, chezmoi, uv, ripgrep, jq,
rootless Podman, build tools, Atuin, Starship, and existing portable terminal
tools. PyCharm selection and sign-in occur through Toolbox. Desktop ricing is a
later concern.

## Validation

Render exact Fedora and existing macOS/Lima inventories, parse scripts, test
native cache variables and missing-mount fallback, verify SELinux labels for
rootless storage, prove Atuin client isolation, and run live package, desktop,
tailnet, update, reboot-required, and Parallels integration checks.
