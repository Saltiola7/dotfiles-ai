# Shell Auth Startup Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Managed shell startup, bounded 1Password loading, signed Herdr external-volume responsibility, native Herdr lifecycle, and exact OpenCode/Codex session recovery |
| Owner | Dotfiles owner |
| Languages/frameworks | Bash, Zsh, C, Swift, ServiceManagement, Go templates, app bundles, launchd plists, and Markdown |
| Modules | Security, Cloud |
| Runtime/platform support | Interactive macOS shells, SSH, Herdr panes, macOS Aqua, Fedora Lima guests, intended RHEL 10 x86_64 remote-workspace successor (release qualification pending), OpenCode, Codex CLI, chezmoi, 1Password CLI, Keychain, and Linux runtime-local authentication |
| Compatibility | Shell startup remains nonblocking; optional auth never becomes startup-required; existing OpenCode and Herdr processes survive migration and recovery failures |
| Trust/data | Credentials remain in environment, Keychain, cache, 1Password, or runtime-local auth; health records contain no prompt, session, database, repository, or state-root path |
| Delivery | Feature branch and draft pull request; signed-host or recovery activation only after explicit operation gates pass |
| Operations | Exact-volume health, signed ancestry, bounded failure, process preservation, versioned exact-session recovery, rollback |
| Authorities | Shell and Swift compilation, rendered plists, signature and ServiceManagement checks, Full Disk Access probes, exact-volume health, `pytest`, and fresh runtime smokes |

The context README retains historical cycle overrides. New cycles use this
profile.

`rhel-remote-workspace` / `rrw-002-rhel-user-runtime` (planned `RRW-002`)
is approved successor Discovery, not implementation or deployment evidence.
Historical RWUE checks remain platform-specific history. RHEL startup stays
nonblocking and credential-free; explicit authentication and local-only Atuin
history remain per-user, with no owner/peer credential copying. Both users are
supported targets, but colleague readiness requires independent exercise.
Coordinator authority, gate results, and actual RHEL qualification remain pending;
UBI10 smoke does not qualify SELinux, rootless Podman, systemd, or IAP.
