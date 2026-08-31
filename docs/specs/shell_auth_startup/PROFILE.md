# Shell Auth Startup Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Managed shell startup, bounded 1Password loading, signed Herdr external-volume responsibility, native Herdr lifecycle, and exact OpenCode/Codex session recovery |
| Owner | Dotfiles owner |
| Languages/frameworks | Bash, Zsh, C, Swift, ServiceManagement, Go templates, app bundles, launchd plists, and Markdown |
| Modules | Security, Cloud |
| Runtime/platform support | Interactive macOS shells, SSH, Herdr panes, macOS Aqua, Fedora Lima guests, OpenCode, Codex CLI, chezmoi, 1Password CLI, and Keychain |
| Compatibility | Shell startup remains nonblocking; optional auth never becomes startup-required; existing OpenCode and Herdr processes survive migration and recovery failures |
| Trust/data | Credentials remain in environment, Keychain, cache, 1Password, or runtime-local auth; health records contain no prompt, session, database, repository, or state-root path |
| Delivery | Feature branch and draft pull request; signed-host or recovery activation only after explicit operation gates pass |
| Operations | Exact-volume health, signed ancestry, bounded failure, process preservation, versioned exact-session recovery, rollback |
| Authorities | Shell and Swift compilation, rendered plists, signature and ServiceManagement checks, Full Disk Access probes, exact-volume health, `pytest`, and fresh runtime smokes |

The context README retains historical cycle overrides. New cycles use this
profile.
