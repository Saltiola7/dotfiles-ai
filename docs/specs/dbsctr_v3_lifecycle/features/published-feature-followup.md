# Initiative follow-up on an existing published feature

Owner: lifecycle maintainer. Engineering Profile: [../PROFILE.md](../PROFILE.md).
Risk: critical; Python and Security. Source-only prerequisite, independent of any
unmerged completion implementation. This contract specifies desired capability;
it does not claim installed qualification or authorize a live PR update.

## Domain and scope

A **published feature head** is the exact current head of one native, open,
same-repository GitHub PR. A **follow-up cycle** is a new cycle at that head after
prior cycles finished feature delivery. An **accepted default** is the current
native target branch, independently fetched and observed. Neither the published
prefix nor accepted-default commits become newly owned cycle work.

Reuse Initiative receipts, `begin`, native GitHub readers, target locks, Gate
Commits, accepted-default reconciliation and Final Push. Do not reopen completed
cycles, invent a second registration/import engine, infer source ownership from
ancestry, or make failed native CI a registration success claim. Arbitrary side
branches, forks, non-GitHub registration and bulk follow-up admission are non-goals.

## Behavior

1. Given a clean linked checkout exactly at its published feature upstream, a
   fresh Build-owned Initiative receipt and an explicit follow-up PR selection,
   preflight reports the exact existing PR/head/default, documentation import,
   applicability plan, risk and launch digest without registering or editing Git.
2. Given approval of that exact plan and unchanged native identities, `begin`
   registers a new cycle in this checkout. Prior records, approvals, failures,
   commits and evidence remain unchanged; no evidence passes by registration.
3. Given absent selection, ordinary new-cycle registration still requires the
   approved comparison-base head. Unknown ahead commits remain refused.
4. Given a changed/missing/closed/forked PR, mismatched repository, branch, head,
   upstream, target, or stale digest, registration refuses without a pointer or
   partial record. Existing active occupancy also refuses; it never gets retired.
5. Given a registered follow-up, target reconciliation selects its independently
   verified accepted default, not its feature-push upstream. It may prepare the
   first no-commit merge when the cycle has no Gate Commits yet. Existing default
   content and feature fixes are both preserved; conflicts remain primary-owned.
6. Given the resulting reviewed merge and passing union validation, Final Push
   updates only the selected existing feature ref and PR. Published prefix and
   independently accepted-default ancestry are not counted as new cycle commits.
   Required evidence covers the reconciled source and every staged output.
7. Given a ready PR or a draft PR, follow-up preserves its native draft/ready
   status. It does not create a replacement PR, change target, mark ready, merge,
   delete branches, install source, or remove checkouts/data.
8. Given failed CI, local source delivery remains distinct from native integration.
   Required native success, current-base protections and exact-head merge approval
   remain mandatory. This capability admits corrective work, never a check waiver.

## CLI and private binding

Extend existing GitHub Initiative `begin` with `--follow-up-pr NUMBER`, valid only
with `--delivery-intent draft_pr`, explicit account/repository/base, and the normal
Initiative receipt/preflight/approval arguments. Low-level `start`, legacy adoption,
local-only and Forgejo paths do not gain this selector or relaxed semantics.

Launch preflight binds the selected PR number, canonical repository, current
published head, feature branch, target/default and independently observed default
head in the existing launch digest. Native `git/ref/heads` and fetched target
objects establish current default; stale PR `base.sha` alone is insufficient.
Before approved documentation import, the clean checkout must equal its configured
feature upstream and native PR head.
Reject changed push/fetch destinations and unknown unpublished commits. A selected
PR must belong to the same repository on both head and base; no fork credentials.

Store an optional version-1 `delivery.follow_up` binding containing exactly
`schema_version`, `number`, `published_head`, and `observed_base`. Existing delivery
fields own repository, account, branch and base branch; existing
`published_feature_head` preserves the approved published prefix. Validate these
fields against one another and the original launch/source baseline on reads and
writes. Missing optional binding retains historical behavior. Unknown/malformed
binding refuses; it cannot turn an ordinary record into a follow-up by inference.
No global Cycle Record schema reinterpretation or actor-authentication claim.

Registration rechecks native identities immediately before the existing locked
record/pointer write. It reuses failed-acquisition cleanup and reports unavailable
native evidence honestly. A changed observed default before registration requires
fresh preflight. This is not an atomic remote CAS: later native changes remain
guarded by fresh target/source observations and existing push/merge checks.

Documentation imports retain their exact reviewed path/blob/mode closure and
conflict refusal. Keep three identities distinct: the published prefix is the
native feature head; an import's parent is that prefix and its exact import commit
becomes the new record's `git.head`; the observed default remains
`delivery.base_head` and `delivery.follow_up.observed_base`. The launch/import
plan's comparison `base_head` is the published prefix, not the observed default.
If no import is needed, `git.head` equals the published prefix. The existing
`discovery_import` binds parent, commit and selected bytes; no import is counted
as an owned Gate Commit. Validate this exact relationship on registration/read
and before reconciliation or push. The follow-up path must not compare an import's
feature parent against the independently selected default as though they were
the same base. Registration verifies only the exact approved import may advance
the checkout beyond its observed native feature head.

This selector grants no branch-authored authority override.
Later normative changes still use the existing separately approved amendment
operation; no automatic amendment or evidence reuse is introduced.

## Reconciliation, delivery and retry

For a qualified follow-up only, `reconcile-target` uses the recorded protected
default. Preserve its normal clean-worktree, exact first-parent Gate Commit,
profile, destination, no-concurrent-Git-operation, lock and bounded-path guards.
An empty recorded prefix is allowed only when HEAD still equals the registered
`git.head`: either the published prefix or its exact approved import commit.
Independently verify accepted-default progression from the
observed base; rewrites or unknown incoming refs block. No arbitrary second parent.

When the current accepted default is already an ancestor of the registered
`git.head`, verify that containment and permit the ordinary exact owned lineage
without manufacturing a merge. Fresh union validation still applies, including
any approved imported documentation. There must be no unrecorded commits beyond
the registration baseline or arbitrary secondary-parent imports.

Otherwise reuse the existing draft reconciliation validator: exactly one reviewed
merge against the current accepted default, exact recorded first-parent lineage,
and required evidence after that reconciliation. A later default advance not
contained in the registration baseline requires a fresh reviewed reconciliation
and validation; earlier containment or merge evidence cannot cover it.
Every introduced staged path receives
matching output evidence. Required gates are revalidated over the union affected
scope; benchmark helper pins and runtime oracles are part of that closure when
helper bytes change. Never fix one source hash against a different merged helper.

Final Push rechecks selected native PR identity and expected remote head before
updating its exact feature ref. Source drift or concurrent feature advancement
refuses or enters existing supported reconciliation; no force push. Preserve the
existing finalizing/idempotent retry path after uncertain push outcomes: query the
native ref/PR before retrying and distinguish the original approved prefix from
the exact already-pushed recorded tip. No duplicate PR, commit or record completion.
Historical reads remain offline and do not probe credentials or recreate cycles.

## Validation and delivery

Red-first tests cover successful published-feature launch, ordinary-route refusal,
native identity drift, closed/forked PRs, unknown ahead commits, occupancy, stale
approval, destination changes and denied/unavailable native evidence. Exercise both
draft and ready PRs without changing their state. Verify prior completed records
and failures are byte-identical and no original execution acquires new credit.

Composed tests cover a nonempty approved documentation import followed immediately
by default reconciliation with no prior Gate Commit, and a separate successful
already-contained-default route without a fabricated merge. Also cover first-commit
default reconciliation, conflicts retaining both sides, multiple owned Gate Commits,
default advancement after initial containment or reconciliation, rejected arbitrary ancestry,
late head/base drift, staged-path evidence, push interruption and idempotent retry.
Retain GitHub new-cycle, Forgejo offline, adoption and historical-reader regressions.
Run supported Python syntax/affected typing and repository-selected publication,
instruction, lifecycle, registration, transport and benchmark/profile authorities.
Use a correctly bound project test environment; interpreter or plugin setup alone
does not establish qualification. Native current-head/base CI remains mandatory.

Kernel, Review/Integrate and Maintain/Retire are required. Source Release, Deploy
and Operate are N/A: no independent package or host activation. Deliver this
prerequisite through an ordinary fresh-main source cycle and separate draft PR,
using the currently installed writer without exercising the new route on itself.
After native green, exact merge approval and verified merge, separately approve
the managed helper/guidance activation and synthetic qualification. Only then may
a new exact approved follow-up launch use it on the retained blocked feature PR.
No existing PR closure/replacement, consumer recovery or cleanup is implied.

## Visual Evidence

Canonical owner/source: lifecycle maintainer, this feature. Update on changes to
admission, custody, delivery or activation. Tables below are their Text Equivalents.

| Concern | Disposition |
|---|---|
| Boundary | required: ownership table below |
| Interaction | required: ordered handoff table below |
| State | required: transition table below |
| Data/trust | required: custody table below |
| Schema | required: versioned binding description above |
| Dependency/deployment | required: ordered handoff table below |
| Quantitative | not_applicable: no performance benefit or numeric comparison claimed |

| Owner | Authority and limit |
|---|---|
| Discovery/operator | Exact normative receipt and launch approval; no authenticated actor claim |
| GitHub/native Git | PR/ref/object identity and permissions; supplied JSON cannot replace them |
| Existing lifecycle writer | New record, locks and evidence; no reopening or inherited gate passes |
| Managed deployment owner | Separately approved merged activation; no self-installation |

| Order | Handoff and condition |
|---|---|
| 1 | Existing writer delivers prerequisite from fresh main with tests and native CI |
| 2 | Exact approved merge verified, then separately scoped managed activation qualified |
| 3 | Fresh existing-feature receipt/preflight approved; new follow-up record registered |
| 4 | Accepted default reconciled, union gates passed, existing feature PR updated |
| 5 | Fresh exact-head/base CI and separate merge approval permit ordinary native merge |

| State | Allowed transition; refusal |
|---|---|
| No new cycle | Exact approved/native-matching launch creates active follow-up; drift refuses |
| Active follow-up | Reviewed reconciliation and evidence permit finalizing; failures retain active work |
| Finalizing | Verified exact push permits completed feature delivery; uncertainty remains retryable |
| Prior completed cycles | Historical only; no transition, evidence replacement or deletion |

| Custody transfer | Preserved boundary |
|---|---|
| Native observation to launch digest | Exact PR/head/default identities, not credentials or consent inference |
| Operator approval to new record | Caller-reported consent and versioned binding; prior records untouched |
| Gate execution to feature push | Helper-owned evidence and owned first-parent commits; imports distinguished |
| Feature delivery to ultimate merge | Fresh native CI/base guards; no inherited merge/install/delete authority |
