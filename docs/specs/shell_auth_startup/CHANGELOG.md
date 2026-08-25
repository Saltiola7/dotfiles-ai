# Shell Auth Startup Changelog

## 2026-08-24 - Herdr External-Volume Responsibility

- Added a native LaunchAgent supervisor so macOS attributes Herdr and pane
  removable-volume access to one narrow, user-grantable executable instead of
  the platform shell, while retaining the state guard, owner monitor, live
  handoff, and paced exact-session recovery.
- Passed 44 affected tests, rendered shell and plist checks, strict Mach-O
  signature verification, and independent security/process review.
- Deployed the signed supervisor and one-line plist change without interrupting
  the old server, then completed the separately approved restart. TCC recorded
  the supervisor as the responsible allowed subject; a fresh pane read and wrote
  the external volume with no new System Policy denial.
- Restored 32 panes with 20 unique detected sessions and closed the temporary
  probe tab. Gate Exceptions: none. Gate commit: `75e6836`.

## 2026-08-23 - Paced OpenCode Session Recovery

- Added Herdr-only `--auto`, stale-safe five-second session-start pacing, exact
  session parsing with trailing flags, serialized restore helpers, and resilient
  manifest watching.
- Passed 78 affected tests, rendered syntax checks, and independent review with
  no actionable findings.
- Applied and verified the three managed executables, recovered 45 stalled exact
  sessions, and verified 46 unique rendered `--auto` sessions while preserving
  Herdr owner/server PIDs `2974` and `3109`.
- Left the duplicate pane open at its shell while retaining that session identity
  in the active operator pane. Gate commits: `01ef8fa`, `828c539`, `36715c4`,
  `1980b9b`.

## 2026-08-22 - Native Herdr Ownership

- Pinned and installed native Herdr 0.8.2 under `~/.local/bin` with SHA-256
  verification, exact protocol checks, bounded live handoff, and rollback.
- Kept the Aqua LaunchAgent owner alive across handoff, added five-probe
  tolerance, and made unexpected server disappearance restartable.
- Live deployment exposed repeated post-handoff shutdowns and session restores;
  recovery finished with 54 panes, 46 live session identities, native server PID
  `47444`, LaunchAgent owner PID `73813`, and a three-minute stable ownership soak.
- Validation passed 75 affected tests, rendered shell and plist checks, and an
  independent final review with no actionable findings. Gate commits: `12f402a`,
  `9020e21`.

## 2026-08-18 - Canonical Ticket Migration

- Migrated completed shell-auth work records to independently validated PM
  Kernel tickets with original row provenance.

## 2026-07-30 - V3.35 Documentation Reconciliation

- Added the missing Engineering Profile and completed AUTH-011 Gate Ledger,
  ordered history newest-first, and archived the completed AUTH-011 start plan.
  Credential precedence and deployed Aqua LaunchAgent behavior are unchanged.

## 2026-07-28

- Made unmanaged Herdr handoff fail without stopping the active server so chezmoi keeps the deployment retryable.
- Replaced unreliable `herdr status server` exit-code checks with structured `running` status in the loader and owner wrapper.
- Added a bounded managed-server shutdown wait before LaunchAgent bootstrap.
- Validated three focused tests, rendered shell syntax, targeted chezmoi deployment, a running Aqua LaunchAgent, Keychain access, and Herdr-mode `op-session`.
- Gate commits: `e858602`, `4a05198`. Deployment: local macOS Aqua session.

## 2026-07-15

- Made Keychain diagnostic capture compatible with inherited Bash `noclobber`.
- Added a rendered-helper regression test proving Herdr service-token validation succeeds under `set -C` without exposing credentials.

## 2026-07-13

- Preserved actionable macOS Keychain errors while keeping service-account tokens out of output.
- Added Keychain Access repair guidance after `security -w` interactive input truncated the service-account token to 128 characters.
- Added a credential-free Aqua LaunchAgent after RCA found the headless persistent Herdr server could not access the login Keychain.

## 2026-07-02

- Changed Herdr secret loading to use `OP_SERVICE_ACCOUNT_TOKEN` from the environment or a machine-local macOS Keychain service/account.
- Herdr panes now fail fast instead of attempting delegated desktop `op signin`.
- Added explicit `Automation` vault scoping for the `Shell Secrets` item fetch required by service accounts.
- Changed the default `ShellSecretsItem` id to the copied item in `Automation`.
- Changed `secret` to source sibling `op-session` directly so existing panes do not need `hash -r` after deploys.

## 2026-06-22

- Created shell auth startup spec after RCA found stuck `op read` processes and Herdr auth fanout.
- Removed Herdr profile auto-hydration so restored panes do not run `secret` automatically.
- Added bounded 1Password CLI execution and session-cache locking for `secret` / `op-session`.
- Changed Clockify SketchyBar polling to use only cached/env API keys; poll loop no longer calls `op read`.
- Removed Databricks `onepasswordRead` template calls; `secret` now exports Databricks env vars.
- Verification: shell syntax checks passed; `secret` with `OP_TIMEOUT_SECONDS=2` failed fast in non-TTY.
