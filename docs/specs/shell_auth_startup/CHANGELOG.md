# Shell Auth Startup Changelog

## 2026-08-29 - Captured Codex State And Recovery Contract

- Extended the signed-host and external-volume contract to future Codex CLI
  preflight, circuit breaking, content-free snapshots, and exact supported-thread
  recovery while preserving existing processes and OpenCode behavior.
- Kept implementation and live capability proof blocked on Codex installation,
  identity correlation, and a separate approved Build readiness mechanism.
- Initiative validation, 57 focused helper/lifecycle/distribution tests, Python
  compilation, Git whitespace, and independent elevated-risk review passed.
  Gate Exceptions: none. Release, Deploy, and Operate: not applicable. Gate
  Commit: the commit containing this entry.

## 2026-08-28 - AUTH-016 Probe-Only Local Deployment

- Provisioned one machine-local signing identity whose trust is limited to Code
  Signing, then proved two strict-valid host builds share the same designated
  requirement before installing the canonical `~/Applications/Herdr Host.app`.
- Registered the bundled agent through ServiceManagement and verified its status
  is `enabled`. The operator added the exact `Herdr Host.app` entry to Full Disk
  Access and enabled it.
- Verified the registered-agent probe is healthy against the configured volume
  UUID: the sentinel and atomic read/write checks pass, the strict bundle
  signature and designated requirement pass, and no matching new TCC denial was
  observed in the verification window.
- Preserved the existing process coalition without a restart: host PID `7028`,
  Herdr PIDs `15287`, `27922`, and `92506`, and all 35 OpenCode processes were
  unchanged. The deployed host remains sealed in probe-only mode with
  `activation_supported=false` and `child_running=false`; AUTH-014 remains
  authoritative, while activation, fault injection, and soak remain not run.

## 2026-08-28 - AUTH-016 Probe-Only Herdr Host

- Added an opt-in, signed `~/Applications/Herdr Host.app` with a bundled,
  distinctly labelled `SMAppService` LaunchAgent and a direct managed CLI link.
  Build, registration, consent, and process activation remain separate gates.
- Added a host-owned exact-volume probe, private atomic health/ownership records,
  bounded retry, deduplicated incident notification, signed-resource validation,
  and fail-closed wrong-volume, permission, unavailable, and I/O states.
- Added OpenCode, restore/capture, state-root, and Herdr-owner circuit breakers.
  New work pauses on active-host degradation; existing processes are never
  restarted by recovery logic.
- Kept authoritative OpenCode and Herdr state on the external volume. Internal
  storage contains only bounded health metadata with no prompt, response,
  session, database, repository, or state-root-path content.
- This is a probe-only staging slice: `activation_supported=false` is sealed into
  the signed bundle, manual activation markers are rejected, and no build/apply
  action registers, grants FDA, replaces AUTH-014, or restarts Herdr/OpenCode.
- Validation passed 100 affected tests, production/test Swift compilation,
  rendered shell syntax, plist lint, privacy scans, and independent probe-only
  security review. No valid signing identity exists, so trusted two-build,
  ServiceManagement, FDA, activation, and soak gates remain not run.

## 2026-08-28 - AUTH-016 Durable External-Volume Discovery

- Recorded the third observed recurrence of macOS TCC attribution-chain failure:
  the mounted, healthy `/Volumes/ext` remained accessible to fresh authorized
  processes while the existing Herdr/OpenCode coalition received System Policy
  denials. OpenCode's low-file-descriptor suggestion was a generic consequence,
  not the cause.
- Chose a stable signed `Herdr Host.app`, bundled SMAppService agent, explicit
  Login Items approval, and Full Disk Access as the durable privacy identity.
  The accepted machine-local signing-certificate provisioning, rotation, and
  removal workflow is an operator-visible lifecycle documented in
  `OPERATION.md`.
- Kept all authoritative OpenCode state on `/Volumes/ext`. The internal disk may
  contain only atomic, non-authoritative health metadata without session,
  prompt, or database content.
- Defined exact-volume identity checks, fail-closed degraded operation, bounded
  recovery probes, deduplicated notification, and manual process lifecycle.
  Permission loss never automatically restarts Herdr, OpenCode, Kitty, or panes.
- The operator added the existing AUTH-014 supervisor to Full Disk Access as a
  stopgap. Access recovered without a Kitty or Herdr restart; denials stopped
  before the first observed FDA-related registration event, so causation remains
  unproven.
- At this discovery checkpoint, no host implementation, registration migration,
  process restart, TCC reset, or authoritative-state migration was performed.

## 2026-08-25 - AUTH-014 Lifecycle Reconciliation

- Verified AUTH-014 is clean, fully integrated, and has no commits ahead of
  protected `main`. Its cycle remains unchanged in `finalizing` because the typed
  retirement contract rejects that state; recovery is assigned to the lifecycle
  state-machine fix.

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
