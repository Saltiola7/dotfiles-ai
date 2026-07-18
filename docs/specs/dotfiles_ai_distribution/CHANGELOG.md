# dotfiles-ai Distribution Changelog

## Unreleased — DAI-002

- Added opt-in Hermes bootstrap, gateway supervision, Herdr integration, daily
  DBSCTR review scheduling, checked updates, and machine-local repository policy.
- Bound reviews to one dedicated native Build session and fail closed on
  ambiguous identity, custom primaries, unrelated permissions, or new authority.
- Added bounded `Allow once` handling for review persistence and compaction only
  after successful persistence.
- Added runtime self-repair when the Hermes launcher cannot report a version.
- Validation: 149 passed, 1 skipped; rendered shell and plist checks passed;
  managed dry-run reported no drift.
- Runtime smoke: cron execution `314956082b7d40f791a390fe2fe10d84`
  marked 3 sessions and 1 cycle reviewed, then compacted only the dedicated
  worker from 15.3K to 3.2K tokens.
- Gate Exceptions: none.

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
