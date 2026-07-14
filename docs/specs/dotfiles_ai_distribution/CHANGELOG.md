# dotfiles-ai Distribution Changelog

## 2026-07-13 — v0.1.0

- Added a standalone public chezmoi source for DBSCTR V3.10, OpenCode, and
  Herdr configuration.
- Added curated machine-local TOML overrides without committed account IDs,
  credentials, or paths.
- Added opt-in 1Password session integration and a credential-free macOS Aqua
  LaunchAgent.
- Added installation, preview, cutover, rollback, update, and retirement
  guidance.
- Validation: 92 passed, 1 skipped; JSON, shell, plist, public-safety, parity,
  and runtime checks passed.
- Independent review found no remaining cutover blocker.
- Deployment restored Herdr workspaces under `dev.dotfiles-ai.herdr-server` but
  required a visible server restart.
- Gate Exceptions: none.
- Intended Final Push: `origin/main`.
