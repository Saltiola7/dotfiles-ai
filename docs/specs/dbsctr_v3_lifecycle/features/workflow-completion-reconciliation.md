# Discovery-defined completion and automatic reconciliation

Owner: lifecycle maintainer. Engineering Profile: [../PROFILE.md](../PROFILE.md).
Initiative: [workflow convergence](../../../initiatives/dbsctr-workflow-convergence/COMPLETION-RECONCILIATION.md).
Risk: critical; modules: Python and Security. This is approved normative Discovery,
not installed behavior. Source delivery is a draft PR; rollout is separate.

## Outcome and precedence

Discovery defines ready and done. A cycle completes when its effective approved
requirements, applicable gates and delivery obligations are satisfied, irrespective
of the number of PRs or approved amendments. Git topology is provenance evidence,
not the definition of done. No success follows merely from a merged PR.

For the newly qualified reconciliation route, this contract supersedes the
first-parent equality requirement of external completion, amendment/recovery mutual
exclusion in lineage recovery, blanket required-gate invalidation on amendment,
and HEAD-only invalidation of otherwise unaffected evidence. Historical receipts
retain their original meaning. Existing exact-tree and rebased-commit proofs
remain valid; no new interpretation of an old receipt is implicit.

Logical successful completion is independent of checkout, branch, session and
data cleanup. Administrative cancellation/retirement remains a distinct outcome.
No successful recovery may substitute retired or abandoned for completed.

## Ready and done authority

Discovery artifacts bind stable requirement IDs, acceptance behaviors, dependency
edges, required evidence authorities, affected source/configuration scope, external
environment obligations and source-versus-activation delivery targets. Existing
profiles and applicability plans remain authoritative; no second policy engine.

Ready requires complete scope/ownership, resolved material decisions, supported
completion/recovery capability for the proposed workflow, publication checks and
an artifact-ready applicability plan. Build launch additionally requires fresh
receipt/preflight and exact launch approval. Specification readiness is not launch
or runtime readiness.

Done requires a requirement-to-evidence disposition for every effective requirement,
all required gate decisions (or existing valid permitted exceptions), verified
delivery proof for the selected target, and actual release/deploy/operate outcomes
where applicable. An amendment records old-to-new requirement correspondence;
removed requirements retain historical dispositions, not fabricated passes.
Editorial authority changes still need valid Discovery authority import, but do
not by themselves invalidate unchanged behavior evidence.

## Domain and private record contract

Use the existing Cycle Record and immutable private custody owner. Add an optional
versioned reconciliation reference; keep original registration, baseline, commits,
imports, approvals, amendment checkpoints and failures unchanged. Do not rewrite
record.commits to resemble the current integration branch.

| Entity | Required relationships |
|---|---|
| Authority revision | Verified original or amended receipt; stable requirement mapping |
| Delivery segment | Exact repository, target, PR head and observed merge result; one existing qualified proof kind |
| Provenance classification | Original cycle commit, verified authority import, reviewed non-gate documentation, or accepted target integration; every intervening change accounted for |
| Evidence binding | Existing immutable envelope plus authority revision, requirement IDs, normalized dependency scope and source/environment identities |
| Reconciliation outcome v1 | Original-record digest, current HEAD/tree, observed target, ordered segments/classifications, evidence dispositions and original-byte preimage |
| Completion outcome | Exact effective authority and reconciled proof references; no cleanup side effect |

Each evidence disposition is retained, rerun_required, unavailable or superseded,
with a bounded reason code. Retained evidence gets a new applicability decision,
not a forged execution timestamp or replacement of its original envelope.
Machine-owned custody and comparisons are proof; caller-authored JSON is not.

Readers validate historical custody without requiring the original checkout or
live credentials. New writers reject unsupported versions; old writers must be
excluded during activation. Preserve schema 3/4/5 historical reading and schema-6
local-only behavior. Local-only reconciliation never fetches or claims external
delivery. Unsupported foreign-forge delivery stays typed unavailable.

## Provenance and supported Git journeys

Support multiple already-merged same-repository PRs and intervening approved
amendments, merges from the approved target, and fast-forward to a verified merge
result. Retain original source objects under the existing private evidence-ref
owner, with compare-and-set creation and no automatic disposal or publication.

Classify the entire change range, including side parents, before assigning success:

1. Original cycle commits retain their recorded gate relationships wherever they
   occur in the DAG. Ancestry alone does not prove unchanged behavior at completion.
2. A verified authority import must exactly match its approved artifact closure.
3. Non-gate documentation must be regular nonexecutable reviewed documentation,
   bound to artifact review and publication checks. It supplies no gate credit.
4. Accepted target history must be reachable from the freshly observed approved
   target and have exact Git parents/trees and native delivery metadata where
   applicable. Unrelated accepted target work is not attributed to the cycle.
5. Arbitrary side-branch imports require explicit scope/authority selection through
   existing review authority before reconciliation. Unknown code commits are not
   auto-adopted because they happen to be ancestors or touch familiar paths.

Verify each PR segment using the existing exact-tree or rebased-commit proof
authority, including native repository/head/target identity and actual Git objects.
No blanket patch-ID or final-tree similarity proof. Unsupported transformations
retain work and name the missing capability. A later segment cannot silently undo
an earlier accepted requirement: final dependency-scope comparison and applicable
validation must establish the effective result. A verified native merge is not
proof of CI compliance, approval, deployment or acceptance.

Ordinary tracked deletion works both staged and unstaged. Derive tracking from
the validated parent/baseline tree, not solely the current index. Use the existing
absence representation (`null`) with an explicit predecessor blob/mode proof in
new custody. Never-tracked missing paths remain invalid. Renames are explicit
delete/add; path safety and secret-path restrictions remain unchanged. Read and
commit the same normalized path set; stage ordering must not change admissibility.

## Affected evidence reconciliation

[Trusted evidence bindings](workflow-evidence-bindings.md) defines the concrete
approved-plan declarations, helper-owned capture, bounded runtime probes and
active legacy enrollment/revalidation protocol required by this section. Changed
Gate Commit paths alone are not complete validation-input declarations. Missing
metadata is a supported revalidation obligation, never fabricated equivalence or
a permanent refusal with no capture interface.

Compute the affected closure from trusted requirement/dependency declarations and
actual blob/mode/configuration deltas, not extension-only or branch-authored claims.
Unknown dependency scope invalidates conservatively; it never proves unaffected.

Reuse an execution result only when command, authority, toolchain, environment,
normalized input scope and all relevant source identities match. Original commit
identity remains in the envelope; a new HEAD needs an explicit equivalence binding
for unchanged declared inputs, not alteration of that envelope. This is a reviewed
extension of exact-commit reuse, not permission to ignore arbitrary commits.

Runtime evidence additionally binds deployed artifact/configuration, target and
its declared freshness rule. A docs-only commit need not rerun deployment if those
identities and freshness still hold. A changed deployment or expired required
observation does. Missing legacy bindings are unavailable and require bounded
revalidation; do not infer them from a successful status bit.

An amendment reopens changed requirements and transitive dependants; unaffected
requirements retain proven applicability. A failed rerun still invalidates its
dependants under the existing failure policy. Preserve all failed runs and genuine
exceptions. A transient credential failure cannot itself waive live evidence.

## Interfaces, ordering and automatic recovery

Extend existing status, begin preflight, initiative-amend preflight,
reconcile-target and complete-external boundaries; do not add a parallel workflow
engine. complete-external retains the single-PR interface and adds repeatable
`--delivery-segment PR:HEAD:MERGE` selectors for preceding segments. The existing
`--pr-number/--expected-head/--expected-merge` pins select the final segment.
Selectors identify candidates; independent native proof is mandatory.

`complete-external --preview` is read-only for cycle state, refs, index and worktree.
It reports all bounded discoverable blockers and stage availability in one result:
authority, topology/provenance, evidence applicability, delivery, runtime and
cleanup (cleanup is informational). Structural checks precede expensive remote,
credential and runtime checks. Blocked structural prerequisites mark dependent
checks not_evaluated rather than launching them or declaring them passed.

The normal non-preview completion invocation automatically reconciles uniquely
provable bookkeeping under existing cycle authorization, without an additional
operator approval ceremony. Reconciliation cannot approve an amendment, merge,
deployment, new import scope or deletion. Material scope changes still return to
Discovery and their existing consent boundary. An already approved amendment and
verified PR pins do not require redundant approval merely to restore consistency.

Use shared cycle/target mutation locks, exact original-byte digest, current source,
authority and target observations. Persist immutable preimage/proof and deterministic
outcome before atomic record replacement; reconcile matching pointers after save.
Crash after prepare or after save supports exact idempotent retry. Changed state
recomputes a fresh proof; it cannot apply stale effects. Conflicting custody blocks
with actionable codes. No hand editing, baseline reset or history rewrite.

Only compute once per unchanged input set during an invocation. Bound metadata
and Git work using existing limits; exceeding a limit returns an actionable
continuation/partition requirement, never a truncated success. Credential expiry
reports the prerequisite once; retry only classified transient failures with the
existing bounded policy. Do not retry deterministic lineage, permission or scope
failures. Recovery remains available after every supported authority transition.

## Behaviors and acceptance matrix

| Given / when | Required result |
|---|---|
| Approved amendment between two merged PRs, then fast-forward and reviewed changelog | Public CLI completes with verified segment/requirement proof; original history retained |
| Merge/import then amendment, or amendment then reconciliation, repeated | Both orders have supported continuation; no categorical amendment exclusion |
| Only unrelated accepted target or editorial source changes | Reuse proven unaffected evidence; no fabricated new execution |
| Relevant source, command, toolchain, environment or freshness changes | Reopen exact affected closure, or conservatively rerun when scope is unknown |
| Early merged work later reverted or changed | No completion from ancestry alone; effective acceptance required |
| Unknown code import or mismatched PR/target | Block before runtime checks; report all structural blockers and supported resolution |
| Staged/unstaged deletion or rename | Equivalent evidence/commit/read/completion behavior with tracking proof |
| Prepared transaction interrupted; save acknowledged late | Exact retry completes once, preserves preimage and failures |
| Concurrent writer, changed target or conflicting pointer | No stale replacement or pointer theft |
| Done met but checkout has retained ignored data or cleanup consumers | Logical completion succeeds if source is valid; cleanup remains independently blocked |
| Dirty tracked source or unknown source changes | Completion blocks; no automatic add, stash, reset or overwrite |
| Supported local-only cycle | Local completion remains offline; no external delivery assertion |
| New proof read by incompatible writer | Explicit unsupported outcome, never erasure or reinterpretation |

## Validation and maintenance

Use disposable synthetic public-CLI journeys across registration, amendment,
integration, completion and historical reading, rather than only helper-unit
refusal tests. Include two and three PRs, ordinary and rebased segments under their
qualified limits, multiple amendments, unrelated target advance, doc-only final
commit, stale live evidence, missing credentials and all interruption boundaries.
Use existing native metadata fixtures; private consumer content never enters tests.

Require passing negative cases for arbitrary import laundering, evidence forgery,
missing objects, replacement/graft influence, unsafe Git attributes, partial
metadata, invalid exception, removed requirements without authority, path escape,
secret disclosure and deletion without consent. Existing exact-tree/rebase,
amendment/checkpoint, DVC preservation, local completion and retirement tests pass.

Configured authorities: affected pytest and compilation, repository instruction
and public-content checks, supported Python/runtime CI. Core plan requires kernel,
Review/Integrate and Maintain/Retire; Release/Deploy/Operate are source-only N/A.
Independent security review is required before activation. Source tests do not
qualify installed migration. Retain compatible readers, preimages and evidence
refs during rollback; stop incompatible writers rather than downgrading records.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: domain/ownership table above and Initiative context map |
| Interaction | required: ordered protocol below |
| State | required: transition table below |
| Data/trust | required: provenance classification and custody flow below |
| Schema | required: domain/relationship table above |
| Dependency/deployment | required: Initiative slice DAG |
| Quantitative | not_applicable: no performance improvement claim |

| Order | Interaction / data flow |
|---|---|
| 1 | Discovery authority and Git objects → read-only structural classification |
| 2 | Native metadata and immutable envelopes → independent proof/applicability decisions |
| 3 | Locked exact state → private preimage, reconciliation proof and outcome |
| 4 | Atomic logical completion → matching pointer reconciliation |
| 5 | Separate cleanup authority → optional preservation and removal; never prerequisite to step 4 |

| State | Event | Next state |
|---|---|---|
| Active | Provable reconciliation; remaining obligations | Active with retained proof and affected work |
| Active | All effective obligations proven | Completed; cleanup independent |
| Active | Missing/ambiguous proof | Active blocked with specific recovery action |
| Prepared | Interrupted | Recover exact transaction or retain conflict |
| Completed | Identical retry | Already completed; no repeated side effects |

**Text Equivalent:** Discovery supplies authority, Git/native metadata supplies
delivery proof, and immutable envelopes supply execution evidence. A locked
reconciliation preserves originals and binds only justified applicability. All
effective obligations permit completion; missing proof retains an actionable
active record. Cleanup is independent. Canonical owner: lifecycle maintainer;
update these tables with authority, schema, ordering or transition changes.
