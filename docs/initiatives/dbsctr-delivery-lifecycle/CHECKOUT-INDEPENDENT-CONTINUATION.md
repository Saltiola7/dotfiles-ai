# Checkout-Independent Continuation

## Status And Authority

Discovery persisted 2026-09-24. Operator approved the existing three-context map,
qualified host deployment plus recovery of the nominated blocked conversation,
and one explicit release action for an idle current writer. Scope approval is
not a digest-bound implementation launch receipt or an assertion of quiescence.
No implementation, installation or live recovery is claimed by this document.

Home: `Saltiola7/dotfiles-ai`; machine authority: [MANIFEST.json](MANIFEST.json),
INT-035 through INT-048. This corrective release group extends
[canonical continuation](CANONICAL-CONTINUATION.md), retaining delivered-slice
history. It is independent of automatic merge. Proposed behavior below governs
the new slices once readiness is closed; it does not describe currently installed
capabilities or waive the delivered runtime's checks.

## Problem And Evidence

Baseline: repository commit `4df45bbc372357e6c08911c16463e9fdc14e66c5`.

| Source | Verified finding |
|---|---|
| `dot_local/bin/executable_dbsctrctl`, `worktree_id` / `worktree_for_id` | Portable identity hashes root commit and current branch. Source checkout switches break lookup; detached worktrees share the identity input. |
| Same helper, `validate_schema5_adapter` / `read_cycle_record` | Ordinary schema-5 reads resolve the historical source unconditionally, including cycle-rooted adapter locators. Source availability becomes a prerequisite for live cycle access. |
| Same helper, `continuation_target` / `command_continuation` | Target loading precedes diagnostic/ownership recovery. Target failures discard approval binding and return no next action. |
| Same helper, `command_continuation` | Completed-cycle cleanup removes routes. Recovery of an unfinished cycle clears ownership but retains selection; no explicit release transition exists. |
| `private_dot_config/opencode/plugins/continuation.ts` | Invalid-target fallback allows ordinary readers but excludes typed DBSCTR diagnostic readers. |
| `private_dot_config/opencode/lib/continuation.ts` | Adapter duplicates branch-based target lookup; response validation requires exact version-1 fields and closed reason/action sets. |
| `tests/test_dbsctrctl.py`, `test_historical_reads_validate_structure_without_live_source` | Tests deliberately allow source-independent historical reads while requiring ordinary reads to fail; correcting the contract is necessary. |

The nominated cycle's native preflight returned `invalid_target`; the attempted
shell inspection was refused with `invalid schema 5 runtime: opencode worktree`.
The exact historical private source ID was not inspected. Branch-switch causality
for that incident remains strongly supported, not conclusively established.
Source coupling and the release/recovery gaps are verified independently.

No graph was available and DKS was unavailable; evidence comes from authoritative
source. Raw sessions, private records, machine paths and credentials stay outside
Git. A new conversation or source branch switch is not the repair protocol.

## Approved Outcome And Context Map

Ordinary source checkouts never invalidate independent cycles. Invalid execution
targets deny writes without trapping diagnostics or supported recovery. Returning
an unfinished conversation to Discovery is an explicit supported transition.

| Context | Responsibility | Profile | Dependency |
|---|---|---|---|
| `dbsctr_v3_lifecycle` | Identity, validation, ownership, release and compatibility | `../../specs/dbsctr_v3_lifecycle/PROFILE.md` | Delivered continuation core |
| `opencode_control_plane` | Typed controls, diagnostic access, routing and native qualification | `../../specs/opencode_control_plane/PROFILE.md` | Corrective core |
| `dotfiles_ai_distribution` | Targeted deployment, rollback and live recovery | `../../specs/dotfiles_ai_distribution/PROFILE.md` | Corrective core and adapter |

Owner: dotfiles operator. Risk: critical for managed writer authority and dirty
work preservation. Python >=3.12, Bun/TypeScript, Markdown and existing chezmoi
machinery; no new dependency selected. Modules: Python, Security, ML/AI; Cloud
where applicable to distribution. Existing profile platform commitments remain;
this corrective live rollout is host-scoped. Guest expansion needs separate
scope/qualification and is not implied by host success.

Reuse [distribution Product Intent](../../specs/dotfiles_ai_distribution/PRODUCT.md)
for preservation and recovery outcomes. No new Product Intent is needed.
Source slices deliver feature-branch draft PRs; the rollout adds qualified host
deployment and real recovery. Existing cycles keep their recorded profiles.

## Domain And Invariants

- **Worktree identity:** stable repository-local identity verified against Git
  registration. Neither branch name nor filesystem path alone is identity.
- **Locator:** current verified location; moving or replacing it requires its own
  supported operation, not an inference from branch or recency.
- **Execution constraints:** expected branch, record state and other live checks
  required for the particular operation.
- **Provenance:** original source branch/commit and activation, retained as history
  independently of whether that checkout still exists.
- **Selection:** one session's chosen cycle, separate from writer ownership.
- **Release:** removal of selection, and relinquishment/fencing of the caller's
  writer where applicable, without completing or abandoning the cycle.

Record parsing validates schema, locator syntax and generic/legacy compatibility.
Each operation separately validates the resources it needs. Cycle writes require
the registered execution target, same common Git directory, valid execution
constraints, native authority and current writer generation. Source synchronization
still validates its exact source and destination. Missing provenance resources
report unavailability, not malformed record structure or invented attribution.

Cycle Record schemas 3/4/5 and historical record bytes remain compatible.
Compatibility bindings are explicit, bounded and identity-verified; no bulk
history rewrite, branch-hash recomputation, read-side state creation, or silent
migration. Identical remote URLs never authorize unrelated clones. Stable IDs do
not excuse registration replacement, unsafe links, branch drift or stale writers.

## Release And Recovery Contract

The operator selected one explicit action for an idle current writer; no extra
confirmation solely because the cycle is unfinished. Native actor and generation
checks remain mandatory. Current-reader release never affects another writer.

| State and request | Required transition |
|---|---|
| Reader explicitly releases | Remove only the caller's route; preserve ownership and other sessions |
| Current writer explicitly releases with no outstanding operations | Atomically relinquish writer, advance generation and remove caller's selection |
| Caller-owned running or uncertain operation exists | Refuse release pending exact-state completion or quiescence recovery; do not infer completion |
| Another session owns writer | Never relinquish or transfer that writer through caller release |
| Execution target invalid but native route/ownership state verifiable | Diagnose independently; allow only a narrowly validated explicit release, never target mutation |
| Ownership/storage state unavailable or corrupt | Refuse state mutation with a bounded supported recovery reason |
| Release committed but response lost | Idempotent replay cannot remove a later route or advance its generation |

Admission and release serialize through the same authority boundary. An admitted
operation cannot race into an untracked writer; outstanding operations and their
history survive. Generation changes fence old calls; no lease expiry or automatic
release. Cache clearing follows durable success and cannot override a newer
selection. Unrelated cycles and other readers remain independently usable.

Preserve dirty tracked/untracked/ignored work, private evidence, failed gates,
cycle ID, receipts, original activation and history. Release neither completes
nor abandons a cycle and grants no later writer automatically. Return to Discovery
requires a valid native conversation checkout and its normal ownership rules;
release does not recreate an absent native home or rebind its directory.

## Diagnostic And Adapter Interfaces

Typed control paths must remain available independently of execution admission.
Read-only diagnostics validate native/repository/store custody and project only
bounded known facts; incomplete authority remains unavailable. Distinguish source
unavailability, execution branch mismatch, missing registration, ownership conflict,
outstanding operations, storage failure and incompatible runtime capability.
Never guess a target, manufacture recovery approval or silently route to main.

Core owns authoritative target resolution. Adapter consumes verified resolution
without independently deriving identity from branch names. Release/recovery run
outside the operation accounting they must drain. Plan inspection stays read-only;
Plan and child mutation remain denied, with no provider or session substitution.

Version-1 response fields/reasons are exact in the current adapter. Do not append
fields or reasons and assume compatibility. The exact additive private schema,
`continuation-v2` envelope, compatibility activation and release replay rules are
now specified in the [core contract](../../specs/dbsctr_v3_lifecycle/features/checkout-independent-continuation.md).
Preserve existing consumers including the delivered
Codex core adapter through affected conformance tests; no Codex native expansion
is implied. Unsupported mixed versions must refuse safely before state changes.

## Delivery And Ownership

| Slice | Execution owner | Depends on | Writable implementation scope |
|---|---|---|---|
| `checkout-independent-continuation-core` | build | `canonical-continuation-core` | Shared lifecycle helper, narrowly required companion-state implementation, focused core/legacy conformance tests, completion evidence |
| `checkout-independent-continuation-opencode` | build | Corrective core | Continuation libraries/plugin, typed tools and scoped permissions, adapter tests and native probe, completion evidence |
| `checkout-independent-continuation-rollout` | build | Corrective adapter | Targeted continuation deploy assets and validators, deployment tests, recovery evidence |

Discovery owns this document, requirements, normative contracts, plans and scope.
Build findings changing them reopen readiness. Work is serial in the primary;
shared helper and native probe ownership cannot overlap adjacent active cycles.

The first core receipt declares the cross-context Discovery references and future
slice plans carried by this documentation commit. Their import does not grant core
Build ownership of adapter/distribution implementation or normative contracts.
This explicit artifact closure is required by same-repository launch preflight.

The `session-resumption` Initiative references this authority rather than starting
a competing identity/release repair. The `active-worktree-relocation` authority
exists on its separate active checkout, not this baseline. Its contract assumes
repository/branch identity and overlaps the helper. Preserve its uncommitted
draft and failed evidence. The operator explicitly approved repair-first ordering:
pause relocation implementation while this corrective core, adapter and host
recovery run, then reconcile relocation's Discovery contract through the restored
supported route before relocation resumes. Its old branch-identity assumption
must not override the corrective contract. Do not copy that manifest into main or
edit it through another cycle's selected route. This is work serialization, not
proof of writer quiescence, ownership transfer, or permission to modify its draft.
Exact live-state recovery consent remains required. Making that broken route a
prerequisite of its own repair would recreate the deadlock; INT-048 records the
approved ordering instead.

Live qualification nominates the existing `ACTIVE-RELOCATION-CORE` conversation.
Retain its draft and failed implementation gate. Prove native preflight/status,
approved ownership recovery where required, explicit release to Discovery and
subsequent validated reattachment without feature edits as test evidence.
No FNBH move, ledger credit, launcher repair, incident feature implementation,
automatic merge, broad apply, automatic restart, or private-state copying is in
scope. Process reload remains operator-controlled and retains the exact session.

Reuse targeted preview/apply/verify/rollback, private source-bound backups,
restricted configuration deltas and installed hash checks. Validate helper and
adapter as a compatible set, then the actually loaded process. Updating files
alone does not upgrade a running adapter. After new coordination state exists,
rollback must not reactivate an incompatible old writer; pause writes and use
qualified compatibility recovery or fix forward. Retain rollback and failed
evidence under existing policy; no automatic state/history pruning.

## Acceptance And Validation

| ID | Given / When / Then |
|---|---|
| CI-01 | Given an independent cycle, when its original source switches branch or is removed, then cycle diagnostics and valid execution remain available without source record rewriting. |
| CI-02 | Given a selected execution target, when its branch changes, then writes fail specifically while diagnostics and validated release remain reachable. |
| CI-03 | Given multiple detached worktrees, when resolved, then identities are distinct and unrelated or substituted registrations are refused. |
| CI-04 | Given an unfinished dirty cycle and idle owner, when release succeeds, then generation is fenced, selection cleared and candidate/record/evidence bytes preserved. |
| CI-05 | Given concurrent admission and release, when serialized, then no admitted operation is lost and no stale writer can mutate. |
| CI-06 | Given uncertain work or stale approval, when recovery/release is requested, then exact quiescence and state binding are enforced; denial is unchanged state. |
| CI-07 | Given lost release responses and later attachment, when retried or restarted, then replay cannot clear the newer route and durable state wins over cache. |
| CI-08 | Given legacy schemas and existing consumers, when inspected or explicitly bound, then record bytes/history remain truthful and read-only paths create no state. |
| CI-09 | Given real OpenCode hooks, when source switch, release, restart and reattachment run, then the same session and provider remain, reader/Plan/child denial holds, and main is never an accidental cycle-write target. |
| CI-10 | Given mixed helper/adapter versions, denied consent, configuration drift or interrupted deployment, when activated or rolled back, then unsafe mutation is refused and owned prior bytes/evidence remain recoverable. |
| CI-11 | Given installed-byte and fresh-process qualification, when the nominated existing conversation completes release/reattach, then record live operator-confirmed progress separately from fixture success. |

Red-first disposable Git repositories must distinguish source checkout, native
home and execution target; same-directory mocks alone cannot reproduce the bug.
Include source absence, registration replacement, symlink escapes, clone mismatch,
writer contention, interrupted transactions and stale-generation denial. Every
identity/resolution caller must be reviewed, including status, active pointers,
runtime attachment, delivery synchronization, cleanup and adapter caches.

Configured authorities: affected `pytest` via `uv run --group test pytest`, Bun
adapter execution, Python compilation, rendered chezmoi verification and the
loopback scripted-provider native probe. Starting affected tests are
`tests/test_dbsctr_continuation.py`, `tests/test_opencode_continuation.py`,
`tests/test_dbsctr_codex_core.py`, `tests/test_continuation_deploy.py`, and selected
identity/schema/Initiative cases in `tests/test_dbsctrctl.py`. Existing CI runs
Python 3.12/3.13/3.14 with Bun and chezmoi; broad local QA needs explicit request.
No new test framework or live provider call is needed. Current evidence is source
inspection, not passing implementation tests or native capability qualification.

## Gate Ledger And Readiness

Three companion `CHECKOUT-INDEPENDENT-CONTINUATION-*.plan.json` files live under
their owning context specifications. Build uses the committed profile identities
and materializes the execution plan through the supported lifecycle boundary.

| Gate | Core / adapter | Rollout | Result | Exception |
|---|---|---|---|---|
| Domain | required | required | pending | none |
| Behavior | required | required | pending | none |
| Spec | required | required | pending | none |
| Contract | required | required | pending | none |
| Test-driven implementation | required | required | pending | none |
| Refactor | required | required | pending | none |
| Review/Integrate | required | required | pending | none |
| Release | not_applicable: no separately versioned artifact | same | not run | none |
| Deploy | not_applicable: source-only, rollout owns installation | required | pending where applicable | none |
| Operate | not_applicable: disposable qualification only | required | pending where applicable | none |
| Maintain/Retire | required | required | pending | none |

Specification readiness closure:

1. INT-044 is resolved by the exact core contract: explicit random registration
   bindings in additive repository-local tables, unchanged historical record IDs,
   versioned v2 controls, v1 refusal for explicitly bound cycles, and replay-safe
   route versions. Unsupported moves remain refused pending relocation authority.
2. INT-045 is resolved by the operator's INT-048 repair-first ordering above.
   Relocation contract reconciliation is a prerequisite to relocation resumption,
   not to building the tooling that restores its route.
3. The operator approved a local Discovery branch and documentation commit.
   Validate artifacts and plans, then obtain a fresh
   receipt and successful typed Initiative launch preflight before asking exact
   digest-bound launch approval. Current persistence is not launch authorization.
4. Qualify critical-risk independent review through available authorized review;
   an unavailable reviewer is a gate gap, never self-approved risk acceptance.

Core specification is ready; downstream slices remain captured pending delivered
dependencies. Launch feasibility and exact digest-bound launch approval are
separate. Do not mark older delivered slices undelivered or reuse their receipts.
No implementation or live deployment gate has passed here.

Initial persistence validation: `initiative-check` accepted 47 statements, three contexts,
nine slices and four release groups. Read-only validation confirmed all referenced
artifacts exist, all pre-existing manifest entries remain identical, the three
plans pass the helper's native profile/gate validator, and 28 local Markdown link
targets resolve. These are Discovery checks, not implementation gate evidence.
Affected context READMEs and CHANGELOGs were reviewed; README references identify
pending scope, while completed-cycle changelog entries remain unchanged because
this persistence step completes no implementation cycle.

## Visual Evidence

| Concern | Decision / evidence | Review question |
|---|---|---|
| Boundary | required: context/ownership tables | Who owns contracts, control state, adapter and rollout? |
| Interaction | required: flow below | Which checks precede release and reattachment? |
| State | required: release transition table | What may change when execution validation fails? |
| Data/trust | required: flow and invariants | Does diagnostics availability grant target writes? |
| Schema | required: exact relationship table in the linked core contract | How do stable IDs, legacy records and replay bindings relate? |
| Dependency/deployment | required: slice table and rollout ordering | What must pass before live recovery? |
| Quantitative | not_applicable: no measured performance claim | No forecast is used as evidence |

```text
Native primary identity + repository/store custody
  -> read-only diagnostic snapshot (execution eligibility separately reported)
  -> explicit release request + current route/generation recheck
  -> if outstanding work: exact approved quiescence recovery, then recheck
  -> atomic relinquishment/fencing/route removal
  -> clear only the matching adapter selection
  -> valid canonical-home Discovery routing
  -> later explicit target validation and writer attachment
```

**Text Equivalent:** Native and repository authority permits bounded diagnostics,
not target writes. Release requires an explicit request, current route/generation
and no outstanding work unless exact recovery has established quiescence. Durable
release precedes cache clearing and canonical-home routing; reattachment is a new
validated action. Core precedes adapter, and both precede installed/native/live
rollout evidence. Discovery owns these tables/flow and the core schema table;
changes to authority, transitions, relationships or deployment reopen review.
