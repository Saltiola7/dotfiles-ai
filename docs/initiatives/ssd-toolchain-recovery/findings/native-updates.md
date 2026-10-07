# Native installer qualification — 2026-10-06

Status: partial qualification; Discovery-owned, not Build-ready.
Source checkout: ae6eace. Profiles: distribution PROFILE.md/PRODUCT.md and
codex_control_plane/PROFILE.md. Risk: elevated. DKS unavailable; no existing
Graphify graph in this checkout. Source and isolated native probes are authority.

## Observed results

| Probe | macOS ARM64 | Fedora 44 ARM64 |
|---|---|---|
| Official OpenCode installer, 2.0.21, isolated HOME/XDG | Passed | Passed |
| Native `opencode upgrade 2.0.22`, automatic curl-method detection | Passed | Failed without `which`; passed with genuine Fedora `which` package on isolated PATH |
| `debug paths` before/after update | Byte-identical | Byte-identical |
| Official Codex standalone install 0.159.0 then update 0.160.1 | Passed | Passed |
| Repeat Codex 0.160.1 installer twice, custom bin directory | Same target and binary digest; synthetic state marker retained; no shell-profile writes | Not run |
| Isolated OpenCode service version before/after install/restart | 2.0.21 / 2.0.21 / 2.0.22; PID unchanged until restart | Not run |

Follow-up on both platforms: native API-created synthetic session metadata and
queued synthetic input (`resume: false`) remained exactly equal after 2.0.21 to
2.0.22 update and service restart. Both platforms retained the old server PID and
version until restart, then reported a new PID and 2.0.22. No agent generation or
provider request was invoked. Scratch services were stopped in finalization.
One macOS attempt failed with upstream update-service HTTP 500; a fresh retry
passed and the failed attempt/logs remain retained. This proves synthetic persisted
identity/input continuity, not authenticated live TUI or pane restoration.

Version pairs are qualification inputs, not claims about today's newest stable.
The probes used new empty state, no credentials or copied conversations. Native
CLI upgrade is proven; interactive `/update`, authenticated exact-session recovery,
managed chezmoi reapply and live activation remain unproven.

macOS service started and stopped using native service commands under isolated
HOME/XDG and a scratch working directory. The separate live service remained
discoverable at a different endpoint. No service registration/database edits were
used. Running service remained at the older release until explicit restart, matching
the V2 configuration documentation.

Fedora's first native update failed with `which: command not found`. Downloaded
`which-2.25-1.fc44.aarch64.rpm` with native dnf, verified it with rpmkeys (digests and
signatures OK), and extracted only its binary into the scratch dependency directory.
The same native update then passed. No system RPM installation or guest runtime
replacement occurred. Add `which` to the future guest provisioning prerequisites.

## Upstream source observations

Inspected official OpenCode V2 installer and Codex standalone installer. Public
documentation: OpenCode V2 intro, config and troubleshooting; Codex CLI installation.
Installer SHA-256 observed identically on both platforms:

- OpenCode: `bc70dd317fd12ef09350cdb1667e55e19f9e7b3d2897d3a1b750b165ae579d87`
- Codex: `150e3cf675682efeaac115aa3747add3f27887896d04ce6d0b56478d8b428bf6`

OpenCode installs to `$HOME/.opencode/bin/opencode`, writes an `opencode2` shim,
and supports `--no-modify-path`. That option left shell profiles absent in the
isolated probe. It detects architecture/libc and retrieves native npm artifacts.
Its `check_version` calls `which`; its installation does not reject a requested
older version. Thus rerunning a pinned installer is not a no-downgrade policy.

Codex defaults the visible command to `$HOME/.local/bin/codex`, configurable by
`CODEX_INSTALL_DIR`; packages live under `$CODEX_HOME/packages/standalone`.
Its installer owns release directories and the `current` symlink, verifies archive
digests, and replaces the visible command with a symlink. Explicit releases remove
the latest-channel auto-update marker; latest installs create it. Automatic-update
policy therefore needs separate inspection before choosing the live invocation.
The installer can modify shell profiles; including its bin directory in PATH
avoided that during these probes. `CODEX_NON_INTERACTIVE=1` avoids launch/removal
prompts. The default visible path collides with the existing managed state guard.

## Keep / replace / retire map

- Keep `dot_local/bin/executable_opencode.tmpl` state environment, absent-volume
  guard, Herdr preflight and exact-session pacing responsibilities (lines 3–59).
  Replace the `exec-managed` package route (lines 60–68) with a qualified native
  executable path. Its unconditional Herdr `--auto` append at line 42 must be
  narrowed for native maintenance subcommands; this is not installer behavior.
- Keep `dot_local/bin/executable_codex.tmpl` CODEX_HOME selection and home validation
  (lines 4–21). Replace recovery/release-lock routing (lines 22–25) only after
  qualification. Installer target must not overwrite this guard.
- Keep `dot_local/bin/executable_codex-project` configuration projection/recovery
  and `validate_home` (lines 251–298). Its package validation/exec path (301–397)
  requires fixed digests, regular non-symlink binaries and mode 0700: incompatible
  with native standalone symlinks. Do not remove unrelated projection recovery.
- `dot_local/bin/executable_opencode-update-all` `healthy` (534–555) and
  `exec_managed` (572 onward) bind launches to admission, fixed digest and mode.
  Do not point native updating at the current managed binary and expect these
  checks to pass. Retain historic migration/admission evidence when retiring the
  future launch dependency.
- Replace `run_after_update-opencode.sh.tmpl` and
  `run_after_update-codex.sh.tmpl` fleet-updater invocation with qualified local
  ownership. Bootstrap should preserve an already installed newer native release;
  explicit update remains a separate action.
- Review `run_onchange_before_install-opencode.sh.tmpl`,
  `run_onchange_after_install-codex.sh.tmpl`,
  `run_onchange_after_install-01-remote-opencode.sh.tmpl`, and
  `dot_local/bin/executable_opencode-install.tmpl` together. Existing remote
  installer has its own fixed artifact path and release-lock short circuit.
- Coordinate guest system wrapper/provisioning in
  `private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl` and host declaration/PATH
  changes in dotfiles. The observed guest wrapper also has a V1-era command list;
  native `service`, `session` and `update` routing needs explicit qualification.

These are proposed write boundaries, not permission to launch or delete whole
updater files. Trace remaining callers before deciding actual retirement scope.

## Candidate and remaining qualification

### Codex native command and automatic-update policy follow-up

Native `codex update` at 0.160.1 passed on macOS and Fedora ARM64 with the custom
`CODEX_INSTALL_DIR` exported. Both selected the standalone installer, retained
the custom visible command, and did not create the default `~/.local/bin/codex`.
The host synthetic preservation marker remained intact. Upstream selected 0.160.1,
so this is native-command integration evidence; the earlier explicit installer
0.159.0-to-0.160.1 test supplies version-to-version evidence.

Upstream source at `rust-v0.160.1` establishes a distinct daemon update policy:
`codex-rs/app-server-daemon/src/settings.rs` defaults `auto_update_enabled` to true
and the interval to 60 minutes. `update_loop.rs` schedules the first ordinary check
after five minutes and later uses that interval; it can request daemon restart.
`codex-rs/tui/src/update_action.rs` invokes the standalone installer through a shell
and inherits the install-directory environment. `lib.rs` locates daemon settings
at `$CODEX_HOME/app-server-daemon/settings.json`.

An isolated native `codex doctor --json` confirmed that
`{"updater":{"autoUpdateEnabled":false}}` in that settings file reports
`automatic updates: disabled (configured)`, while startup update checks remain
true and `updates.status` is OK. Overall doctor exited 1 because this deliberately
credential-free fixture has no login; it also reported a WebSocket reachability
warning. This is policy parsing evidence, not an authenticated health pass or a
long-running scheduler test.

Future managed projection must merge that setting without replacing unrelated
daemon settings, and the launcher must export the selected native install directory.
Do not confuse `check_for_update_on_startup` with daemon automatic installation.
Preserve native manual updates and notification behavior.

Prefer official standalone installers: OpenCode's normal install location already
separates executable from managed guard; Codex supports a distinct install directory.
Retain existing XDG/CODEX_HOME routing. Existing native package manager declarations
must not install a competing owner. Use installer PATH suppression where supported.

Before readiness:

1. Qualify Codex daemon policy persistence through managed projection and running
   service lifecycle. Native manual update preserves custom install directory on
   both ARM64 platforms; same-release installer idempotence is proven on macOS,
   not full managed reapply.
2. Exercise native `/update`, authenticated exact-session restoration, guarded launch,
   absent-volume failure, background-service environment and twice-repeated targeted
   chezmoi apply; current probes establish only a subset of that matrix.
3. Qualify existing guest wrapper routing. Linux ARM64 isolated service restart
   now passes. Linux x86_64 remote support is source-inspected only; no remote
   target was upgraded. Subsequent operator decision INT-023 defers x86_64 native
   activation and preserves its current route; runtime evidence is not an ARM64
   launch prerequisite, but shared-template regression checks remain required.
4. Approved successor policy now has a precedence map in
   `features/native-platform-updates.md`; Product Intent, profiles and historical
   feature/Initiative pointers are reconciled in Discovery. Registered migration
   authority and its original manifest are retained. Implement only after the
   remaining qualification and launch gates.
5. Finish caller/test inventory, concrete bootstrap/transition plan, applicability
   plan and committed dependencies before any Build receipt.

Affected check candidates: existing distribution, Codex control-plane, OpenCode V2
authority, Herdr session-recovery and Lima suites; template/shell validation; native
update/service/path probes; operator UI recovery. No configured gate is marked
passed by this research note. Private raw logs remain outside Git.
