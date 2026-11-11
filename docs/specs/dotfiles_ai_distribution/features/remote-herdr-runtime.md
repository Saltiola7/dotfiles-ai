# Remote Herdr Runtime Selection (RRW-007F)

## Authority and readiness

INT-077 and INT-079, coordinator Discovery #508, authorize one remote user's
selection of `herdr-core` or `tui`. RRW-007D is the delivered prerequisite.
Risk is critical: switching must preserve session identities and layout without
ever running an agent session under both runtimes. This document records the
Domain and Behavior contract and version-qualified native interfaces. Disposable
hosted qualification passed; a registered cycle alone is not runtime readiness,
and hosted proof is not live rollout approval.

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
  `~/.config/herdr-core/config.toml`, and native socket
  `/run/user/<uid>/herdr-core/default.sock`. The desktop adopts a compatible pinned core;
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
The layout document is named `herdr-app`: its `doc.get` response contains
`version` and `value.spaces`. Core terminal addresses bind leaf panes; document
replacement uses that observed version for CAS, never an unversioned overwrite.

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

## Implementation and qualification

### Controller interface

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
and recovery wait up to 75 seconds for live kept records without PIDs, covering
the native 60-second backoff cap plus sweep/recovery-loop margin. Other ordinary
readiness waits remain 30 seconds. Full actual-program proof still follows the
kept-spawn wait. This wait only observes; persistent pending
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
the native transient units. Core selection can adopt an already available proven
current document; no layout or session is invented on first boot. TUI is launched by the separate
foreground `remote-herdr-tui.service`, with no independent enable/restart policy.
Its guarded exec requires selection and a persisted controller startup intent.
The controller proves saved clients absent and retains its lock through actual
socket, layout and session readiness, not merely `Type=exec` acknowledgement.
Automatic restore refuses unfinished switches. `recover` explicitly reconciles
retained boot/switch intent. Reapply enables the timer without restarting either
runtime or the shared OpenCode service.

Selected-core user edits become a baseline after current-document adoption and
exact process/session proof. Unselected target replacement and unrelated ownership
conflicts still refuse. Stored shell argv
is not proof of a plain-shell target: actual process argv, cwd and PID/start-time
identity are checked before destructive operations. Native OpenCode client proof
accepts the foundation wrapper's exact executable and loopback `--server`, session
and optional `--auto` expansion; arbitrary flags/endpoints remain unsupported.
TUI stop repeats layout, exact client coverage, actual foreground-program and
PID/start-time checks after durable stop intent, immediately before native stop.
A newly busy pane or changed process inventory refuses before either stop command.

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

The disposable hosted fixture qualifies core 0.1.18, TUI 0.9.5 and the observed
native OpenCode v2.2.6 executable. It uses real native APIs/processes, the lingering
systemd user manager and two container reboots, with no external model credentials
or calls. It verifies three exact TCP-connected session clients, two spaces,
labels/order, directories and supported split geometry, private target backup and
retained terminal records, bidirectional switching, interrupted-switch recovery,
core restart/explicit-stop recovery and both selected-runtime boot phases.
The held turn keeps its original assistant/model identity, shared backend PID and
one provider request through transfer, then completes the exact expected output.
An isolated three-round kept-shell probe did not reproduce a general core stall;
full-fixture inspection observed holder-free backoff pending beyond the old
30-second adapter bound. It did not prove lost SPAWN or a claim-before-send defect.

All 19 hosted checks passed implementation head
`24de7482f3c9ccc461b998ad17c63e1501ef1afa`; exact-head and final delivery evidence
remain in the private Cycle Record. This is not live RHEL/VM, desktop connection,
two-owner rollout or acceptance of a producer that omits tab labels. Fork A owns
desktop transient-unit adoption, the setup interview and live migration/runbook.

Source client-exit verification uses Linux same-user procfs PID/start-time
identities plus exact CLI session references. Socket disappearance alone is not
proof. A still-live captured process, ambiguous identity, unreadable inventory
or a newly observed matching client blocks target activation. Verification uses
kernel task UIDs, not proc-inode ownership: same-user nondumpable tasks can
have root-owned proc files. Scheduling state changes do not change PID identity.
Disappearance during inventory restarts the complete observational scan, at most
three times; persistent uncertainty still refuses. Scoped proc reads never relax
the ordinary owned-file reader or expose task status/argv in diagnostics.
Hosted native qualification exercises the foundation OpenCode wrapper and real
Herdr processes; synthetic procfs tests alone do not establish native coverage. Shared
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
separately authorized Fork A work. No live deployment or merge is claimed here.

## Operations and maintenance

### Current-document restore and adoption (RRW-007G / INT-082)

The desktop owns layout edits. The controller owns proven session bindings, not
the whole shared `herdr-app` document. A binding identifies a stable leaf ID and
terminal address, exact session (or plain shell), directory and observed native
labels. Display position is not ownership. Renaming/reordering spaces or tabs,
resizing/splitting nodes and the app's serialization defaults are not conflicts.
The current bounded document is the baseline; unknown non-layout metadata is
retained byte-for-value, not regenerated from the migration plan.

Required behavior:

- Given a retained `restore_pending` switch whose target document was subsequently
  edited, recover reconciles the current document, updates the private plan and
  completes the same transaction after actual-program and duplicate checks.
- Given user-closed views or finished terminals, their old session bindings are
  retired from the current baseline, never recreated from the original plan.
  Native terminal records and earlier backups remain retained.
- Controller-stopped terminals are not user closures. A completed private stop
  record bound to the manifest transaction, captured document/leaf/address and
  observed labels authorizes restoration only of those recorded stopped bindings,
  after captured PID/start-time exit proof and exact-session absence. Unrelated
  or incomplete stop records never authorize resurrection. Missing current leaves
  remain closed even when the controller previously stopped their terminals.
- Given new exact `--session` clients in the current document, adopt only after
  actual argv, same-owner PID/start-time, directory, native session-store and
  account-wide duplicate-client proofs. No-`--session` home screens are not session
  identities. Directory, recency, titles and backend PID never substitute for one.
- Given a proven owned agent leaf that rebooted into a plain shell, prove the old
  client absent, stop only that proven shell, create one exact client and rebind
  only that leaf. Preserve all other current nodes, IDs, sizes, labels and metadata.
- Given no manifest, an already available selected core can establish a proven
  baseline. No document/core to adopt is a quiet no-op, not a repeatedly failing
  timer. No baseline authorizes taking over an unselected runtime.
- Given concurrent desktop writes, CAS uses the latest observed version. A stale
  version refuses safely without replaying terminal creation. Recovery observes
  durable intent and reconciles the existing effect before any further mutation.
- Given unnamed TUI labels, compare native null custom names through their live
  display projection (`~` can identify home; tabs use one-based tab numbers), not
  as explicit empty names. Bind correspondence through persisted public identities,
  topology, directories and sessions: automatic workspace labels can change after
  Git discovery and are not identity proof. Keep nullable naming provenance and
  all explicit names unchanged, including empty, whitespace, `~` and numeric names.
  Use the same comparison for capture, stop and stopped-source reconciliation.

Manifest schema 2 marks the current-document ownership contract; schema 1 remains
readable for existing migration receipts. An older adapter must refuse schema 2
rather than overwrite a desktop-edited document through its old whole-plan CAS.
The private receipt retains the current plan, document/version, native labels and
terminal bindings before a destructive effect. Adoption preserves the previous
manifest/receipt in a private backup. Unfinished initial migration creation still
uses its original receipt and explicit replacement authority; a missing address
is not evidence that a native create failed.

Restore/verification and migration completion must use the reconciled plan, not
the journal's stale original plan. Foreign actual programs in owned slots, changed
directories, duplicate clients, malformed bindings and uncertain native outcomes
remain refusals. Unowned content is preserved, never killed merely to make a
layout match. The shared OpenCode backend and in-flight turns remain independent.

Transient inventory disappearance may restart the entire read-only scan within a
bounded settling window (at most five seconds); partial inventories never pass.
Ownership/permission failures, ambiguous identities and exceeded bounds do not
become retryable. Native start/run/kill/doc.set effects are never retried by this
settling policy.

Qualification must include edited layouts and app-style serialization, closing
owned shells and an agent, adopting three later exact clients, fresh baselines,
CAS races, interrupted mutation recovery, inventory churn and both boot phases.
Use synthetic IDs, not live session prefixes or operator paths. Pins, live recovery,
rollout, VM/Mac changes, 007H wrapper/config/activation work and 007I editor recovery
remain outside this slice. Fork A owns the subsequent reviewed live operation.

### Reboot-interrupted repair (RRW-007G-R4 / INT-082)

Core can return an already-created replacement as a live labelled plain shell
after restart. A stored `created` address is an effect identity, not proof its
desired OpenCode process survived. Classify its current program before requiring
active-client coverage. Given exact owned labels, expected cwd, a proven plain
shell and no duplicate desired client, admit a fresh repair generation under the
existing ownership and exit guards. Do not call a plain shell a ready client or
reuse old process identity against a new process. Preserve finished historical
records without treating them as current creations or deleting uncertain clients.

Use current document facts to distinguish an unbound retained replacement from
one already bound by a successful CAS. A finished original address and a retained
created address are not interchangeable. Do not overwrite a user-rebound leaf,
attach the desired session to a wrong directory, repeat an uncertain run or retire
a live replacement using an original-source proof. Revalidate process identity,
desired-session absence and document version at every mutation boundary. New
repair remains replacement-first: live readiness, leaf CAS, captured-shell stop.

Given a stopped repair whose stable leaf is gone, preserve that closure and
continue the remaining owned repairs once its original exit and absence of an
uncertain live owned client are reconciled. Finished history is not a live client.
Do not recreate the closed view or clear unexplained live/unbound terminals.

Every admitted interruption phase must be recoverable after core restart: idle or
controller stop, run admission/readiness, leaf CAS before/after acknowledgement,
old-shell cleanup and completed restore. Reconcile durable effect intent against
current live/finished inventories and current process facts before admitting new
effects. Never convert stale PID/start-time evidence into authority over a new
boot's process, infer process absence solely from a restarted server or silently
discard a pending mutation. Unsupported or ambiguous identity/version facts retain
state and refuse rather than guessing. Retained legacy schema-1/2 forms remain
readable; any private proof extensions require exact validation and conservative
older-adapter refusal. Completed switch history remains unchanged.

The reported retained-state regression has a complete journal, 54 repairs, two
legacy unbound created replacements now plain shells with their original labels,
finished original terminals, a stopped repair whose leaf is absent and no desired
sessions live. Recover through installed restore/recover, with no published-state
hand edits. Keep R3 closed pending-run behavior and all R1/R2 ownership safeguards.

Qualification interrupts after some native repairs, restarts core as boot would
with an app-like finish-event pane remover connected, then completes recovery.
Restart again after completed restore and verify convergence without duplicate
clients, resurrected closures or changed unrelated document/process facts. Cover
the finer interruption matrix with synthetic tests and negative ownership, cwd,
PID reuse, duplicate and version cases. Keep the deterministic pre-kill ordering
oracle, held-turn and both-boot qualification. A fixture client/observer is not
actual Desktop GUI execution; core-only restart is not a full VM boot claim.

Authority remains ready INT-082 under #524, manifest
`0ac1088028a1d3aca0cff09897bdce2ff3cb0829647a6bd885179af70715a8b3`;
base is R3 `7579ac3a4575f1296f8aeb2e84eda2174ceaac95`. No new public inputs,
bootstrap or binary pin changes, live recovery, timer changes or cleanup. Fork A
owns pins and live rollout. The independent lifecycle `gate-commit` staged-deletion
defect is outside R4. RRW-007I stays paused with all work retained.

### App-connected repair ordering (RRW-007G-R3 / INT-082)

A connected desktop removes a pane whose referenced terminal finishes. New repair
must not kill its referenced kept shell before a live replacement is ready and
the proven leaf has been rebound by document-version CAS. Prefer per-leaf create,
verify, rebind, then retire the old shell so one failed later repair cannot strand
every earlier replacement outside the document. The original shell remains live
until rebind. No duplicate exact-session client is permitted: an idle Bash is not
an already-live OpenCode client, regardless of its retained launch metadata.

Before creation, preserve ownership namespace, actual shell argv/cwd, PID/start-time,
desired-session absence and current leaf/address/version proofs. Persist every
effect intent before invoking native mutation. Before rebind, verify the exact
created client, original shell identity, duplicate absence and unchanged leaf and
version. After a proven CAS, retire only the captured old shell, never the live
replacement. Prove its process exit independently of RPC acknowledgement. Raw
document edits outside the owned leaf are not overwritten or synthesized.

Crash recovery must distinguish pre-create, created/unbound, CAS-uncertain and
post-rebind old-shell-stop stages. Accept a proven successful effect without
repeating it; uncertainty remains durable until qualified. New private intent or
repair fields require bounded exact validation; older adapters must conservatively
refuse unsupported active forms. Retained R1/R2 intents remain readable using their
original proofs, without inventing historical process identity. The R1 kill-first
transition below describes legacy compatibility only; R3 owns new repair ordering.

Given a retained pending `terminal.run`, inspect the actual current document and
all native terminals, live **and finished**, using exact ownership-namespace labels.
If its stable leaf is absent and no terminal carries those labels, resolve that
repair as closed, retain its private history, and continue remaining repairs. Do
not recreate the removed view or blindly repeat `terminal.run`. A finished match,
duplicate match, conflicting ownership or replacement reference is not absence and
must not be silently cleared. A present leaf with no terminal match remains an
uncertain create, not permission to retry. Preserve process, layout and version
guards around observations; never turn an observation into an atomicity claim.

New repairs may carry a private `source` identity snapshot and `create_id` of
exactly 32 lowercase hexadecimal characters, bound to a `remote-herdr-repair`
ownership label. Each new admitted creation gets a fresh generation; unrelated
finished historical generations are not evidence of that create. A matching
current-generation finished record still blocks absence claims. Legacy intents
without a generation retain their original label meaning. Per-leaf CAS intents
bind `leaf` and exact `replacement` process proof; post-CAS kill intents bind a
validated `rebound` document/version and replacement proof in addition to original
shell identity. These are private bounded extensions, not setup inputs.

Recovery must continue from the reported complete switch journal and current
receipt containing many repairs, already-created unbound replacements and a gone
pending-run leaf. Project the actual current document without resurrecting user
closures; rebind proven earlier creations before attempting new creates. Never
hand-edit journals, fabricate a clean manifest, discard uncertainty or restart the
shared backend. Ambiguous or changed original-process proofs still refuse.
With a complete switch journal, explicit `recover` for selected core invokes the
same native current-document reconciliation as `restore`; it does not replay the
completed switch or rewrite its history. Complete TUI journals remain a no-op.

Native disposable qualification runs a concurrent app-like client which removes
panes when their referenced terminals finish, using version-checked app document
writes. Assert the replacement is live and bound when old shells finish; exercise
retained legacy mixed state and interruptions around run, readiness, CAS and stop.
Keep held-turn, R1/R2 compatibility, duplicate, private-backup, restart/stop and
both-boot evidence. Fixed refusal labels expose no native values. This is an
app-like protocol client, not a claim of actual Desktop UI execution.

Authority: INT-082, #524 `d8e9e0f`, manifest
`0ac1088028a1d3aca0cff09897bdce2ff3cb0829647a6bd885179af70715a8b3`.
No new public CLI/configuration inputs, bootstrap or binary pin changes. Fork A
exclusively owns live recovery, timer decisions, pinning and rollout. 007I remains
paused, with all work retained, until this separately approved hotfix is delivered.

### Desktop ownership and identity compatibility (RRW-007G-R2 / INT-082)

App display labels and ownership labels have different owners. At every shared
`_same_labels` consumer, including duplicate-creation checks, compare exactly the
complete `remote-herdr-*` namespace. Ignore non-ownership labels such as `where`,
`herdr.seen`, `herdr.space` and `herdr.tab`, including changes during recovery.
Missing or changed owner/pane/session, extra ownership keys and malformed label
records still refuse. Preserve the existing omitted/empty optional session-label
compatibility for plain shells; never infer ownership from app display labels.

The app may use its tab ID as its row root ID, including a one-child row. Validate
IDs independently for spaces, tabs and all tree nodes; cross-kind reuse is legal.
Within each kind, missing or duplicate IDs still refuse, including duplicate nodes
across different tabs or spaces. All node IDs share one node namespace so a branch
and leaf cannot alias. Stable leaf bindings and duplicate terminal/session guards
remain exact. Projection may collapse a one-child row in its private canonical
plan, but it must not rewrite the raw app document, names, layout or opaque fields.

Given retained `restore_pending`, selected `herdr-core`, manifest and receipt with
mixed live and repair terminals, `remote-herdr recover` must complete after these
compatibility corrections without hand-editing journals or manufacturing a new
manifest. Already-live exact sessions stay live; required repairs retain R1's
ownership, original-process, exit, desired-session absence and document/version
checks. User-closed views remain closed; no duplicate client or backend restart.

Qualify synthetic positive/negative label and ID cases plus disposable native
terminals carrying app labels and app-created-tab document structure. Distinguish
actual app-producer evidence from a fixture-authored compatible document; unavailable
producer capability is not a native app UI pass. Retain both R1 interruption cases,
held-turn, raw-document leaf-only CAS and both-boot evidence. No new CLI/configuration
inputs, receipt/manifest schema, binary pins, bootstrap or live operations. Fork A
retains the live journal and exclusively owns live recovery and pinning. 007H must
build on this separately qualified hotfix; 007I remains separate.

### Kept-shell kill-intent recovery (RRW-007G-R1 / INT-082)

A terminal's presentation is not its process identity. Title, status/records,
turn counters, geometry and same-process foreground reporting may change after
publishing a kill intent without invalidating a proven owned idle shell. Do not
compare the whole terminal record at that boundary. Preserve exact native binding,
labels, launch identity, actual shell argv/cwd, PID/start-time and document/version
checks. A changed layout, terminal reference, process or ownership still refuses.

Given a current-document receipt with a pending kill:

- If its bound terminal is finished, prove the original captured processes absent,
  validate ownership and the unchanged document/version, then mark the stop observed
  without issuing another kill. Do not infer exit from an RPC acknowledgement.
- If the same original owned idle shell remains live, reconcile that observation
  against the private intent and desired-session absence. Recheck all ownership,
  process and version guards before completing the admitted kill, wait for terminal
  completion and old PID/start-time exit, then proceed through the existing single
  create/readiness and leaf-only CAS recovery. This is not blind mutation replay.
- If any proof is unavailable, changed or contradictory, retain the intent and
  refuse. Never stop a replacement process, resurrect a user-closed view, create a
  duplicate session or weaken the selected-runtime/shared-backend boundary.

New kill intents may add a private `identity` snapshot binding actual argv/cwd,
native launch fields and terminal/foreground PID roles to the existing PID/start-time
proofs. Validate its bounded shape before use. Existing receipts without that field
remain readable under their original exact ownership, original PID/start-time,
allowed idle-core-Bash argv, directory, binding and document/version proofs; never
invent a historical argv snapshot. Unknown extra intent fields remain refusals.
No new CLI/configuration input or manifest schema is introduced. Older adapters
must refuse unsupported extended intents, not reinterpret or discard them.

Refusal labels identify a fixed field category (binding, labels, PID/role, start-time,
argv, directory, state, exit, session, document version or layout), never observed values. Hosted
diagnostics preserve that label across the bounded boot observation deadline.
Synthetic and disposable native tests must cover display churn after publication,
interruption before kill, lost successful kill replies, already-finished terminals,
and negative identity/layout changes. Keep all existing exit, duplicate, CAS,
retained-journal, held-turn and both-boot qualification.

Fork A owns pinning and any live recovery. This separate critical-risk hotfix does
not include 007H preference/activation/wrapper work or 007I editor recovery. Bootstrap,
binary pins, installer owners, databases and saved layouts remain unchanged.

### Plain-shell label compatibility (RRW-007F-R1)

Core 0.1.18 removes labels with empty values. Agent terminals require exact
`remote-herdr-owner`, `remote-herdr-pane` and nonempty `remote-herdr-session`.
Shell terminals require the owner and pane labels but omit the session label.
Only an absent session label and the legacy empty session label are equivalent;
missing owner/pane labels, nonempty mismatches and extra labels still refuse.
Label compatibility never substitutes for actual program, directory, PID/start-time
or duplicate-client proofs. No binary pin, installer, backend or CLI ownership changes.

TUI 0.9.5 (`src/pane.rs` / `src/config/model.rs` at
`2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`) defaults to `/bin/sh` when `SHELL`
is absent, as in the sanitized `exec-tui` environment. TUI capture and pre-stop
proof also accept exactly `['/bin/sh']` with no arguments, in addition to the
existing Bash forms. `sh -c`, shell flags, aliases and other executable paths
still refuse. This TUI-only compatibility does not change core's shell policy.

- Given a retained `restore_pending` switch, no manifest, and a receipt naming one
  live owned shell with no session label and `pending=None`, explicit
  `remote-herdr recover` reuses that terminal, creates only the remaining panes,
  performs the version-checked document update and verifies before completing.
- Given a legacy uncertain shell `terminal.run` intent containing an empty session
  label, recovery matches the pinned core's omitted label without repeating creation.
  Missing or multiple matches remain an uncertain outcome, not permission to retry.
- Given a changed owner, pane, nonempty session, directory or actual program,
  compatibility does not authorize attachment, replacement or destructive cleanup.

The original transaction ID, receipt, native terminal record and private backup
are retained. Recovery may publish its manifest through the existing controller;
operators must not manufacture one or hand-edit a receipt. Automatic restore still
refuses an unfinished switch. This hotfix does not implement INT-082 daily-layout
adoption, unnamed TUI label normalization, broader CLI diagnostics or editor repair.

Hosted native proof passed implementation head
`dea822039d71902ca7dc6dc5cc337a7d31514b31`: legacy label emission/comparison
generated the retained failure through real controller writes, then the unmodified
installed CLI recovered the existing shell without receipt edits. The same job
passed held-turn preservation, bidirectional switching, core restart/explicit-stop
recovery and both runtime boot phases. This is disposable qualification, not live
owner recovery, final-head CI closure or delivery of the broader adoption slice.

`remote-herdr selected` observes selection; `remote-herdr-core check` verifies the
installed bytes without repair. The restore timer only invokes the serialized
controller; upstream `hc-serve-*`, `hc-hold-*` and `hc-shutdown-*` units own core
lifetime. A failed restore does not activate the unselected runtime and retains
private boot/transaction intent. Diagnose through selected-unit status and
source-literal failure labels without publishing native journals, registrations,
titles, directories or session payloads. Use explicit `recover` to reconcile an
interruption; do not erase receipts, blindly restart either runtime or restart
the shared OpenCode service. Unknown outcomes require owner inspection.

Fork A coordinates future core/TUI/OpenCode compatibility changes. A pin or native
schema change requires renewed checksum, adapter and disposable native lifecycle
qualification before rollout. Keep backups, receipts and completed history during
support and migration; retirement needs an explicit inventory/retention decision.
Disabling the selected runtime is not permission to uninstall binaries, remove
native terminal records or discard OpenCode sessions. No automatic cleanup is added.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary | required: transition table; who owns binary and runtime activation? |
| Interaction | required: transition table; what must stop before target agents start? |
| State | required: transition table; where does uncertainty block activation? |
| Data/trust | required: transition table; where is sensitive migration data retained? |
| Schema | required: transition table and selected-interface contract; native IDs may change but session identities cannot |
| Dependency/deployment | required: transition table; what is the installation prerequisite? |
| Quantitative | not_applicable: no performance or capacity claim |

| Transition | Owner | Guard / result |
|---|---|---|
| Reviewed binary pin to installed core | Foundation; Fork A coordinates version | One installer verifies archive and binary; no desktop update owner |
| Local selection to user-manager startup | Fork B | Only selected runtime may resume agents |
| Active source to captured inventory | Switch controller | Private fidelity-checked layout/session data |
| Captured source to stopped source | Switch controller | Prove source runtime and agents stopped |
| Stopped source to live target | Native target adapter | Verify exact identities, directories, labels/order |
| Retained shell receipt to recovered switch | Recovery controller | Match exact owner/pane with omitted or legacy-empty shell session label; reuse existing terminal |
| Desktop edits to current baseline | Recovery controller | Prove exact current bindings; retire closed views; preserve raw document and metadata |
| Proven owned shell to resumed agent | Recovery controller | Old client absent; owned shell proof; one create; latest-version leaf-only CAS |
| Pending shell kill, original shell still live | Recovery controller | Reprove original identity and unchanged version; complete kill; prove exit |
| Pending shell kill, terminal already finished | Recovery controller | Same binding/labels/version and original process exit; observe without another kill |
| Presentation churn at kill boundary | Recovery controller | Ignore display fields only; retain identity/layout guards and value-free field refusal labels |
| App display labels alongside ownership labels | Shared ownership matcher | Ignore non-ownership labels; compare complete remote-herdr namespace exactly |
| App tab ID reused by its row root | Current-document projector | Separate kind namespaces; retain global tree-node uniqueness and raw document |
| New kept-shell repair while app is connected | Recovery controller | Create/verify replacement, CAS leaf, then stop only the captured old shell |
| Pending run with gone leaf and zero live or finished label matches | Recovery controller | Preserve closure, resolve repair, continue others without replay |
| Crash after leaf CAS but before old-shell exit | Recovery controller | Prove replacement binding and original identity; reconcile old-shell stop only |
| Created replacement returns as an owned plain shell after restart | Recovery controller | Reclassify current program; admit fresh proven shell repair, never call it a ready client |
| Stopped repair leaf absent after restart | Recovery controller | Reconcile original exit and uncertain live clients, retain closure, continue other repairs |
| Restart during run/CAS/cleanup or after completion | Recovery controller | Reconcile durable intent against current process/document facts without replay or stale process authority |
| Any uncertain or failed transition | Recovery controller | Retain evidence; no duplicate activation |

**Text Equivalent:** The foundation installs the reviewed core binary, with
version coordination retained by Fork A. Fork B starts
only the explicitly selected runtime. Switching first captures private state,
then proves the source stopped before any target agent starts. Target readiness
requires live session and layout fidelity. Shell recovery accepts the core's
omitted empty session label without relaxing owner or process checks. Uncertainty retains evidence and
blocks activation. Canonical source: approved INT-077/079 and this behavior
contract; hosted qualification is distinct from live acceptance. Owner: distribution maintainer.
Update with selection, native interface, ownership or recovery changes.
