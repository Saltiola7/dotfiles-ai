# PY-08 Python runtime qualification handoff

Status: approved authority adopted; source prepared for hosted qualification.
This is one same-repository import slice for the selected PY-08 scope. It adds
no independent context or implementation lane. The operator selected policy and
root qualification with preserved runtime pins, weekly/manual-first 3.15, and
monthly review with urgent security intake. Native registration and the approved
publication-order amendment are preserved in the active Cycle Record. This
manifest continues to express specification readiness, not a live runtime pass.

## Context map and source authority

| Implementation context | Home repository | Dependencies and ownership |
|---|---|---|
| `dotfiles_ai_distribution` | `Saltiola7/dotfiles-ai` | No predecessor slice; owns runtime-review policy, hosted root qualification and compatible fixture repair |

Lifecycle remains the adjacent owner of publication/approval semantics, with a
distribution-owned cadence amendment in its existing document. Continuous
validation, knowledge-store, security-toolkit and other isolated runtime owners
retain their pins, interfaces, disabled states and future upgrade obligations.

The existing distribution Engineering Profile and Product Intent remain
authoritative. The [feature contract](../../specs/dotfiles_ai_distribution/features/python-runtime-qualification.md)
contains behavior, acceptance, evidence, risks and the eleven-gate ledger.
[SOURCE.plan.json](SOURCE.plan.json) is the machine applicability plan.
[MANIFEST.json](MANIFEST.json) is the complete statement and artifact inventory.
The existing update runbook remains the canonical installer/procedure inventory.

## Material statement coverage

| Statements | Scope and canonical coverage |
|---|---|
| INT-001, INT-002 | Single distribution ownership, retained floor and current PR authority; feature scope/ownership and Engineering Profile |
| INT-003, INT-008, INT-013 | Weekly/manual 3.15, full exact-source qualification, existing required checks and validation-publication order; feature acceptance/sequence amendment and existing cadence amendment |
| INT-004, INT-006, INT-012 | Monthly/urgent review, existing owner procedures and regression recovery; update runbook and feature maintenance contracts |
| INT-005, INT-009 | Preserved isolated pins, activation boundaries and non-goals; feature runtime boundary and scope |
| INT-007, INT-010 | Demonstrated compatible repairs and qualification risks; feature porting evidence and acceptance |
| INT-011 | Complete import closure, clean approved-base checkout and exact launch approval; Build handoff below |

Every statement is ready for the one `root-source` Build slice. Ready means
specified and covered, not implemented, tested, delivered or activated. There are
no deferred requirements or unresolved product choices in this selected scope.

## Build handoff

Risk: elevated. Modules: Python and Security. Delivery: one source/hosted-CI
implementation PR; no live installation or service operation. Kernel,
Review/Integrate and Maintain/Retire are required; Release, Deploy and Operate
are not applicable for the reasons in the committed plan and feature ledger.

Use one Build primary. Retain unmerged Discovery commits as the import authority;
do not reset them or publish a preliminary documentation-only PR. Prepare one
clean code-only checkout through the native Worktrunk template at the freshly
fetched approved remote base, with the intended upstream. Copy the reviewed
machine plan into that checkout's Git-ignored `.dbsctr/plans/` location.

Run the existing publication authority over the exact candidate/import closure,
then refresh the native Initiative receipt for `root-source`. Run real
`dbsctrctl begin --preflight` with the manifest, slice, manifest digest, plan
digest, repository identity and explicit Discovery source. Resolve actual
blockers before requesting exact scope/risk/target/launch-digest approval. Only
after that approval may Build register with the exact expected launch digest.
No terminal consent, session attachment or operator identity is manufactured.

The import closure includes this README, manifest and plan plus the feature,
distribution PROFILE and README, update runbook and existing lifecycle cadence
amendment. Retain the entire closure in the implementation PR. Fresh receipts
and preflight are required if its authority changes. Specification readiness
does not establish checkout feasibility or a qualified interpreter.

Build changes only the weekly/manual root matrix, explicit frozen interpreter
selection and demonstrated compatible fixture/source repairs. Preserve 3.14
PR/main, root 3.12, all isolated pins and every security assertion. Complete the
focused oldest/newest regression, exact-source full manual matrix and existing
required checks before qualification. No runtime owner upgrade is delegated.

The feature's sequence amendment addresses hosted CI's need for a published
candidate. After exact native amendment approval, local TDD/oldest-newest checks
dispose Test, then recorded Gate Commits may receive one normal candidate branch
push/draft PR solely for validation. Review/Integrate stays open until the full
hosted matrix and current PR checks pass. Final Push and cycle completion still
require every applicable gate; no evidence waiver or Gate Exception is selected.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: Context map above identifies the sole implementation owner and unchanged adjacent owners |
| Interaction | required: Build handoff orders publication, receipt, preflight, exact approval, registration and qualification |
| State | required: Feature qualification-state table distinguishes specification readiness, candidate failure and actual qualification |
| Data/trust | not_applicable: no private runtime inventory or credential transfer; reuse existing publication authority |
| Schema | not_applicable: reuse existing Initiative/plan schemas without changing them |
| Dependency/deployment | required: Context map and Build handoff distinguish documentation import, hosted CI and unchanged live runtimes |
| Quantitative | not_applicable: no measured speedup, cost or capacity claim |

**Text Equivalent:** One distribution slice carries the entire same-repository
Discovery closure into a source-only implementation PR. A clean approved-base
Build checkout and fresh receipt/preflight precede exact launch approval and
registration. Actual Python 3.15 qualification follows implementation and full
candidate evidence; isolated runtimes stay unchanged. Canonical source: context
map, manifest and feature acceptance. Owner: distribution maintainers. Update
trigger: ownership, requirements, artifacts, dependencies, launch or qualification
contracts change.
