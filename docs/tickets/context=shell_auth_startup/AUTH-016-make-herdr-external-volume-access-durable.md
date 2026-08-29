---
schema_version: 1
id: "AUTH-016"
slug: "make-herdr-external-volume-access-durable"
context: "shell_auth_startup"
title: "Make Herdr external-volume access durable"
kind: "bug"
state: "in_progress"
priority: "high"
points: null
depends_on: []
relations:
  - "follows:AUTH-014"
  - "related:AUTH-012"
  - "related:AUTH-013"
  - "related:OCP-35"
  - "related:OCP-39"
owns:
  - "docs/specs/shell_auth_startup/README.md"
  - "docs/specs/shell_auth_startup/OPERATION.md"
  - ".chezmoidata.toml"
  - ".chezmoiignore"
  - "config.example.toml"
  - ".chezmoitemplates/herdr-host.swift"
  - ".chezmoitemplates/herdr-host-Info.plist"
  - ".chezmoitemplates/dev.dotfiles-ai.herdr-host-agent.plist"
  - "run_onchange_before_build-herdr-host.sh.tmpl"
  - "dot_local/bin/symlink_herdr-host.tmpl"
  - "dot_local/bin/executable_herdr-server-owner.tmpl"
  - "dot_local/bin/executable_herdr-opencode-restore"
  - "dot_local/bin/executable_opencode.tmpl"
  - "dot_local/bin/executable_state-root-exec"
  - "tests/test_herdr_launchagent.py"
  - "tests/test_opencode_control_plane.py"
  - "tests/test_portable_distribution.py"
reads:
  - ".chezmoitemplates/herdr-launchagent-supervisor.c"
  - "run_onchange_before_build-herdr-launchagent-supervisor.sh.tmpl"
  - "run_onchange_load-herdr-launchagent.sh.tmpl"
  - "dot_local/bin/executable_state-root-exec"
parallel_safe: false
validation:
  - "uv run --group test pytest -q tests/test_herdr_launchagent.py tests/test_opencode_control_plane.py tests/test_portable_distribution.py"
  - "Compile Swift and C with warnings as errors; verify the installed bundle and each nested executable independently with codesign --verify --strict"
  - "Build twice and prove the two signed versions satisfy the same designated requirement"
  - "Run bash -n on changed shell templates and plutil -lint on every rendered plist"
  - "Preview installation without replacing the active Herdr server, then perform an explicitly approved activation and external-volume fault-injection soak"
created: "2026-08-28"
updated: "2026-08-28"
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Herdr and its OpenCode descendants retain a stable macOS privacy identity across
source rebuilds, detect loss of access to the configured external state volume,
and degrade and recover without freezing every managed session or restarting
user processes. All authoritative OpenCode state remains on `/Volumes/ext`.

## Context

AUTH-014 replaced a shell-responsible LaunchAgent with a native, ad-hoc-signed
supervisor. That restored access initially, but an ad-hoc signature's designated
requirement is tied to the exact build. It does not provide durable privacy
identity across rebuilt executables.

External-volume denials recurred on August 25, August 27, and August 28, 2026.
During the August 28 incident, macOS TCC logged `missing auth_value` and
`Failed to create Attribution Chain` at 17:34:08 local time, followed by System
Policy denials for Herdr, OpenCode, Git, and Bash paths under `/Volumes/ext`.
Denials against the existing Herdr process continued until 17:53:32. OpenCode
reported a misleading possible file-descriptor shortage, while shells and npm
reported `getcwd`, `process.cwd`, and `uv_cwd` `EPERM` failures. The volume stayed
mounted and healthy, and root or fresh-process `stat` success did not prove that
the long-lived responsible process had TCC access.

At least 22 OpenCode processes across four projects and 15 sessions were exposed
to the outage. Access returned without a new Kitty window or a Herdr restart.
The operator also added the current raw supervisor to Full Disk Access (FDA).
The last observed denial preceded the related registration evidence, so the
incident does not prove whether FDA caused recovery or macOS recovered first.
The raw-supervisor FDA entry is therefore a useful stopgap, not the durable
identity contract.

## Scope

- Build and install a managed, non-sandboxed `Herdr Host.app` under
  `~/Applications`, with bundle identifier `dev.dotfiles-ai.herdr-host` and the
  Herdr supervisor or host executable inside the bundle.
- Register the bundled LaunchAgent through `SMAppService.agent(plistName:)`.
  Use a bundled `BundleProgram` so launchd starts code whose responsibility and
  signing identity are anchored to the application bundle.
- Provision and use one explicitly selected, machine-local, self-signed code-
  signing identity in the login Keychain. Sign nested code before the outer
  application, and refuse deployed mode when the identity is missing,
  ambiguous, expired, or replaced by ad-hoc signing.
- Document interactive certificate creation, trust, selection, renewal,
  rotation, recovery, and removal. Never silently create, trust, replace, or
  delete a signing identity.
- Require the operator to approve the Login Item and grant FDA to the durable
  application identity. Detect access through a real filesystem probe; never
  inspect or mutate the TCC database and never attempt to grant FDA in code.
- Bind external state to its expected volume UUID and a managed sentinel. Before
  starting or restoring OpenCode, and before declaring recovery, verify the
  volume identity and complete an atomic read/write probe in the configured
  state root.
- Add an external-volume health controller with starting, healthy,
  degraded-permission, degraded-unavailable, and recovering states. Retry probes
  with bounded backoff.
- On `EPERM`, enter degraded-permission state, circuit-break new OpenCode starts,
  restore attempts, and session-capture writes, publish one notification per
  incident, and retain structured status for diagnostics. Leave every existing
  pane, Herdr server, and OpenCode process untouched.
- On absence or I/O failure, report degraded-unavailable separately from a TCC
  denial. If a different volume appears at the expected mount path, fail closed
  and do not write to it.
- On recovery, revalidate UUID, sentinel, read access, and write access before
  resuming starts, restore, and capture. Never restart or replay existing
  processes automatically; operators may retry a failed prompt or request a
  maintenance restart explicitly.
- Keep only minimal, non-authoritative health metadata on the internal disk,
  such as state, timestamps, errno, expected and observed volume identity, and
  notification status. Store no prompt, response, session manifest, database,
  repository content, or other OpenCode state there.
- Expose a documented operator status and diagnostic interface, including
  machine-readable health output and direct guidance to the relevant macOS
  Login Items and FDA settings. Make the OpenCode wrapper preflight this status
  and report an external-volume permission failure instead of surfacing Bun's
  false file-descriptor hint.
- Install and register the new bundle without replacing the active Herdr server.
  Preserve AUTH-014 files and the current FDA entry through a controlled
  migration and rollback window. Activate the new responsibility chain only
  during a separately approved maintenance restart.

Non-goals:

- Moving any authoritative OpenCode state, session data, or database from
  `/Volumes/ext` to the internal disk.
- Automatically restarting Herdr, Kitty panes, OpenCode sessions, or failed
  prompts after permission loss or recovery.
- Granting privacy permissions to Bash, Git, OpenCode, or other descendants
  individually.
- Running `tccutil reset`, editing TCC databases, deleting the legacy FDA entry,
  or removing the signing identity automatically.
- Depending on Apple support or feedback responses for runtime recovery.

## Acceptance Criteria

- `Herdr Host.app` contains the LaunchAgent plist and executable used by
  `SMAppService`, and rendered configuration contains no direct script or
  platform-shell responsibility boundary.
- One documented certificate workflow produces a stable designated requirement.
  Two separate source builds signed by that identity mutually satisfy the
  expected requirement and pass strict signature validation.
- Build and install fail with actionable output when no exact signing identity is
  configured, more than one candidate matches, the certificate is unusable, or
  any required nested artifact would remain ad-hoc signed.
- Operator documentation defines FDA, identifies the exact app to authorize,
  explains Login Item approval, and covers certificate lifecycle, normal health
  checks, incident response, activation, rollback, and post-recovery validation.
- The configured external state root remains `/Volumes/ext` and no authoritative
  session or OpenCode database data is copied to internal storage.
- Expected UUID plus sentinel and atomic read/write probes distinguish healthy,
  permission-denied, unavailable, I/O-failed, and wrong-volume conditions.
- A simulated or live `EPERM` changes status once, emits at most one notification
  for that incident, and prevents new starts, restores, and capture writes while
  existing processes remain running.
- OpenCode preflight reports the external-volume access problem, responsible app
  identity, current health state, and manual next action without recommending a
  larger `ulimit` as the primary fix.
- A replacement volume mounted at `/Volumes/ext` is never written, even if it is
  otherwise writable and contains a similarly named directory.
- Recovery requires the expected UUID, sentinel, and successful read/write probe.
  It clears the circuit breaker without restarting or duplicating any Herdr pane
  or OpenCode session.
- Internal health status is atomic, bounded, non-authoritative, and contains no
  prompt, response, session identifier, session manifest, database payload, or
  repository content. Logs follow the same privacy rule and bounded retention.
- Registration, deployment preview, and bundle installation do not replace the
  active Herdr server. Activation cannot occur without explicit restart approval.
- Failed activation restores the previous plist and raw supervisor atomically.
  Existing server state is preserved, and any restart during rollback also
  requires approval.
- Exact-session capture and paced restore behavior remain compatible with
  AUTH-013, OCP-35, and OCP-39: no duplicate sessions, no unpaced restart burst,
  and no server-wide generic XDG routing.
- Focused automated tests, rendered-file validation, signature checks, a fresh-
  pane external read/write check, sleep/wake validation, and at least one signed
  source-rebuild soak all pass before AUTH-014 is retired as the rollback path.

## Evidence

Established facts:

- Repeated failures are process-scoped macOS privacy denials, not volume
  unmounts, Unix ownership failures, or exhaustion of the observed 8192 file-
  descriptor limit.
- The August 28 outage self-healed while the same user-facing environment stayed
  open; a new Kitty window was not involved.
- The current raw supervisor is ad-hoc signed and has no Team ID. The machine had
  no valid code-signing identity before this discovery.
- Apple documents `SMAppService` for managed login items and agents, and TN3127
  explains why stable designated requirements matter for privacy identity:
  <https://developer.apple.com/documentation/servicemanagement/smappservice> and
  <https://developer.apple.com/documentation/technotes/tn3127-inside-code-signing-requirements>.
- Apple DTS recommends placing daemon or agent code inside an application bundle
  when durable privacy authorization is required:
  <https://developer.apple.com/forums/thread/118508>.

Discovery decisions:

- Use both a stable signed application identity and operator-granted FDA.
- Keep all authoritative OpenCode state on `/Volumes/ext`.
- Default to manual process recovery. Automated health-state recovery may reopen
  starts and writes only after validation; it may not restart processes.
- Permit minimal internal health metadata because diagnostics must remain
  available while `/Volumes/ext` is denied. Any future proposal to copy session
  manifests requires separate explicit approval.
- Treat exact probe cadence, bounded-backoff values, and command spelling as
  implementation details, provided tests enforce bounded resource use and the
  behavioral contract above.

Required validation evidence:

- Unit and integration tests inject `EPERM`, `ENOENT`, `EIO`, stale status,
  wrong UUID, missing sentinel, and successful recovery.
- Tests prove no write reaches a replacement volume and no private session data
  reaches internal health files or logs.
- Swift and C compile with warnings as errors; the app and nested executables pass
  strict signature verification; two builds pass mutual designated-requirement
  checks.
- Changed shell templates pass `bash -n`; rendered property lists pass
  `plutil -lint`; focused pytest suites pass.
- Deployment preview preserves the active server. Approved activation proves a
  fresh pane can read and write the exact external state root, then survives
  sleep/wake and one source rebuild without renewed privacy failure.

## Risks

- An unstable bundle path, identifier, signing certificate, or nested-code layout
  can create another macOS privacy identity and invalidate FDA expectations.
- Self-signed certificate private-key compromise would permit impersonation of
  the local app identity. Keychain ACLs, exact identity selection, documented
  rotation, and least-privilege use are required.
- `SMAppService` changes LaunchAgent registration and may require explicit Login
  Item approval. A premature activation could interrupt every Herdr pane.
- A stale health record could block healthy starts or permit a start after access
  disappeared. Preflight age limits and a live probe must fail safely.
- Probe writes can create wear, debris, or noise if cadence and cleanup are wrong.
  Tests must cover atomic creation, cleanup, bounded retry, and interrupted probes.
- Volume-path reuse creates data-corruption risk unless UUID and sentinel checks
  precede every recovery transition and every write-enabled operation.
- Keeping legacy and new privacy entries during migration can confuse operators.
  Documentation must identify active identity without automatically deleting
  recoverable rollback state.

## Review

Discovery and the probe-only implementation slice are complete. The staged host
implements the stable-signing boundary, sealed configuration, exact-volume
health checks, private health metadata, ServiceManagement registration command,
and runtime circuit breakers. It deliberately rejects active ownership and does
not register, grant FDA, replace AUTH-014, or restart a process during build.

The approved probe-only local deployment provisioned a Code-Signing-only identity,
proved two strict-valid builds share the same designated requirement, installed
the canonical host, registered its bundled agent with `enabled` status, and added
the exact `Herdr Host.app` FDA entry. The registered-agent UUID, sentinel, and
atomic read/write probe is healthy. Host PID `7028`, Herdr PIDs `15287`, `27922`,
and `92506`, and all 35 OpenCode processes were preserved without restart.

This ticket remains `in_progress`: durable runtime ownership still requires a
separately reviewed activation/handoff command with process-preservation tests,
explicit maintenance-restart approval, live fault injection, and soak. Those
operation gates may not be inferred from probe-only deployment evidence.

Probe-only checkpoint evidence: 100 affected tests passed; production/test Swift
compilation, rendered shell syntax, plist lint, privacy scans, and diff checks
passed. Independent review found the staged boundary clean, while confirming
that active-mode probe serialization, child-exit handling, and error unwinding
must be redesigned before `activation_supported` can ever become true.
