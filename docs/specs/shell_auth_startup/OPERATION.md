# Herdr External-Volume Operation

This runbook governs Herdr and OpenCode when their managed state and projects
remain on an external macOS volume. It covers the currently deployed legacy
supervisor and the durable `Herdr Host.app` design selected by AUTH-016. The
external state root remains authoritative; this procedure does not move or copy
OpenCode state to the internal disk.

The durable design is not considered deployed until its signed application,
ServiceManagement registration, health interface, fault tests, and controlled
activation have all passed the gates below. Until then, the existing native
supervisor is the rollback path.

The repository currently delivers the **probe-only staging slice**. Its signed
configuration sets `activation_supported=false`; a manually edited `active`
ownership marker is rejected. Building or applying this slice does not register
the Login Item, grant Full Disk Access, replace the AUTH-014 owner, or restart any
Herdr/OpenCode process. Durable ownership remains intentionally unavailable until
a separately reviewed activation command, process-preservation tests, and an
explicit maintenance-restart approval exist.

## Visual Evidence

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | required: the README owns the responsible-code and external-volume trust boundary | Which signed code identity receives privacy approval and owns Herdr descendants? | `README.md` Visual Evidence | Shell-auth owner; signing, TCC, or process-ancestry change |
| Interaction | required: the incident and activation procedures below order every operator action | Can the operator recover without destroying live pane state? | Immediate Incident Response and Migration and Activation | Shell-auth owner; recovery or deployment change |
| State | required: the health table below maps every durable state to one bounded response | Does a denial stop new work without restarting existing work? | Health Model | Shell-auth owner; probe or recovery-state change |
| Data/trust | required: the local metadata allowlist below bounds internal-disk persistence | Can prompts, sessions, credentials, or OpenCode databases reach internal recovery storage? | Data and Privacy | Shell-auth owner; status, logging, or retention change |
| Schema | not_applicable: health metadata is an implementation-private, replaceable status record | Is any health record a source of session truth? | Data and Privacy | Shell-auth owner; health record becomes externally consumed |
| Dependency/deployment | required: the migration gates below define signing, ServiceManagement, FDA, handoff, and rollback order | Can a new host be staged without disturbing the active server? | Migration and Activation | Shell-auth owner; bundle, LaunchAgent, or registration change |
| Quantitative | not_applicable: retry timing and log retention are safety bounds, not comparative evidence | Would a metric alter the permission decision? | Health Model and Data and Privacy | Shell-auth owner; SLO or capacity decision |

**Text Equivalent:** During an incident, preserve the running process tree, move
the operator shell to an accessible directory, inspect the responsible host's
health, and wait for validated access recovery. New OpenCode launches are
blocked while permission, volume availability, or volume identity is degraded.
Recovery re-enables launches but never restarts Herdr, panes, or OpenCode. A new
signed host is staged and granted Login Item and Full Disk Access approval before
one separately approved activation; failure leaves or restores the legacy host.

## Operating Model

macOS privacy policy follows the responsible process and its code identity, not
only the path being accessed. A successful `stat /Volumes/ext` from an unrelated
shell therefore does not prove that a running Herdr process tree can traverse
the volume. Likewise, a fresh Kitty window can receive a different privacy
decision and is not a repair for an existing process tree.

| Stage | Responsible code | Registration | Signing | Purpose |
|---|---|---|---|---|
| Current rollback | `~/.local/bin/herdr-launchagent-supervisor` | legacy Aqua LaunchAgent `dev.dotfiles-ai.herdr-server` | ad-hoc | Preserve the deployed AUTH-014 process tree until durable activation succeeds |
| Durable target | `~/Applications/Herdr Host.app` (`dev.dotfiles-ai.herdr-host`) with a bundled LaunchAgent program | `SMAppService.agent(plistName:)` and the macOS Login Items UI | one explicitly provisioned, machine-local self-signed code-signing identity | Give TCC a stable application identity and expose bounded external-volume health |

The target application and bundled host are not App Sandbox processes. They
receive only the user-approved privacy access required for the configured state
root. The bundled LaunchAgent uses `BundleProgram`; it must not launch an
unbundled shell as the responsible executable.

The expected configured root on this machine is `/Volumes/ext/state`, marked by
`.dotfiles-ai-state`. The implementation must additionally pin the expected
volume UUID. A path and sentinel match without the UUID match is insufficient.

## Full Disk Access

**FDA** means **Full Disk Access**, the macOS privacy permission shown under
**System Settings > Privacy & Security > Full Disk Access**. It is a local,
per-user operating-system decision. It is not a Unix mode-bit grant and cannot
be made durable by `chmod`, `sudo`, or a larger file-descriptor limit.

The current FDA entry for
`~/.local/bin/herdr-launchagent-supervisor` is an approved stopgap. Keep
it enabled through durable-host activation and the rollback soak. Do not remove
it automatically.

For the durable host:

1. Open **System Settings > General > Login Items & Extensions** and approve the
   background item registered by `Herdr Host.app`.
2. Open **System Settings > Privacy & Security > Full Disk Access**.
3. Add `~/Applications/Herdr Host.app` with the `+` control and enable it. Use
   Command-Shift-G in the file chooser if the user Applications directory is not
   visible.
4. Confirm with `herdr-host doctor` that the responsible bundle identifier,
   signing fingerprint, and designated requirement are the expected values. If
   macOS presents a bundled helper rather than the outer application, record the
   exact displayed item and require `doctor` to prove that it belongs to the
   expected signed bundle before approving it.
5. Run the host-owned read/write probe. Do not infer approval from a probe run by
   Terminal, Kitty, `sudo`, `stat`, Git, Bash, or OpenCode directly.

Never grant FDA individually to Bash, Git, Node, Bun, OpenCode, or every terminal
application as a substitute for a stable responsible host. Never edit `TCC.db`,
run `tccutil reset` as routine recovery, or script-click the privacy UI. Those
actions broaden or destroy user consent and make the next incident harder to
attribute.

## Health Model

AUTH-016 must install these non-mutating operator interfaces before activation:

```sh
herdr-host status --json
herdr-host doctor
herdr-host registration-status --json
herdr-host preflight --if-active
```

`status --json` reports the last completed host-owned probe. `doctor` validates
registration, responsible-code identity, configured volume identity, sentinel,
and current read/write access. Neither command starts, stops, or restarts Herdr.

| State | Meaning | Runtime behavior | Operator action |
|---|---|---|---|
| `starting` | The host has not completed its first identity and access probe | Do not restore or start OpenCode sessions | Wait for the bounded first probe; inspect `doctor` if it does not complete |
| `healthy` | Expected UUID, mount, sentinel, and atomic read/write probe all pass | Permit managed Herdr/OpenCode starts and capture | No action |
| `degraded_permission` | The responsible host received `EPERM` or a macOS System Policy denial | Circuit-break new starts, restores, capture writes, and other state-root writes; preserve every existing process | Verify FDA identity and wait for a bounded retry; do not restart |
| `degraded_unavailable` | The configured volume or state root is absent, or the probe returns an availability/I/O failure | Fail closed and preserve existing processes | Restore the correct device or investigate storage; do not create replacement directories at the mount path |
| `degraded_unavailable` with `error_category=wrong_volume` | `/Volumes/ext` exists but its UUID does not match | Stop before the sentinel or write probe; never read or write managed state | Unmount the replacement and mount the expected volume; do not recreate the sentinel |
| `recovering` | A degraded host has regained preliminary access but has not completed the full identity and atomic read/write sequence | Continue blocking new starts and writes | Wait for the complete probe; investigate flapping if it returns to a degraded state |

The host probes at startup and periodically. A failure enters the matching
degraded state immediately and produces one state-change notification, not a
notification for every retry. Retries use bounded backoff with a documented cap.
Recovery requires, in order, the expected UUID, the expected sentinel, a read,
and an atomic create/write/sync/remove probe in a dedicated health directory.
Only then may the host publish `healthy` and reopen the circuit breaker.

Recovery never restarts the host, Herdr server, panes, or OpenCode processes.
Existing processes may become usable when macOS access returns. A prompt that
already failed to send must be retried by the operator; it is not replayed
automatically.

Before AUTH-016 is deployed, the following commands provide partial diagnostics
but do not replace a host-owned probe:

```sh
launchctl print "gui/$(id -u)/dev.dotfiles-ai.herdr-server"
herdr status server
diskutil info /Volumes/ext | rg 'Mount Point|Volume UUID|File System Personality'
/usr/bin/log show --last 30m --style compact \
  --predicate '(subsystem == "com.apple.TCC") OR (process == "sandboxd")' \
  | rg 'herdr|opencode|/Volumes/ext|SystemPolicy|attribution'
```

## Incident Recognition

Treat the following cluster as an external-volume privacy incident until the
responsible host proves otherwise:

- OpenCode reports `Failed to send prompt` and `Unexpected server error` across
  several otherwise unrelated sessions.
- Shells whose current working directory is on `/Volumes/ext` report
  `getcwd: cannot access parent directories: Operation not permitted`.
- Node or npm raises `EPERM: process.cwd failed` or `uv_cwd`.
- Git, Bash, or OpenCode descendants receive `Operation not permitted` for paths
  that still exist on a mounted, healthy disk.
- macOS unified logs show TCC attribution failure, `missing auth_value`, or System
  Policy denials for the Herdr responsibility chain.

OpenCode/Bun may summarize the same failure as:

```text
An unknown error occurred, possibly due to low max file descriptors
```

That message is not evidence of descriptor exhaustion. Do not run
`ulimit -n 2147483646` or change the system-wide `launchctl limit maxfiles`
unless independent process-level descriptor evidence actually shows exhaustion.
In the observed incidents, the decisive error was `EPERM`, not `EMFILE` or
`ENFILE`.

## Immediate Incident Response

1. In any broken shell, run `cd /` (or another known internal directory) before
   diagnostics. This only makes the operator shell usable; it does not repair
   external-volume access.
2. Preserve the existing Herdr, pane, and OpenCode processes. Do not open a wave
   of replacement sessions, restart the LaunchAgent, log out, reboot, or kill
   children as a first response.
3. Run `herdr-host status --json` and `herdr-host doctor` when the durable host is
   deployed. Under the legacy deployment, collect the partial diagnostics above.
4. Confirm the correct volume is mounted and compare its UUID with the recorded
   expected UUID. A successful root-shell `stat` is only storage evidence, not
   Herdr privacy evidence.
5. If the state is `degraded_permission`, verify that the exact responsible host
   remains enabled in FDA. Do not add broad interpreters or edit TCC state.
6. Wait for the bounded health retries. The system is intentionally allowed to
   self-recover without process replacement.
7. After the host publishes `healthy`, retry one failed OpenCode action. If it
   succeeds, allow normal work to resume. No new Kitty window is required.
8. If access remains degraded, preserve the process tree and collect the evidence
   listed under Escalation. A restart is a separate maintenance decision and is
   forbidden when the correct volume or a safe session inventory is unavailable.

When the host is healthy again, there is no benefit in restarting it merely
because the incident occurred. The 2026-08-28 incident recovered after waiting
and without a new Kitty window or Herdr restart, so no restart was warranted.

## Stable Signing Identity

The durable host must never be deployed with an ad-hoc signature. Ad-hoc identity
is tied too closely to exact code content for a reliable privacy grant across
rebuilds. AUTH-016 uses one machine-local, self-signed code-signing identity so
successive reviewed builds share a stable designated requirement.

### One-Time Provisioning

Provisioning is an explicit, interactive operator action:

1. Open **Keychain Access** and select the `login` keychain.
2. Choose **Keychain Access > Certificate Assistant > Create a Certificate**.
3. Name it `Herdr Host Local Code Signing`, choose **Self Signed Root** as the
   identity type, and choose **Code Signing** as the certificate type.
4. Keep non-code-signing trust purposes at their defaults. If local verification
   requires a trust override, set only **Code Signing** to **Always Trust** and
   authenticate the change.
5. Keep the private key in the login Keychain. Its access control may allow only
   `/usr/bin/codesign` for unattended managed builds; never select “Allow all
   applications to access this item.”
6. Record the certificate's SHA-256 fingerprint, subject, serial number, validity
   dates, and emitted designated requirement in machine-local operator metadata.
   The private key is never written to managed configuration or logs.

Verify discovery before any build:

```sh
security find-identity -v -p codesigning
security find-certificate -a -c 'Herdr Host Local Code Signing' -Z \
  "$HOME/Library/Keychains/login.keychain-db"
```

The managed build selects the identity by the configured SHA-256 fingerprint,
not by a non-unique display name. It fails closed if the fingerprint is absent,
expired, lacks a private key, or resolves ambiguously. It must not fall back to
ad-hoc signing.

Sign nested executables and helpers first, then sign the outer application with
the same identity. Do not use `codesign --deep` to conceal an unsigned or
differently signed nested component. Verify every signed component and the outer
bundle:

```sh
codesign --verify --strict --verbose=4 "$HOME/Applications/Herdr Host.app"
codesign --display --verbose=4 "$HOME/Applications/Herdr Host.app"
codesign --display --requirements - "$HOME/Applications/Herdr Host.app"
```

Before activation, build the bundle twice from reviewed source and verify that
each build satisfies the other build's designated requirement. Also verify that
an ad-hoc build and a build signed by a different certificate do not satisfy it.
The recorded requirement and fingerprint are deployment evidence, not secrets.

### Backup, Rotation, and Removal

Loss of the private key requires a new identity and a new privacy approval. If
continuity across a machine rebuild is required, the operator may export the
certificate and private key as an encrypted PKCS#12 backup to a separately
protected backup system. Never store that backup in Git, the OpenCode state
root, an unencrypted external-volume directory, or logs. Document the backup's
location and recovery owner without recording its password.

Rotation is never automatic. For expiration, loss, or suspected compromise:

1. Create a replacement identity with a new unique name and record both old and
   new fingerprints.
2. Build and verify a separately staged bundle with the new identity.
3. Register the staged host, grant its displayed code FDA explicitly, and pass
   the host-owned probe before changing the active Herdr owner.
4. Perform the normal controlled activation and rollback soak.
5. Only after the rollback window closes, manually disable the old FDA item and
   remove the old certificate/private key from Keychain if policy requires it.

Never delete a certificate, private key, FDA record, Login Item, or old host as a
side effect of build, activation, rollback, or uninstall. Identity retirement is
a separately reviewed operator action.

## Migration and Activation

Migration is additive until the controlled handoff. It must not disturb the
active AUTH-014 supervisor or server while preparing the new host.

| Gate | Required evidence | Stop condition |
|---|---|---|
| 1. Identity | Exact configured fingerprint resolves to one valid private-key identity | Missing, ambiguous, expired, or ad-hoc identity |
| 2. Build | Swift and nested native components compile from reviewed source; inside-out signatures and strict verification pass | Compile warning/error, signature mismatch, or unstable designated requirement |
| 3. Stage | `Herdr Host.app` is installed atomically under `~/Applications`; its bundled plist uses `BundleProgram` | Bundle path, ownership, mode, plist, or nested-code mismatch |
| 4. Register | The application registers its agent with `SMAppService.agent(plistName:)`; macOS reports the expected Login Item | Registration error or unexpected responsible item |
| 5. Consent | Operator approves the exact Login Item and FDA item | Approval absent, broad substitute grant proposed, or identity cannot be proven |
| 6. Probe | Probe-only mode validates expected UUID, sentinel, read, and atomic write without starting Herdr | Permission, availability, I/O, wrong-volume, or privacy-log failure |
| 7. Inventory | Exact live pane/OpenCode inventory and rollback artifacts are available | External state inaccessible, duplicate ownership, or incomplete rollback |
| 8. Activate | Operator separately approves one managed ownership handoff | No explicit approval or any prior gate stale |
| 9. Verify | New ancestry, server health, exact session identities, host health, logs, and one fresh OpenCode action pass | Lost/duplicated session, old and new owners both active, or degraded health |
| 10. Soak | Sleep/wake and a same-identity source rebuild pass without a renewed grant | Recurrence, identity drift, or state loss |

The activation helper must present the live process/session impact and require an
explicit confirmation. It may use the existing bounded live-handoff protocol;
it must not silently fall back to killing the server. The legacy plist,
supervisor, and FDA entry remain intact through the soak even when they are no
longer active.

### Probe-Only Staging Commands

Set `data.dotfiles_ai.herdr.host_enabled = true`, the exact
`signing_identity_sha256`, and `state_volume_uuid` in the machine-local chezmoi
configuration. Then preview and apply the managed build:

```sh
chezmoi diff
chezmoi apply
herdr-host registration-status --json
herdr-host register
herdr-host open-login-items
```

Approve the registered background item and grant FDA to the exact
`~/Applications/Herdr Host.app` identity using the manual steps above. Only after
ServiceManagement reports `enabled` can the registered agent own valid probe
evidence:

```sh
herdr-host registration-status --json
herdr-host probe
herdr-host doctor
herdr-host status --json
```

The build creates a signed `Herdr Host.app`, direct `herdr-host` symlink, and a
mode-`0600` `probe_only` ownership record. It does not call `register`, alter the
legacy LaunchAgent, or restart a process. `register` uses the distinct
`dev.dotfiles-ai.herdr-host-agent` label. ServiceManagement starts that agent in
probe-only mode; it still may not spawn or take ownership of Herdr. Stop after
the probe-only health and consent gates unless a separately reviewed activation
command and explicit restart approval are both available.

If the canonical app already exists, a rebuild preserves it and every earlier
candidate, then writes a new versioned
`~/Applications/Herdr Host.pending.<UTC>-<pid>.app`. Inspect candidates without
executing them:

```sh
find ~/Applications -maxdepth 1 -name 'Herdr Host.pending.*.app' -prune -print
codesign --verify --strict --verbose=4 \
  ~/Applications/'Herdr Host.pending.<exact-candidate>.app'
codesign --display --requirements - \
  ~/Applications/'Herdr Host.pending.<exact-candidate>.app'
```

There is no approved pending-to-canonical promotion command in this probe-only
slice. Do not replace a registered canonical bundle by hand. After review, an
unwanted exact candidate may be moved to Trash for recovery; never use a broad
glob for removal. A future updater must preserve the canonical bundle for
rollback, prove mutual designated requirements, and separately coordinate
probe-only unregister/promote/re-register before activation is available.

## Manual Recovery and Restart Policy

Health recovery is automatic; process recovery is manual. The host may retry its
probe and reopen the circuit breaker, but it may never restart Herdr, panes, or
OpenCode on an `EPERM`, missing mount, I/O error, wrong UUID, or transition back
to `healthy`.

A process restart may be considered only when all of these are true:

- the expected volume UUID and sentinel are present;
- the host-owned read/write probe is `healthy` and stable;
- an exact live session inventory and tested rollback are available;
- the problem is a dead or invalid process, not an unresolved privacy flap; and
- the operator has reviewed the impact and explicitly approved the restart.

Use only the managed recovery/activation command delivered and tested by
AUTH-016. Until that command and its process-preservation tests exist, there is
no approved emergency `launchctl kickstart -k` procedure. Directly restarting the
legacy label can terminate the responsibility supervisor and its descendants.

If the external root is denied and the session inventory cannot be read safely,
do not restart to “see if it helps.” Preserve the processes and restore access
first. If access returns, retry failed prompts manually; do not replay requests
or recreate panes automatically.

## Rollback

Before activation, any target-host failure rolls back by unregistering or
quarantining only the staged target. The active legacy supervisor and Herdr
server remain untouched.

After activation:

1. Stop new managed starts and collect target-host health, signing, TCC, and
   process evidence.
2. If a healthy server is still running, prefer the tested live handoff back to
   the retained legacy owner. Never create two socket owners.
3. Restore the retained legacy plist and supervisor atomically, then activate it
   only with explicit operator approval and the same session-impact checks used
   for forward activation.
4. Verify the expected volume, server owner, pane count, exact OpenCode session
   identities, and one external-volume read/write action.
5. Keep the target application, identity, health evidence, FDA record, and Login
   Item available for diagnosis until the rollback review closes.

Rollback never edits, migrates, or restores the OpenCode database as a side
effect. It never recreates `/Volumes/ext`, changes the sentinel, deletes a TCC
record, or removes a signing identity automatically.

## Validation and Soak

The following gates are required before durable activation:

### Static and Automated Validation

- Compile Swift and C/native code with warnings treated as errors.
- Run `plutil -lint` on the application and bundled LaunchAgent plists.
- Run `bash -n` on every rendered deployment and recovery script.
- Run `codesign --verify --strict --verbose=4` separately for every nested
  executable and for the outer bundle.
- Build twice and prove mutual designated-requirement compatibility.
- Simulate `EPERM`, absent volume, `EIO`, wrong UUID, lost sentinel, recovery,
  and probe flapping. Every case must fail closed without restarting processes.
- Prove the wrong-volume case performs no write.
- Prove health status/log writes are atomic, mode-restricted, bounded, and free
  of prompt/session content.
- Preserve exact OpenCode IDs, reject duplicates, retain launch pacing, and
  continue capture after individual restore failures.

Focused repository validation:

```sh
uv run --group test pytest -q \
  tests/test_herdr_launchagent.py \
  tests/test_portable_distribution.py \
  tests/test_opencode_control_plane.py
git diff --check
```

### Controlled Live Validation

1. Preview managed changes and prove they do not restart or replace the active
   server during build, install, registration, or consent.
2. In probe-only mode, verify the target host can read and atomically write the
   expected external state root.
3. After approved activation, verify the signed responsible ancestry, exact
   server identity, exact pane/session inventory, and a fresh-pane read/write.
4. With separate disruption approval, toggle FDA off for the durable host.
   Confirm `degraded_permission`, one notification, clear OpenCode preflight
   failure, no write, and no restarted or terminated process.
5. Toggle FDA back on without restarting the host. Confirm `recovering`, then
   `healthy`, and manually retry one failed OpenCode action.
6. Soak through at least one sleep/wake cycle and one reviewed source rebuild
   signed by the same identity. Neither may require a new FDA grant.

Fault injection is never performed during an unplanned incident. It requires a
captured inventory, a rollback-ready maintenance window, and explicit approval.

## Data and Privacy

All authoritative Herdr/OpenCode state, databases, session manifests, worktrees,
and projects remain under the configured external state root. The first durable
slice must not copy any of those artifacts to the internal disk.

The host may persist only minimal, non-authoritative health metadata under:

```text
~/Library/Application Support/Herdr Host/health.json
~/Library/Application Support/Herdr Host/ownership.json
```

Allowed fields are host version, bundle identifier, public signing fingerprint,
expected and observed volume UUID, sentinel result, health state, coarse error
category or errno, state-transition timestamps, probe duration, and the
`probe_only` or `active` ownership mode. The status directory must be mode
`0700`; regular status files must be mode `0600` and replaced atomically. The
records never include the configured state-root path.

The internal record must never contain:

- prompts, responses, message fragments, or tool payloads;
- OpenCode databases, configuration bodies, or session manifests;
- session identifiers, project/repository names, or full accessed paths below
  the configured root;
- environment dumps, command lines, credentials, tokens, Keychain contents, or
  private-key material; or
- file contents read during a probe.

Logs must rotate under an explicit bounded size/count or age policy before
activation; unlimited retention is prohibited. `health.json` is a replaceable
last-known observation, never recovery authority. Deleting it while the host is
stopped is safe; the host must reconstruct health from a new probe. Any future
proposal to copy a session manifest internally requires a separate privacy and
recovery decision rather than an expansion of this allowlist.

## Incident Evidence and RCA Baseline

The recurring incidents reported on 2026-08-25, 2026-08-27, and 2026-08-28 share
the same boundary failure: existing Herdr/OpenCode descendants lost access to
the mounted external volume while unrelated fresh processes could still access
it. Disk presence and Unix permissions were not the limiting condition.

For the 2026-08-28 recurrence, unified logs recorded `missing auth_value` and a
failed TCC attribution chain at 17:34:08, followed by System Policy denials for
the Herdr/OpenCode process tree. The last observed denial was at 17:53:32. The
operator added the legacy supervisor to FDA, an FDA-related registration was
observed around 17:54:23, and OpenCode recovered without a Herdr restart or new
Kitty window. Because the denials stopped before that observed registration,
the evidence does not prove whether the FDA change caused recovery or whether
macOS self-healed immediately beforehand.

The disk remained mounted, the configured paths remained present, and descriptor
exhaustion was not observed. The `low max file descriptors` suggestion was a
generic wrapper around the underlying permission failure. Increasing global
descriptor limits is therefore outside this RCA and this repair.

AUTH-014's raw, ad-hoc-signed responsibility supervisor narrowed the privacy
subject and initially passed live verification, but recurrence shows that exact
binary responsibility alone is not durable enough. AUTH-016 therefore changes
the durable boundary to an application bundle, modern ServiceManagement
registration, a stable designated requirement, explicit FDA consent, and a
health circuit breaker. The solution does not depend on Apple support replying
to an incident report.

## Escalation Evidence

If denial recurs after durable activation, preserve and attach:

- `herdr-host status --json` and `herdr-host doctor` output;
- outer and nested `codesign --display --verbose=4` output, designated
  requirements, and public certificate fingerprint;
- ServiceManagement/Login Item status and the exact FDA item shown in System
  Settings, without private Keychain material;
- the expected and observed volume UUID, sentinel result, and mount metadata;
- the bounded unified-log window spanning the first denial and recovery;
- Herdr owner/server ancestry and counts, without prompt or environment content;
  and
- whether access recovered without restart and which failed action required a
  manual retry.

Do not wait for external support before applying the fail-closed behavior in
this runbook. Support feedback may inform a later design review, but it is not a
runtime dependency.
