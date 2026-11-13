# Native CI applicability and candidate receipts

Discovery amendment to [integration runtime adapters](integration-runtime-adapters.md).
The lifecycle maintainer owns this critical-risk Python, Security and Cloud
extension. It is a prerequisite for hosted opt-in, not activation authority.

## Outcome and existing owners

Qualify every applicable native CI concern for the exact current candidate.
Legitimate workflow filtering must not stall unrelated changes, and missing or
skipped checks must never establish that a concern does not apply. Keep the
existing coordinator, queue, candidate slot and qualification owner. Consumers
retain check/workflow authority. Dagger remains a separate default-off shadow
observer. This change neither selects tests inside workflows nor reuses execution
results across changed inputs.

The fixed CheckPlan cannot express justified negative applicability. Some separate
producers also lack an artifact proving the tested merge object. Both gaps must
close before hosted activation; classic required contexts alone are insufficient.

## Behavior

- Native-required checks remain mandatory for every candidate, irrespective of
  mapping, paths or skipped jobs.
- A proved false supported native condition produces an identity-bound negative
  applicability result; a true condition requires current successful evidence.
- Absent, pending, skipped, failed or unbound applicable producers do not pass.
- Unknown conditions, incomplete scope, authority drift or ambiguous event
  causality block; workflow absence is not negative applicability evidence.
- A base advance or rerun requires current scope, applicability and attempt proof.
  Source-head equality alone does not preserve qualification.

## Versioned interfaces and compatibility

Preserve exact CheckPlan-v1 reading, static behavior and digest identity. Add
CheckPlan schema 2 with existing `producers` and optional `codeql` fields plus an
`applicability` binding containing repository-relative `mapping_path` and SHA-256
`mapping_digest`. Preserve HostedConfig schema 2 and existing enrollment,
candidate, queue and qualification schemas. Version-aware serialization must
round-trip both plan versions without rewriting a v1 policy identity.

The trusted-base mapping is closed schema 1: `schema_version` and `producers`.
Each row binds one producer context/app identity to an `all` array of bounded,
typed predicates. Support exact native event, exact target branch, positive
repository path patterns and exact native actor inequality. Empty conjunction is
unconditional; unmapped producers also remain unconditional. Reject duplicates,
unbound references, unknown fields, negated paths and arbitrary expressions.
Native-required producers cannot have an exempting condition.

Concrete wire shape: each mapping row has exactly `context`, `app_id`, and
`all`. Each predicate has exactly `kind` and `value`. Kinds are `event`,
`target_branch`, `paths`, and `actor_not`; values are an exact string except
`paths`, whose value is a nonempty bounded array of positive segment patterns.
The initial native pattern subset supports ASCII letters/digits, underscore,
dot, slash, hyphen and space as literals, plus `*` and whole-segment `**` only;
reject `?`, character classes, escaping and negative patterns rather than infer
equivalence. Changed-path proof includes deleted paths and both names of a rename.

Each row uses its producer's pinned workflow definition digest. Source
qualification reviews the typed predicates against the actual workflow conditions.
Runtime verifies the registered mapping digest and exact workflow bytes, then
evaluates only typed predicates; it does not parse/evaluate arbitrary Actions
expressions. Unrepresented native conditions or unsupported pattern semantics
block source qualification. New definitions require renewed mapping review.
Candidate changes to mapping or producer authority need separately reviewed plan
qualification; candidate bytes cannot authorize their own omission. This mapping
describes native workflow applicability, not a new test-impact selector.

Reuse existing CI path validation/matching only where semantics match that native
subset. Extract a pure shared owner if needed; the native adapter must not import
the lifecycle CLI. Preserve the diagnostic mapping/checker's conservative union
behavior and errors. Its affected subset is not an omission grant.

## Scope, event proof and qualification

Independently prove complete changed old/new paths from native Git objects with
no rename elision. Bind scope to candidate base/head/tested parents/tree. Require
the refreshed head's merge base to equal the candidate base before interpreting
that scope as the PR filter comparison. Missing objects, truncation, unsupported
change kinds or unproved provider comparison/limits block negative applicability.

The initial scope bound is at most 3,000 changed paths and fewer than 1,000
commits, with complete local Git object ancestry. GitHub documents a 3,000-file
path-filter limit and always-running fallback when diff generation times out.
An observed native run is therefore qualified normally even when a path/branch
predicate is false; it cannot be hidden by negative trigger proof. An absent run
requires independent false-condition proof and a final absence fence. See
[GitHub workflow trigger semantics](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

Native event proof binds repository, PR, event, source head, target branch and
causal actor where required. PR author is not event actor, and a missing workflow
supplies no causal actor proof. If native APIs cannot prove the causal event
needed by a condition, retain unavailable rather than inventing an exemption.
Actor inequality uses case-insensitive comparison, matching native expressions.
An actor/event exemption with an observed run also requires an identity-bound,
actually skipped producer job/check. Evaluate the actor predicate and verify that
skip using the same native run snapshot; a newer run, changed actor or rerun
invalidates the final fence. A skipped status alone never establishes an exemption.

Return applicable, not applicable with proof, or unavailable with a bounded
reason. Bind the complete applicability resolution digest, including negative
proofs, into each actual positive producer evidence digest in the existing
qualification. Digest mapping/workflow authority, producer, exact candidate,
complete scope and native event facts. Require at least one authentic positive
producer; do not invent native IDs or a passing Evidence record for an omitted
check. Preserve core Evidence kinds and schemas. Recheck before merge. Do not swap
global plans/enrollment per ticket; unrelated queued work retains policy identity.

## Credential-free candidate receipt

Provide one small shared receipt action and bounded writer to avoid consumer
copies. It is inert until consumers pin its reviewed merged commit. Read only
selected safe native identity fields and checked-out Git metadata, never tokens,
the full environment or full event. Use an owned runner-temporary directory,
fixed `receipt.json` and bounded output; no PR-controlled path/interpolation or
extra network/history fetch.

Receipt schema 1 binds repository, PR source head, tested commit/tree, ordered raw
commit parents, run ID, attempt, event, concern/job discriminator and terminal
concern result. PR tested HEAD must equal the native tested SHA and parents must
equal the candidate base/head. Read raw headers to support shallow checkout.
Validate before output. Include tested SHA and attempt in artifact names. Failure
receipts are diagnostic. The verifier still requires current native job and whole
workflow success, exact app/workflow identity, unique artifact, native archive
digest and bound receipt fields. Existing suitable receipts remain supported.

Preserve scan/smoke command, exit, trigger, condition, permissions, runner,
container, matrix and timeout. Metadata does not turn diagnostic CI into a gate.

## Source slice and acceptance

Own shared plan parsing/serialization, native applicability verification, a pure
matcher extraction only if necessary, credential-free receipt action/writer,
focused tests and existing Initiative docs. Exclude consumer workflow wiring,
installation, state refs, secrets, protections and opt-in. Target wiring follows
merged shared source; native qualification and credential delegation stay separate.

Registration inventory also needs the bounded historical-profile reader repair
in [retained cross-repository authority](cross-repository-initiative-amendment.md).
An unrelated current checkout must not invalidate a completed record whose local
profile and retained authority are intact. Bind historical profile lookup to the
approved amendment's immutable source commit; keep live profile selection and all
custody/history checks. Test another checkout's later profile, malformed/moving
selectors, unavailable commits and wrong blobs. No record edits or inventory
exemptions are included. This is a source prerequisite, not a launch bypass.

Tests must cover v1 digest/behavior compatibility; v2 closed parsing/round trips;
mandatory native checks; true/false/unknown predicates; path/deletion/comparison
limits; missing/forged actor proof; authority/candidate drift; negative-proof
binding; reruns; missing/skipped workflows; malformed/duplicate/stale receipts;
safe temporary output; shallow-parent reads; and default-off behavior. Run
affected helper/coordinator/controller/client/workflow tests, project typing and
publication authorities. Preserve unrelated typing baselines.

Rollback disables opt-in first and retains state/evidence. Older writers reject
unsupported v2 plans; no automatic downgrade or state rewrite. The runtime
dependency is verified merged through the native rebase route, with
individual commit correspondence and identical qualified tree. Source launch still
requires fresh exact preflight and operator approval; source readiness is not
installed or live activation.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: authority flow table below |
| Interaction | required: qualification order table below |
| State | required: applicability outcome table below |
| Data/trust | required: authority flow table below |
| Schema | not_applicable: bounded version extension is defined in interface prose |
| Dependency/deployment | required: delivery dependency table below |
| Quantitative | not_applicable: no throughput comparison is claimed |

| Source | Direction and recipient | Authority |
|---|---|---|
| Trusted default mapping/definitions | To native adapter | Supported applicability policy; candidate cannot exempt itself |
| Native Git/event/run/job APIs | To native adapter | Complete scope, causality and producer identity |
| Producer receipt artifact | To native adapter | Candidate identity; never substitutes native success |
| Native adapter | To existing qualification/controller | Positive evidence and negative proofs; unknown blocks |

**Text Equivalent:** Trusted default policy, independently proved native facts and
bound receipts enter the same adapter. That adapter supplies existing qualification;
PR content and artifacts grant no policy authority.

| Order | Action | Guard |
|---|---|---|
| 1 | Capture candidate/scope | Exact current base/head/tested parents/tree |
| 2 | Load mapping/workflow authority | Trusted-base regular blobs and reviewed definitions |
| 3 | Determine applicability | Native-required always applies; unknown blocks |
| 4 | Verify applicable producers | Current native success, attempt and candidate evidence |
| 5 | Bind evidence and repeat freshness guards | All positive/negative proof covers same candidate |

**Text Equivalent:** Candidate and authority capture precede applicability, then
producer verification, evidence binding and fresh guards precede the existing merge.

| Condition | Outcome | Effect |
|---|---|---|
| Mandatory or supported true condition | applicable | Require successful current producer |
| Supported false condition with complete proof | not applicable | Bind negative proof; never claim a passing test |
| Unsupported, incomplete, stale or ambiguous | unavailable | Block; absence/skips cannot exempt |

**Text Equivalent:** Only a proved false supported condition justifies omission.
True requires success; unknown blocks.

| Dependency | Deliverable | Boundary |
|---|---|---|
| Merged runtime adapters | Shared applicability/receipt source | Source-only, default-off |
| Reviewed merged shared implementation | Target disabled caller/receipt wiring | Existing CI preserved |
| Qualified target facts and explicit delegation | Public pilot, then governed consumer qualification | Live opt-in and A/B competition proved separately |

**Text Equivalent:** Shared source precedes target pins. Target source and native/
credential qualification precede live opt-in. One target's success does not prove
another's. Tables are canonical here; lifecycle maintainer updates them when
authority, interfaces, states or ordering change.
