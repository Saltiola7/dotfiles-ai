# OpenShell host Git and lifecycle boundary

Status: normative target; authenticated transport and runtime qualification remain
outstanding. Owner: lifecycle maintainers. Profile: [PROFILE.md](../PROFILE.md).
Initiative: [OpenShell pilot](../../../initiatives/openshell-pilot/README.md).
Risk: critical because untrusted workloads request host mutations. Modules:
Python, Security and Cloud. Existing records, gates and approvals remain authority.

## Outcome and compatibility

Preserve the complete supported managed Git workflow for sandboxed Codex and
OpenCode while protecting other checkouts and host execution. Full workflow means
capability parity under existing authority, not arbitrary Git arguments or new
permission to rewrite history. The operator explicitly confirmed that existing
Git approval and preservation rules remain unchanged.

Reuse native Worktrunk, native Git, dbsctrctl evidence/gate/delivery operations and
existing signing. No second lifecycle, worktree allocator, commit ledger or general
host command service. Partial operation support cannot complete the joint pilot.

## Capability matrix

| Capability | Existing owner | Required boundary |
|---|---|---|
| Status, diff, log, show, branches, worktree inventory | Native Git / Worktrunk | Bounded reads without external helpers or other-cycle evidence |
| Selected staging, unstaging and ordinary signed commit/amend | Native Git and existing caller permissions | Exact enrolled paths, current ask/deny rules and signer |
| Phase commits | dbsctrctl gate-commit | Existing evidence/path/gate checks and recording, invoked once |
| Checks and evidence | dbsctrctl record-evidence | Host constructs fixed sandbox-execution adapter; no caller-selected host executable |
| Fetch, selected branch push and draft PR updates | Existing Git/delivery owners and final-push | Exact approved destination, account and gates |
| Creation/navigation | Worktrunk and storage hooks | Host orchestration; distinct enrollment for changed target |
| Restore/reset/stash, merge/rebase/cherry-pick and conflict recovery | Current caller permissions and recovery/delivery contracts | Each operation keeps existing authority; denied operations remain denied |
| Removal, branch deletion and retirement | Worktrunk and preservation/lifecycle owners | Revoke enrollment first; sandbox exit is not preservation proof |
| Administrative exceptions | Existing operator approval | Transport availability cannot grant permission |

Managed OpenCode distinguishes allowed gate-commit/final-push from ask-controlled
direct Git mutations and denied force/no-hooks/custom-path routes. Codex's parent
sandbox/approval limits remain ceilings. The adapter must honor each effective
caller policy and cannot manufacture consent or native agent identity.

DVC materialization, private-history extraction, arbitrary remote APIs and native
Mac tests remain separate capabilities. Unavailable operations are explicit, not
silently executed on host to maintain apparent parity.

## Closed enrollment and request contracts

An enrollment binds trusted canonical repository/common Git identity, linked
administrative directory, branch, cycle when applicable, workload generation,
operation set, policy generation and expiry/revocation. It is short-lived runtime
authority, not a replacement task registry. The host resolves it from native
sources; caller paths, environment and mutable Git pointers are never authority.

Requests contain a version, opaque enrollment handle, unique request ID, expected
state token, operation and that operation's bounded typed fields. Reject unknown
fields, duplicate keys, shell strings, executable/argv selectors, cwd/environment
overrides, arbitrary Git options, credentials and alternate repository selectors.

The local channel must bind a revocable capability to one host-controlled
enrollment and confer no gateway, SSH-agent, provider or cross-worktree authority.
The selected pilot transport and versioned operation contract below define the
design; actual lifecycle ownership, per-mode mappings and native approval binding
still require qualification before this dependent slice is promoted.


## Selected pilot transport

Use the existing host-initiated OpenShell non-PTY exec transport to a fixed
sandbox relay, with login-shell startup disabled. A trusted host controller opens
each stream; no workload initiates a connection to a new Mac command listener.
The relay coordinates sandbox-local client requests, but its contents and messages
are untrusted. The controller supplies fixed argv; no request text becomes a host
or relay shell command. Upstream escaping still involves a sandbox shell, so
no-login-shell is not a claim of shell-free execution.

Research basis: NVIDIA/OpenShell v0.1.6 CLI sandbox_exec_streaming_integration
tests, SDK execInteractive implementation, ExecSandboxRequest and supervisor
SSH cleanup. Native streams provide stdin, separate stdout/stderr, exit and
terminal transport status. The CLI's cumulative stdin limit is four MiB.
Select one request per stream, at most one in-flight mutation per enrollment,
and the bounded frame sizes below; drain stderr concurrently. Exit zero without
complete terminal transport status is not successful completion.

The public exec selector is workspace plus sandbox name, not an atomic expected
sandbox-generation precondition. The pilot therefore requires exclusive trusted
controller ownership of the gateway workspace, unique never-reused sandbox names,
serialized lifecycle changes and a host-owned enrollment/transport binding.
A fresh nonce establishes protocol freshness only. It is not proof of native
workload generation or agent identity.

Observe sandbox identity before and after stream establishment and immediately
before effect, without treating separate observations as atomic. Workload processes
have no lifecycle/admin credentials. Any stop, replacement, restart, controller
ownership uncertainty or transport loss closes mutation admission. No transparent
reconnect, name reuse or automatic replacement. Resume requires fresh enrollment
and revalidation of existing authoritative Git/lifecycle state. If exclusive
lifecycle ownership cannot be established on the actual runtime, host mutations
remain unavailable; do not conceal the upstream API limitation.

For a mutating request, receive and validate the complete frame before pausing the
workload. Execute only after whole-workload quiescence and trusted state checks.
Resume the same known generation before delivering the result to its paused relay.
If either resumption or acknowledgement fails, retain the known host result and
report transport uncertainty; never execute the mutation again to get a reply.

## Versioned operation contract

Protocol version 1 is a closed semantic interface, not arbitrary native CLI
forwarding. The future client shim maps supported native invocations to these
operations; unrecognized flags or forms return unsupported and cannot fall back
to host execution. Inspecting an unsupported spelling must not change work.

| Envelope field | Type and invariant |
|---|---|
| schema_version | Integer exactly 1 |
| request_id | UUID; unique within enrollment; identical replay has identical bytes |
| enrollment | Opaque host-issued handle bound to the opened stream |
| state_token | Opaque host-issued expected-state token; never a caller-selected path or branch |
| operation | One of the closed operation families below |
| input | Exact per-operation object; unknown and duplicate fields rejected |

Use a length-prefixed UTF-8 JSON frame. Request payload limit is 64 KiB, result
limit one MiB; aggregate host stdin per CLI stream remains below two MiB. No
streamed partial request can cause an effect. Maximum JSON nesting is eight levels and 32 fields per object;
at most 256 repository-relative paths, each at most 4096 UTF-8 bytes, and a commit
message at most 16 KiB. Paths reject NUL, traversal, absolute roots, Git pathspec
magic and alias ambiguity. Host argument construction always separates operands
from flags. Symlink leaves remain data; path components never follow workload
instructions into another root.

Results contain schema_version, request_id, status, reason_code, refreshed
state_token when safe, and a bounded operation-specific result. Status is one of
completed, refused, approval_required, unavailable or uncertain. Source diffs and
file names may return privately to the enrolled agent when needed for its task;
they do not enter public evidence. Oversized read output is explicitly truncated
with a bounded continuation token; truncation and remaining-data status are
mandatory result fields for that case. Mutation outcomes are never truncated in a way
that hides whether an effect occurred.

| Family | Typed inputs and target | Authority and acceptance |
|---|---|---|
| inspect | Fixed query enum, bounded result selection and allowed repository object/ref operands | Read only; no external diff/pager, config reads or lifecycle secret disclosure |
| stage / unstage | Exact path list; unstage against current enrolled HEAD | Existing direct-Git approval class; preserve unrelated staging |
| commit / amend | Message, expected index/tree and selected commit mode | Native current approval plus signer; amend retains existing history-rewrite restrictions |
| gate_commit | Existing gate identifier, message, exact paths and existing evidence references | Existing lifecycle validates and commits; no client cycle override |
| record_check | Host-qualified check identifier and bounded selection | Host constructs sandbox adapter; no host program/argv from workload |
| fetch | Trusted remote selector and allowed ref selection | Existing permission; fixed native transport/account, no arbitrary URL/helper |
| push / draft_delivery | Existing selected target and bounded draft text | Direct push keeps existing approval; lifecycle delivery reuses final-push gates |
| restore / reset / stash | Fixed mode, explicit selected paths or host-recorded task-owned stash identity | Current exact destructive/history consent; preserve foreign stash entries, change only exact task-owned entries, and prohibit global stack operations |
| reconcile | Fixed merge/rebase/cherry-pick/abort/continue mode and approved object selection | Current policy and conflict-recovery authority; denied routes remain denied |
| worktree / branch | Fixed create/select/remove action through existing host owner | Existing storage/preservation rules; no mutation of a live enrollment's target |
| lifecycle_inspect | Explicit bounded existing state/readiness query | No arbitrary command or private evidence-body export |

This table defines families and invariants, not blanket permission for every
mode. Before host implementation promotion, expand each enabled mode into its
exact input fields, native owner mapping, existing approval class, state guard,
result and recovery tests. Modes denied by current policy remain denied.
Unknown mode is unavailable, never an unrestricted CLI escape.

Every revision/ref operand is a host-approved handle resolved to an exact object
or allowed destination. Reject raw caller refspecs, revspec expressions and mutable
stash ordinals. A stash handle binds exact object ID, observed shared reflog state
and originating task ownership. Apply and drop are separate operations; a conflict
never authorizes drop, and global stash clear is unavailable. Disable rebase
updateRefs, autostash, executable todo entries and interactive editors unless a
separate typed mode is qualified under existing authority. No raw garbage
collection, reflog expiration, prune, config mutation or repair interface exists.

Read operations have a 30-second execution bound, local mutations 120 seconds,
remote mutations 300 seconds and governed final delivery 900 seconds. Approval
requests return approval_required promptly rather than hold an open stream while
waiting. Host-only approval handles expire after ten minutes and any state change.
The controller applies bounded cancellation and drains stdout/stderr concurrently;
cancellation after a possible effect is uncertain, not proof of rollback.
One request is outstanding per enrollment and one metadata mutation per shared
repository at a time. Read outputs and stderr are separately bounded; stderr
retention is capped at 256 KiB with explicit truncation status. These are operation
ceilings, not performance claims or permission to extend native owner deadlines.

Shared repository objects and refs remain native owner state. Stash operations
may address only the exact task-owned object recorded by the host; ordinary
stack-index lookup cannot select another task's stash. Branch operations cannot
move protected/default or independently checked-out branches. Qualified fetch may
advance approved remote-tracking refs but cannot rewrite unrelated local branches.
Treat these explicit shared effects separately from unintended sibling mutations.

## Existing approvals through the host interface

Derive effective authority from the current qualified client policy and existing
lifecycle owner, never the requested operation name alone. An automatic native
permission authorizes only its unchanged checks; an ask-controlled operation
returns approval_required until a trusted host-side decision is available.
A denied native route stays denied.

A host-side approval handle is one-use and bound to enrollment, operation, exact
normalized inputs, expected state and expiration. Workload-supplied approved
flags, chat excerpts, tokens or claimed user identity have no authority. If the
native approval surface cannot provide trustworthy binding, present the exact
operation through an operator-controlled host confirmation path; never downgrade
ask to allow. Approval questions must show actual target/effect before the user
decides. A changed state or input invalidates the handle.

Existing lifecycle-specific approval remains separate. Initiative begin, gate
exceptions, adoption, integration and retirement retain their established
authorities and cannot be simulated by the bridge. Host enrollment starts only
after its required existing cycle/checkout prerequisites are met. General pilot
approval does not approve a particular destructive operation.

## Host execution and filesystem contract

- Keep common Git writes, reservations and lifecycle evidence host-owned. Prefer
  bounded host reads over exposing the entire common directory. Shared object
  history is not confidentiality isolation between branches.
- Protect the checkout Git pointer against overwrite, unlink, rename and parent
  replacement. Revalidate trusted identity before each mutation and before return
  to ordinary native use.
- Refuse unsafe aliases, external hardlinks, case/Unicode collisions and ambiguous
  roots. Treat tracked symlink leaves as Git data; never follow untrusted path
  components. Qualify submodules, nested repositories and Git alternates explicitly.
- Quiesce all workload descendants before operations needing stable source/index/
  metadata, then revalidate expected HEAD, index and tree. Existing launcher locks
  are cooperative; arbitrary trusted host writers are not excluded. Require host
  quiescence and drift refusal rather than claiming absolute atomicity.
- Qualify the complete effective host Git configuration/include closure. Refuse
  workload-writable includes, executable paths or configuration. Default-deny
  hooks, filters/process filters, external diff/textconv, merge drivers, fsmonitor,
  pagers, editors, remote helpers and implicit lazy fetch.
- A pinned hook that invokes an agent-edited script still executes untrusted code.
  Project validation runs in the sandbox; hook qualification must include its
  transitive execution. Existing mandatory protections cannot simply be skipped.
- Bind signing to the operator-selected native profile, host-owned program,
  allowed key and purpose. Private keys/socket access never enter workload.
  Missing or locked signer preserves work; never retry unsigned.
- Host delivery retains exact remote/refspec/account authority. Reject remote
  rewrites, arbitrary protocols/helpers and provider-credential reuse for Git.

## Evidence and Gate Commit reuse

record-evidence executes a supplied program today. The bridge constructs that
program from a fixed qualified sandbox adapter and reviewed check selection.
Project tests, dependency scripts and repair commands execute only inside the
approved workload. Caller-provided host commands or environments never reach it.

The host observes actual workload generation, check identity, source identity,
image/policy identity, exit/timeout and provenance, then uses existing evidence
handling. Workload text claiming success is insufficient. Preserve existing
failure, source-digest, gate-order, privacy and timeout rules. Do not invent a
parallel evidence receipt that independently authorizes lifecycle progression.

gate-commit remains phase owner: evidence-bound paths, unrelated-stage rejection,
native signed commit, post-commit byte checks and lifecycle update happen there.
Never commit and manually edit the Cycle Record afterward. final-push keeps its
existing target, account, protected-base and gate checks.

## Mutation order and recovery

| Step | Contract |
|---|---|
| Admit | Validate the authenticated stream and host enrollment under exclusive lifecycle ownership; resolve current authority and exact operation |
| Reserve | Serialize relevant host metadata operation; reject conflicting enrollment |
| Quiesce | Pause all relevant workload writers while preserving native session |
| Revalidate | Check canonical identity, pointer, configuration and expected source/index/HEAD |
| Execute | Invoke only the existing owner with fixed argument construction |
| Verify | Observe actual result and post-state, signing and lifecycle outcomes |
| Record | Retain bounded private request/outcome evidence bound to generation |
| Resume | Resume only the same valid generation after known completion or safe refusal |

Record accepted operation identity before effect. Identical retries return known
recorded outcomes; changed inputs refuse. Timeout, lost reply or crash may mean
the mutation completed. Inspect authoritative Git/lifecycle state before any retry.
Uncertainty never triggers automatic reset, source rollback, alternate runtime,
new session or duplicate publication. Retain failed and uncertain evidence.

## Given/When/Then acceptance

- Given an enrolled cycle, when either agent requests a Gate Commit, then existing
  lifecycle creates exactly one correctly signed, evidence-bound commit while
  unrelated refs/checkouts remain unchanged.
- Given changed generation, target, expected HEAD or inputs, when a request is
  admitted, then reject before mutation.
- Given malicious pointer/configuration/attributes/hooks or path races, when Git
  operates, then no execution or write escapes the approved host boundary.
- Given project validation, when evidence is recorded, then execution occurs in
  OpenShell and existing lifecycle consumes observed source-bound results.
- Given concurrent host changes, failed signing or lost replies, when recovery
  runs, then retain work and report drift/uncertainty without duplicate effects.
- Given removal or target transition, when native owner proceeds under existing
  authority, then revoke old enrollment and never reuse its capability.
- Given an operation denied by existing policy, when called through the bridge,
  then it remains denied; bridge access is not approval.

## Readiness and gates

Qualify runtime quiescence, the selected transport's exclusive lifecycle ownership,
exact per-mode mappings, trusted approval binding, required hook/signer closure
and crash recovery before marking this slice ready. Test every row in the capability matrix with both
clients. Unsupported mandatory workflow is a blocker, not accepted partial parity.

All kernel, Review/Integrate and Maintain/Retire gates are required. Release is
not applicable to this internal adapter. Source-only Deploy/Operate exceptions
require a separate explicit activation owner; joint pilot activation requires
both. No Gate Exception is approved. Adversarial fixtures and actual selected-host
signing/transport tests are required; destructive cases use disposable repositories.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary | required: capability table; who owns each operation? |
| Interaction | required: mutation-order table; what precedes a host write? |
| State | required: state table below; what permits retry? |
| Data/trust | required: request/execution contracts; what crosses the boundary? |
| Schema | required: versioned envelope, operation and relationship tables; what binds authority? |
| Dependency/deployment | required: runtime, transport and signer prerequisites in readiness |
| Quantitative | not_applicable: no performance or safety-rate claim |

| Entity/state | Relationship or outcome |
|---|---|
| Enrollment | One repository, worktree and workload generation; no lifecycle ownership |
| Request | One enrollment, operation, expected state and request ID |
| Admitted | May execute once after all guards |
| Known result | Identical retry returns recorded result |
| Uncertain | Requires authoritative inspection; no blind retry |
| Revoked or stale | Cannot admit mutations |
| Qualification | Binds implementation, channel, configuration and runtime identities |

**Text Equivalent:** Generation-scoped requests cannot choose host execution or
target. Existing owners act only after admission, quiescence and revalidation.
Known outcomes are idempotent; uncertain ones retain work and require inspection.
Canonical source: this contract and existing lifecycle specifications. Owner:
lifecycle maintainers. Change trigger: operations, authority, channel or state.
