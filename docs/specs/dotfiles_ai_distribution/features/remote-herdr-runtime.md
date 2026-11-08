# Remote Herdr Runtime Selection (RRW-007F)

## Authority and readiness

INT-077 and INT-079, coordinator Discovery #508, authorize one remote user's
selection of `herdr-core` or `tui`. RRW-007D is the delivered prerequisite.
Risk is critical: switching must preserve session identities and layout without
ever running an agent session under both runtimes. This document records the
Domain and Behavior contract; version-qualified native interfaces, implementation
and qualification remain pending. A registered cycle is not runtime readiness.

The approved handoff amendment makes the foundation the sole user-local core
installer and integrity owner. Fork A coordinates reviewed version changes,
desktop adoption/runbook (INT-078), setup interview and live migration
(RRW-015/INT-080). Fork B owns that installer plus selection, services, restore
and switching. No second installation or static `serve` supervisor is added;
core's own upstream transient units remain process owners. Missing/incompatible native
interfaces reopen implementation readiness.
Bookmarking is deferred (INT-081); migrated agent panes stay live.

## Domain and boundaries

- **Selected runtime:** explicit per-user local configuration, either core or
  TUI; never inferred from OS Login, process discovery or desktop focus.
- **Active runtime:** the one verified runtime permitted to own that user's
  live agent panes. Installed does not imply active or selected.
- **Layout:** spaces, tabs, labels/order, pane topology and working-directory
  mappings. Native IDs may differ across runtimes; agent session identities do
  not. Sensitive titles, paths and session data never enter shared Git/logs.
- **Live session:** the exact saved OpenCode identity running in its intended
  pane and directory, not merely a shell, saved record or recognized process.
- **Switch transaction:** private, recoverable ownership transfer from one
  runtime to the other. The source must stop and its agents be proven absent
  before target agents may start. Uncertainty blocks target activation.
- **Restore:** recreating live agent sessions after runtime restart/VM boot,
  preserving identity and mapping without duplicated execution.

Herdr TUI/core ownership is distinct from the shared OpenCode service delivered
by F01. This slice does not silently disable that service or change its purpose.
The owner explicitly selected preservation of that shared backend and in-flight
turns during switching: transfer Herdr client ownership, proving the old clients
exited before attaching the same session IDs in the target. Do not abort native
server-owned turns or equate PTY termination with backend execution termination.
Existing macOS/Lima/Linux-workstation behavior is outside remote selection.
User-manager lingering is already owned by Fork A, not enabled by this source.

## Selected interfaces and binary contract

- Setup writes `[data.dotfiles_ai.herdr] runtime = "herdr-core"` or `"tui"` in
  the user's local foundation TOML. `tui` is the compatibility default, not an
  inferred owner preference. Invalid values fail render and foundation checks.
- Native TUI `session.resume_agents_on_restore` is true only for TUI selection.
  `herdr-opencode-restore`, including its watcher and paced launches, also honors
  this gate. Non-remote behavior retains its existing defaults.
- Core 0.1.18 is installed at `~/.local/bin/herdr-core`; add relative
  `hc -> herdr-core` only if no entry exists, preserving even dangling aliases.
  `remote-herdr-core check` reports drift without repair; explicit `install`
  converges the reviewed bytes without executing an untrusted existing binary.
  Matching existing bytes/mode are adopted without download/inode replacement.
- Verify release archive SHA-256
  `5b2f97cb4b2a9d7a6b2cc5942628203ed9fbb7cc0c2b4b09ad8a6f5648e246b7`
  and independently verified binary SHA-256
  `baa9d208d6400556a6e379152455fe1301e0e1acdbc114ff60b79d64425179cf`.
  The reviewed archive has three regular members: `herdr-core`, `LICENSE`,
  `THIRD-PARTY-NOTICES`. Bound parsing and validate both hashes before atomic
  publication. Source pins cannot be overridden through local configuration.
- A busy native core lock blocks replacement; matching-byte adoption need not
  stop it. Lock inspection is bounded to documented user-local state roots,
  is advisory, and does not prove absence of holders or protect against a user
  starting another same-UID session concurrently. Nonstandard relocated state
  needs separate review. Installer checks never launch or stop core.
- The runtime identity is the default core session with `HC_SESSION` unset,
  state `~/.local/state/herdr-core/default`, config
  `~/.config/herdr-core/config.toml`, and the native default socket under
  `/run/user/<uid>/herdr-core/`. The desktop adopts a compatible pinned core;
  users decline desktop or machine-update replacement offers. App-side config
  remains unmanaged on the Mac. No private runtime state enters source control.
- Raw core calls use an existing owned Unix endpoint and plain JSON-RPC, require
  generation 1/version 0.1.18, enforce bounded messages and never retry an
  uncertain mutation. A probe must never auto-start the unselected runtime.
  On Linux, endpoint checks reject group/world write access (which grants socket
  connection), retain protected-parent and peer-UID verification, and allow
  harmless read/execute bits from the upstream transient service's umask.

The native terminal/schema contracts are pinned to core source `3965a46`, TUI
`2ecf19a` and desktop `93b097f`. Core's `keep` restores a shell, not an agent;
the adapter must explicitly restore sessions and remap the app document.
SIGTERM/restart preserves programs; runtime exit is not a stop proof.

The pure adapter accepts native on-disk TUI snapshot version 3 or labelled
space plans. TUI `api snapshot` is a different, observational schema and must
not be written as `session.json`. A labelled space plan supplies each tab as
`{"label": "exact original label", "steps": [...]}`. The historical producer's
bare step arrays lack labels and refuse fidelity-sensitive import. It must be
updated by Fork A, not guessed or rewritten here. Conversion preserves order,
session identities and supported binary split geometry; unsupported/lossy
layouts refuse rather than silently flatten. Pure conversion is not native
restore evidence.

## Behavior

1. Given an explicit valid selection, when the user's manager boots, only that
   runtime starts and resumes its agent sessions; the other remains installed
   and stopped, with its restore mechanisms disabled.
2. Given core selection and migrated panes, when core or the VM restarts, every
   migrated OpenCode pane resumes the same session live in its mapped directory.
   Shell-only reconstruction is a failed acceptance check.
3. Given a switch request, when source capture and validation succeed, preserve
   a private recoverable layout/session inventory, stop the source and verify
   its agents are gone, then populate/start the target and verify fidelity.
4. Given uncertain process ownership, an occupied target, conflicting sessions,
   invalid mappings or an incompatible native version, refuse before launching
   target agents. Never manufacture evidence that the old runtime stopped.
5. Given failure or interruption at a switch boundary, retain the transaction
   and source state. Recovery must not start both runtimes, erase mappings or
   silently discard a session. The exact rollback/resume procedure must be
   defined and tested before this feature is ready.
6. Given concurrent switch/apply/boot operations, serialize the user's ownership
   decision and refuse conflicting activation; another user's choice is isolated.
7. Given config selection is changed, provide one documented convergence path
   and switch command. Applying configuration must not overwrite sensitive
   runtime inventories or lose the explicit selection on a later apply.
8. Given an unowned target layout, ordinary switching refuses replacement.
   An explicit replace-target option may adopt it after private backup, retaining
   terminal records and refusing unknown live agents. This is the approved
   initial migration path for the desktop's plain-shell copy. Subsequent ordinary
   switches may update only previously adapter-owned layout, never overwrite
   unexplained target edits.

## Implementation and validation blockers

### Controller interface (local implementation; native acceptance pending)

```sh
remote-herdr selected
remote-herdr switch herdr-core --replace-target
remote-herdr switch tui
remote-herdr switch herdr-core --from-file "$HOME/migration/labelled-plan.json" --replace-target
remote-herdr restore
remote-herdr recover
```

`switch` captures the selected live source unless `--from-file` is supplied.
File input accepts canonical schema version 1, native TUI snapshot version 3,
or the labelled space-plan array described above. File import requires its source
runtime stopped and the imported session clients absent. It does not stop an
unrepresented live layout or grant permission to replace an occupied target.
`--replace-target` is required to replace an unowned layout even when all its
panes are shells; native terminal records remain retained. Previously owned
layouts with unexplained later edits refuse even with this option.

The private controller store is
`~/.local/state/dotfiles-ai/herdr-runtime/`, mode 0700, with mode-0600 JSON and
a nonblocking advisory owner lock. `transaction.json` retains phase, capture,
plan, transaction ID and receipt; backups and completed history are retained.
The controller persists mutation intent before stop, preparation, selection,
restore and verification. `manifest.json` binds the current owned layout to its
runtime, exact session identities and per-pane native terminal receipt. Store
files are neither source-owned nor an interchange format to hand-edit.
Core socket readiness does not establish kept-terminal readiness. Preparation
and recovery wait within the existing bound for live kept records without PIDs,
then apply full actual-program proof. This wait only observes; persistent pending
spawns or unknown programs still refuse without creating or killing terminals.

Recovery observes stopped source PID/start-time identities, exact post-stop
snapshot fidelity, target backups, native CAS versions and transaction labels
before continuing. It does not blindly repeat an unknown terminal creation or
stop. Unknown core start must become observable; absence of a socket does not
authorize a second start. TUI write/start recovery compares the generated
snapshot and requires a proven inactive managed unit plus client absence before
starting again. Active or activating units are observed for readiness instead.
Unresolvable native outcomes remain blocked with the journal intact; no automatic
rollback, source restart, shared-service restart or discard is performed.

`remote-herdr-restore.timer` invokes the oneshot restore service at user-manager
boot and every 30 seconds after completion. It does not supervise core or replace
the native transient units. Core selection requires a migrated owned manifest;
no layout or session is invented on first boot. TUI is launched by the separate
foreground `remote-herdr-tui.service`, with no independent enable/restart policy.
Its guarded exec requires selection and a persisted controller startup intent.
The controller proves saved clients absent and retains its lock through actual
socket, layout and session readiness, not merely `Type=exec` acknowledgement.
Automatic restore refuses unfinished switches. `recover` explicitly reconciles
retained boot/switch intent. Reapply enables the timer without restarting either
runtime or the shared OpenCode service.

Core user edits become an owned baseline only after a successful source capture
and proven stop. Later unexplained target edits still refuse. Stored shell argv
is not proof of a plain-shell target: actual process argv, cwd and PID/start-time
identity are checked before destructive operations. Native OpenCode client proof
accepts the foundation wrapper's exact executable and loopback `--server`, session
and optional `--auto` expansion; arbitrary flags/endpoints remain unsupported.

OpenCode installation and native updates retain F01 ownership. Legacy asset
defaults in the source are not a pin for the remote native v2 executable. Hosted
qualification records the actual native version/hash and checks its served API
schema before creating sessions. The v2.2.6 database contract uses `session_v2`;
when that table exists, stale legacy `session` rows cannot establish identity or
directory proof. The earlier `session` schema remains supported only when the
current table is absent. The native read-only `debug paths db` resolver selects
the channel-specific filename, constrained to the user's private OpenCode data
directory. Unsupported schemas or relocated databases refuse.
The held-turn fixture uses the current top-level prompt input and projected native
context/message APIs. Native CLI services do not retain event payloads by default;
qualification must not assume historical payload retention or change service
ownership to enable it. Admission, original assistant identity, active execution and final
output are checked across a real switch without external provider credentials or
calls. Interrupted TUI boot recovery preserves an unchanged native saved snapshot,
including supported view/default fields, rather than rewriting a generated copy.

The CLI/controller and services above are not yet qualified for rollout. Native
boot, restart and bidirectional switching remain required completion gates.

Before source implementation can be accepted, qualify the pinned core's serve,
shutdown, process ownership, layout enumeration/creation, agent session start,
observation and persistence interfaces. Resolve native TUI/core schema mappings
and desktop-managed transient-unit adoption with Fork A. Neither a TUI API nor
an app-created plain-shell copy is assumed compatible with core.

Source client-exit verification uses Linux same-user procfs PID/start-time
identities plus exact CLI session references. Socket disappearance alone is not
proof. A still-live captured process, ambiguous identity, unreadable inventory
or a newly observed matching client blocks target activation. Verification uses
kernel task UIDs, not proc-inode ownership: same-user nondumpable tasks can
have root-owned proc files. Scheduling state changes do not change PID identity.
Disappearance during inventory restarts the complete observational scan, at most
three times; persistent uncertainty still refuses. Scoped proc reads never relax
the ordinary owned-file reader or expose task status/argv in diagnostics.
Native qualification must prove this against the foundation OpenCode wrapper and real Herdr processes;
synthetic procfs tests alone do not establish complete native coverage. Shared
backend processes are deliberately not killed. Same-UID users can bypass their
own controller; this is a cooperative ownership contract, not a security boundary
against the account owner.

Mandatory evidence: offline state-transition/failure/race tests, exact-version
native bidirectional switching, identity/layout fidelity, no duplicate agents,
restart and real user-manager boot restore, invalid/unknown-state refusal,
other-profile and other-user isolation, private-data diagnostics, rollback and
recovery. Mocks alone do not satisfy native acceptance. Keep 007E activation,
F01 shared-service proof and final optional-overlay disjointness intact.
All live apply, pin changes, desktop connection and owner migration remain
separately authorized Fork A work. No completion or native pass is claimed here.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary | required: transition table; who owns binary and runtime activation? |
| Interaction | required: transition table; what must stop before target agents start? |
| State | required: transition table; where does uncertainty block activation? |
| Data/trust | required: transition table; where is sensitive migration data retained? |
| Schema | not_applicable: native interface/schema qualification remains open |
| Dependency/deployment | required: transition table; what is the installation prerequisite? |
| Quantitative | not_applicable: no performance or capacity claim |

| Transition | Owner | Guard / result |
|---|---|---|
| Reviewed binary pin to installed core | Foundation; Fork A coordinates version | One installer verifies archive and binary; no desktop update owner |
| Local selection to user-manager startup | Fork B | Only selected runtime may resume agents |
| Active source to captured inventory | Switch controller | Private fidelity-checked layout/session data |
| Captured source to stopped source | Switch controller | Prove source runtime and agents stopped |
| Stopped source to live target | Native target adapter | Verify exact identities, directories, labels/order |
| Any uncertain or failed transition | Recovery controller | Retain evidence; no duplicate activation |

**Text Equivalent:** The foundation installs the reviewed core binary, with
version coordination retained by Fork A. Fork B starts
only the explicitly selected runtime. Switching first captures private state,
then proves the source stopped before any target agent starts. Target readiness
requires live session and layout fidelity. Uncertainty retains evidence and
blocks activation. Canonical source: approved INT-077/079 and this behavior
contract; native adapters remain unqualified. Owner: distribution maintainer.
Update with selection, native interface, ownership or recovery changes.
