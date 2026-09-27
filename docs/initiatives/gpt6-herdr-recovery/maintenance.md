# Post-macOS Upgrade Runtime Maintenance

## Readiness Reopened And Approved Scope

The original source slices reached protected main through PRs 182 and 183. Live
inventory then exposed two gaps: implicit OpenCode sessions are absent from
argv-only capture, and a large restoration burst exceeds five-minute admission.
Do not call the previous thirty-session qualification proof for this workload.

The operator has approved all eligible Homebrew software updates, host and
registered-workspace managed runtime updates, and a controlled Herdr restart
after complete private inventory, backups and workload qualification. The prior
blanket restart hold is superseded by these prerequisites. Current behavior and
source assertions in this document override conflicting earlier timeout and
argv-only assumptions, without rewriting historical test or delivery evidence.

Existing context homes remain: shell-auth startup owns session identity/pacing
and native Herdr release compatibility; distribution consumes the pinned assets
and owns fleet operations; OpenCode model policy was already delivered. The
source slice is elevated risk, using Python, Security and Cloud modules under the
existing profiles. No new provider, delegation, lifecycle writer-recovery or
credential-copying authority is granted.

## Native Session Identity Contract

Given an OpenCode foreground process, capture and restored-session recognition
accept either its valid explicit session argument or the same pane's native
`agent_session` with `agent=opencode`, `kind=id`, `source=herdr:opencode` and a
valid `ses_` identifier. Native identity must come from Herdr's structured pane
inventory/get response with `agent=opencode`, never a terminal title or transcript.
When both authorities are present they must agree. Malformed, conflicting or
unavailable identity leaves existing recovery intent unchanged and prevents
unsafe launch; native identity never proves a stopped process is currently alive.

Both capture and restoration observation use the same resolution rule, preserving
schema 1 reads, schema 2 pending/observed writes, atomic replacement, directory
matching and occupied-pane refusal. A complete inventory includes implicit sessions
and never discards a pending entry merely because argv omitted `--session`.
Native metadata cannot turn an unrelated foreground process into OpenCode.

## Workload And Pacing Contract

An eighty-session burst must finish without false unavailable-storage failures,
with at least five-second spacing. Keep the native shlock identity and the
twenty-second no-progress deadline. Extend total admission to 600 monotonic
seconds; progress never extends that hard bound. The roughly eight-minute
worst-case paced burst fits without changing spacing or weakening stalled-lock
detection. Retain argument forwarding, cancellation, stale-owner and unsafe-path
checks. Tests may use deterministic time for the large workload, plus real-process
lock/spacing coverage; do not claim a fake-clock test is a live restore.

## Herdr Release Qualification

Select stable Herdr 0.9.1, wire protocol 22, from the upstream tagged source and
published release digests. Keep macOS ARM64 and Linux x86_64 defaults/examples
consistent, and replace the stale Fedora ARM64 provisioning pin with the same
release's verified asset. Pin byte digests, not just filenames/version strings.
Disposable native version/API/server probes precede installation. An older
sender's sixty-four-pane handoff limit still applies: do not remove or bypass
the existing live-handoff guard. Use the separately approved controlled restart
for a larger live server after backups and identity coverage pass.

## Ownership And Validation

Source ownership: recovery helper, OpenCode wrapper if needed, Herdr defaults and
example asset metadata, Fedora Herdr provisioning pin, their focused tests, and
context completion notes. No normative scope edits by Build; a material finding
returns to Discovery. No live deployment is part of source qualification.

Required checks cover implicit native capture, explicit/native agreement and
conflict, missing/malformed metadata, unrelated processes, native restoration
observation, pending retention, large-workload admission and total-deadline
refusal, existing platform rendering, asset pins, and retained old-server guards.
Use existing pytest/chezmoi/shell authorities and unchanged public runtime
catalogs. Required CI must pass before normal PR merge. Do not create more
provider requests or weaken a pre-existing benchmark when CI is noisy.

## Authorized Maintenance Operations

Homebrew dependency-only updates can proceed independently of source development.
Refresh metadata, preview upgrades, keep old kegs with cleanup disabled, update
eligible formulae/casks and rebuild pkgconf for the new macOS. Recheck versions
and doctor output. Do not zap private state, grant blanket tap trust, remove
deprecated software or migrate databases under this approval. Running GUI/network
applications require orderly coordination; failed privilege prompts remain visible.

Use the managed OpenCode/Codex staged fleet updaters, including registered guests,
only once the authorized VM-control route is available. The harness denied direct
VM inspection during Discovery: permission remains a blocker, not a reason to
hide the operation in another helper. Do not copy host sessions or credentials to
guests. Preserve guest-local authentication and prior running-state expectations.
Runtime or continuation qualification failures retain prior working generations.

Before host restart, retain owner-private configuration/binary preimages and
complete Herdr/native conversation inventories. Verify every live OpenCode ID
exists in its source-local history store and is represented in durable recovery
intent, including this conversation. Prevent an old watcher from overwriting
new schema-2 state. Deploy the qualified helper/wrapper pair and approved model
routes from merged source, never broad-apply the unrelated Discovery checkout.

The restart controller must survive the pane it is restarting and preserve the
existing host supervisor/TCC responsibility. It must record stages, rollback
authority and exact resumption instructions privately before stopping services.
Post-start verification compares expected and observed conversation identities,
pane count, versions and external-state health; it never claims success merely
because the server is running. If this conversation disconnects, it resumes its
same native identity and verifies persisted operation evidence before continuing.
No live restart may run before coverage, backup and workload gates pass.

## Visual Evidence

State and interaction: required transition table. Question: when is disruption
authorized? Source/owner: contracts above, dotfiles maintainer; update when a
prerequisite, identity rule or deployment stage changes.

| Stage | Admission | Next action |
|---|---|---|
| Source correction | Approved exact slice and isolated writer | Test and merge corrected source |
| Maintenance preparation | Supported package/VM permissions and reviewed targets | Preserve preimages and stage validated candidates |
| Restart ready | Complete private identity coverage, backups, candidate qualification and workload proof | Controller may stop old server and start qualified replacement |
| Restoring | Native identities retained; no occupied-pane overwrite | Observe every expected conversation |
| Verification incomplete | Missing identity, failed health or unavailable permission | Keep explicit incomplete status and recovery evidence |
| Verified | Exact inventory and health/version checks pass | Report installed and restored outcomes |

**Text Equivalent:** Source correctness alone cannot admit a restart. Package
permission, complete identity coverage, backups and workload proof must precede
disruption. Restoration is complete only after exact identities and health match;
any missing prerequisite retains an incomplete result and recoverable evidence.

Boundary/data-trust: not_applicable; existing host/guest private-state boundaries
remain unchanged and are explicit above. Schema: not_applicable; recovery schema
2 is unchanged. Dependency/deployment: not_applicable; existing supervisor and
fleet topology remain authoritative. Quantitative: not_applicable; acceptance
limits are contractual bounds, not claimed benchmark results.
