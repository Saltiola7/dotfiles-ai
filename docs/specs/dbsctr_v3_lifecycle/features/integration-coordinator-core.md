# Integration coordinator core: offline source contract

This implements the independent source slice of the
[integration contract](integration-coordinator.md). Critical risk; existing
Engineering Profile, Python/Security/Cloud and the explicit cycle plan apply.
This package supplies records, pure transitions, append construction and typed
ports. It supplies no authenticated live adapter, lifecycle hook or enabled policy.

## Domain and trust

A SourceSeries retains original ordered phase commits and separately identified
base/CI wrappers. A Ticket binds one opaque handle, native PR, requester authority
reference and immutable SourceSeries. A Target owns its queue, sequence and
monotonically increasing candidate generation. A Candidate binds source, base,
tested object/parents, tree, current plan and policy. A Reservation binds one
operation and invocation before a native mutation. A Qualification binds external
native evidence to the exact candidate. A Delivery binds actual native outcome
and ordered original-to-landed correspondence.

Records and transition results are immutable. Their hashes identify content;
they do not authenticate requesters, tests, native policy or source custody.
Injected typed ports are future trusted adapter boundaries. Parsing caller JSON,
a test double or a green field never establishes native or lifecycle authority.
The CLI cannot load adapters or enable live operations from input/configuration.

## Behavior

| Given / when | Then |
|---|---|
| Twelve durably requested tickets are admitted | Assign unique FIFO sequences; one claim owns the target; others remain queued |
| A duplicate request has identical immutable identity | Return existing state without duplicate queue position or sequence |
| The same handle has different source/requester identity | Refuse without changing prior state |
| Two transitions share the same observed control tip | Construct the same expected-head guard; only the store's successful CAS can acknowledge persistence |
| A candidate/head/base/plan/policy changes | Prior qualification cannot reserve a merge for its replacement generation |
| A mutation is reserved or its result uncertain | Keep ownership; no timeout, failure transition or late actor may free that reservation |
| A failed candidate has no outstanding reservation | Retain failure reference, release slot and allow unrelated queued work |
| Quiescent native no-effect outcome is verified externally | Clear only the matching reservation; no guessed retry or proof from elapsed time |
| Delivery has incomplete/reordered phase correspondence | Refuse delivery; retain source evidence and reservation |
| Qualified remote delivery is recorded | Release integration slot; local custody/completion/cleanup remains unclaimed |
| Unknown fields, duplicates, nonfinite numbers, oversized data or invalid identities arrive | Reject with a bounded fixed diagnostic and no native side effect |
| No adapter is enrolled | Every mutation command returns unavailable before reading input, credentials or state |

## Interfaces and records

Package: `private_dot_config/dotfiles-ai/integration_coordinator/`.
Thin source entrypoint: `dot_local/bin/executable_dbsctr-integration`.
Supported runtime: Python >=3.12; standard library only, no new dependencies.

Closed schema version 1 is a source interface, not an installed lifecycle receipt.
`SourceSeries`, `Candidate`, `Evidence`, `Qualification`, `Reservation`, `Delivery`,
`Ticket` and `Target` are frozen dataclasses with validated constructors.
`Snapshot` joins one Target and the complete retained ticket population and checks
cross-record identity, queue/active/state/generation/count consistency. No source
or ticket is deleted by a transition. Requests and code repairs retain original
task ownership; this core does not implement a repair loop or change a series.
A later source version/adoption contract must qualify code-changing resubmission.

Pure operations: request, admit, claim, wait for operator, invalidate candidate,
record failure, reserve merge, mark uncertain, resolve no-effect and record delivery.
Each returns a new Snapshot. Admission/qualification/no-effect/delivery arguments
are bound references supplied by qualified ports later; they are not native proof
merely because constructed or decoded. The current default path never invokes them
against GitHub. No clocks, age-based lease, retry worker or network client is added.

`build_append(before, after, expected_head, control_branch, operation_id)` returns
GraphQL `createCommitOnBranch` input, including `branchName`, `expectedHeadOid`,
bounded base64 additions and correlation ID. It never calls GitHub. Native CAS,
ledger rules/root continuity, uncertain append reconciliation and provenance must
be qualified by the later persistence owner; clientMutationId is correlation,
not native deduplication. Source-only fixtures prove neither persistence nor
exactly-once remote effects. No deletion or arbitrary path is generated.

`validate --kind source|candidate|ticket|target` consumes one bounded UTF-8 JSON
record from stdin and reports its content identity. `status` consumes a Target and
reports structural queue/slot state explicitly as offline/unverified. Mutation
verbs submit/adopt/advance/reconcile/operator-resume return unavailable. No input
file path, module name, subprocess, credential lookup or environment enable flag.
Wrapper resolution binds one complete source package or the declared installed
package; malformed selected source refuses instead of falling back elsewhere.

## Preconditions, invariants and failures

Use exact closed fields and enums; reject booleans where integers are required,
invalid UTF-8, duplicate keys, NaN/Infinity, unknown versions, unsafe branch/path
components and mixed Git object formats. Source phase commits are nonempty,
ordered, unique, and disjoint from wrappers. Original evidence never changes.
Native integers are positive and <=2^53-1 except explicit zero initial counters.
Opaque handles are 16–64 lowercase hexadecimal characters; digests are full SHA256.
Git OIDs are full lowercase SHA1 or SHA256, consistently sized within a record.
No free-form diagnostic/log/credential/task/path fields are serialized.

Ticket/source/candidate records are <=128 KiB, Target <=64 KiB, queue <=256,
retained tickets <=4096, source commits <=1024, evidence references <=512.
Both raw input and canonical writes enforce bounds. Nested dataclass serialization
is canonical JSON; decoding and encoding preserve content and immutable aliases.
Unknown errors do not echo payloads. Parser recursion errors are bounded refusals.

A stale generation, occupied slot, foreign PR/source/policy, incompatible duplicate,
capacity limit, missing qualification or outstanding reservation refuses atomically.
Delivery requires all original phase IDs in order, unique landed IDs, matching PR
and candidate; native replay/security/ancestry verification remains a port outcome.
The default unavailable implementation cannot be activated by JSON fields.

## Validation and maintenance

Use project pytest/Hypothesis and scoped ty over every new Python source and test;
configured publication/instruction checks precede runtime tests. Run oldest/newest
available supported Python for portable parsing/wrapper cases. Meaningful tests
exercise actual pure transitions and controlled store contention; no real hosted
merge, authentication, branch-rule or event-trigger qualification is claimed.

Source rollback removes only these new unused files through normal reviewed Git.
It changes no installed generation, state branch or ongoing task. Future schema
or supported-runtime changes require explicit compatibility qualification. The
lifecycle maintainer owns failures and security intake; do not retire retained
sources/receipts or bootstrap a missing ledger. No Release/Deploy/Operate applies
to this draft source slice. Maintain/Retire retains the original custody boundaries.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary/data trust | required: Domain and trust ownership table/prose; what is structural versus native authority? |
| Interaction/state | required: Behavior table; what retains a slot across uncertainty? |
| Schema | required: Interfaces and records; which content binds a generation? |
| Dependency/deployment | required: source-only ports and wrapper ownership; what remains unavailable before enrollment? |
| Quantitative | not_applicable: bounds specify refusal, with no measured speedup claim |

**Text Equivalent:** The offline core validates immutable source/ticket/target
records, computes guarded single-slot transitions and constructs expected-tip
append input. Later trusted adapters authenticate admission, native qualification,
mutation and delivery. Unknown outcomes retain reservations. Native delivery and
local cleanup remain separate. Owner: lifecycle maintainer; canonical source:
this contract and its behavior/interface tables. Update together when record
fields, guards, boundaries, runtime support or source applicability change.
