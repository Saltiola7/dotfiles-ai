# PY-09 Build handoff: measurement before optimization

Status: specification ready; implementation, full measurements and launch
feasibility unverified. Home repository and coordinator: `Saltiola7/dotfiles-ai`.
This document extends existing `dbsctr-cycle-speed` authority; it creates no
parallel Initiative, lifecycle controller, permanent service or PM workflow.

## Approved decisions and facts

The operator approved the three active owners, reusable opt-in benchmark tooling
and evidence format, and disposable local synthetic fixtures plus retained CI
evidence on 2026-10-31. Retired DKS/model-service measurements are deferred.
Fresh CI measurement dispatch and live host/service profiling are not selected.
Ordinary source-validation CI remains required when source is delivered.

The prior Python audit identified source-backed performance hypotheses and slow
retained CI jobs. It did not collect representative CLI or snapshot resource
baselines. Historical CI success proves behavior on its matching tree; it does
not qualify another source or establish a comparable performance population.
No expected speedup, memory saving or performance pass is asserted here.

Existing `lifecycle-performance-core` and `validation-execution-performance`
contracts remain the optimization owners. New precursor dependencies supersede
old receipts/readiness without implementing those optimizations. All material
PY-09 decisions are INT-080 through INT-095 in MANIFEST.json.

## Context map, slices and source ownership

| Order/slice | Profile and modules | Source boundary | Dependency |
|---|---|---|---|
| 1: `python-cli-baseline` | Lifecycle PROFILE; Python/Security | Common evidence/report code, opt-in CLI benchmark and synthetic fixtures/tests under `tests/benchmarks/` | Delivered `performance-audit-workflow` |
| 2: `python-ci-baseline` | Distribution PROFILE; Python/Security | Retained-job parser and synthetic fixtures/tests; no workflow edits or dispatch | Delivered CLI baseline |
| 3: `python-snapshot-memory-baseline` | Continuous-validation PROFILE; Python/Security | Isolated capture benchmark and synthetic fixtures/tests; no runner, enrollment or worker changes | Delivered CLI baseline |

Canonical contracts:

- [Shared protocol and CLI](../../specs/dbsctr_v3_lifecycle/features/python-performance.md#py-09-measurement-only-foundation).
- [Retained-CI precursor](../../specs/dotfiles_ai_distribution/features/validation-execution-performance.md#py-09-retained-ci-baseline-precursor).
- [Snapshot measurement](../../specs/continuous_validation/features/snapshot-performance-baseline.md).

Current primary performs context work serially and owns integration. Later owners
consume delivered common evidence code without parallel edits. Production source
refactors, Python floor/tool migrations and all other Python-audit findings remain
separate work. Existing roots, schemas, runtime routes, native identity, gates,
privacy, standalone deployment and retention contracts remain authoritative.

The CLI slice must import the complete changed-document closure listed in its
manifest artifacts, including carried unmerged Discovery authority. Dependent
slices obtain a fresh receipt after prerequisite source delivery and reconcile
any changed closure. Do not publish precursor docs separately merely to satisfy
an upstream requirement. Same-repository source delivery carries approved docs.

## Acceptance and evidence

A successful source slice delivers opt-in tooling, deterministic bounded fixtures,
validated evidence and focused passing source checks. Measurement completeness
is independent: full cells require the declared attempts/qualified metrics;
partial smoke, missing RSS, absent CI identities and unsafe/unavailable workloads
remain explicit. There is no speedup threshold for baseline tooling acceptance.
Optimization thresholds apply only to later matched candidate comparisons.

| Surface | Initial workload and measurement | Important limit |
|---|---|---|
| CLI | Help, empty status and valid 10/100-node Initiative checks on 1/100-commit synthetic histories; one warmup plus ten attempts | Whole-process wall timing; Git counts/profile attribution in separate cohorts; OS cache uncontrolled |
| Retained CI | Explicit existing metadata/log files grouped by exact source, workflow, runner/toolchain and runtime/Worktrunk identities | No new jobs; queue/setup/job/test timing separate; counts do not prove unique-test coverage |
| Snapshot | Live plus unique history at 1/16/64/240 MiB, bounded file layouts and one/two isolated controllers | Default smoke 1/16 MiB; per-controller OS RSS distinct from traced allocations, Git children, combined host memory and responsiveness |

Raw records/profiles/logs stay owner-private outside Git. Generic tooling and
synthetic fixtures pass the existing public-content authority. No private stores,
credentials, real operator/session identities, actual machine paths or raw source
bodies enter public artifacts. No hosted research receives runtime evidence.

Use existing project dependencies and supported Python/Git authorities. Source
profiles select pytest/compilation/publication and configured CI. No new profiler,
checker or environment install is authorized. Root typing authority remains
unconfigured; static-analysis coverage is unavailable rather than a claimed pass.
No full-repository typing migration or metric qualification follows from this work.

## Gate applicability

Each source slice is elevated risk: it executes selected committed Python in
isolated fixtures and handles potentially sensitive raw profiles/logs. Committed
plans name existing profiles:

- `PYTHON-BASELINE.plan.json`: lifecycle.
- `CI-BASELINE.plan.json`: distribution.
- `SNAPSHOT-BASELINE.plan.json`: continuous-validation.

Domain, Behavior, Spec, Contract, Test-driven implementation, Refactor,
Review/Integrate and Maintain/Retire are required. Required results start pending.
Release is not applicable: no independently published package/image. Deploy and
Operate are not applicable: source-only fixtures/retained files, with no installed
runtime, worker or service change. No exception or automatic evidence admission
is selected. Build persists the applicable plan under its ignored plan directory.

README, PROFILE and CHANGELOG were reviewed for all three contexts. Stable profile
ownership is retained; feature contracts carry cycle overrides. No completed-cycle
CHANGELOG entry is written during Discovery because tooling, measurements,
deployment and source delivery are not complete.

## Validation and launch handoff

1. Verify fresh approved base, existing source/fixture interfaces and complete
   intended document closure. Preserve unmerged docs, dirty work and other audits.
2. Run the existing publication authority over all intended tracked/staged added
   artifacts and the existing instruction/lifecycle tests. Run `initiative-check`
   after every material manifest change. A manifest check alone is not privacy.
3. Immediately before promotion, obtain a fresh digest-bound `initiative-receipt`
   for exactly one dependency-satisfied slice. Use a Worktrunk code-only task
   checkout at the approved fetched base and intended upstream. Import only the
   exact approved document closure through the existing Initiative route.
4. Run real launch preflight before requesting approval. Present exact scope,
   elevated risk, target and launch digest. Only explicit digest-bound approval
   permits registration; this Discovery invocation is not that consent.
5. Build one source slice through existing DBSCTR and applicable tests. Preserve
   failing evidence, report actual baseline capabilities and unavailable cells,
   and deliver source through normal review/CI. Reobserve prerequisite delivery
   before promoting the next slice; no unattended multi-slice launch.

Recommended Build owner: current primary with applicable Python/Security guidance.
Launch preflight and implementation are not performed by this Discovery. No
remaining product/scope question blocks specification readiness; fixture/OS
capability failures must remain explicit evidence or reopen readiness if they
would change the selected interface, safety or ownership.

## Risks and maintenance

- Instrumentation and OS cache/load can distort comparisons. Separate cohorts,
  retain attempted denominators and report inconclusive results without retuning.
- Source interfaces, Python/OS resource units and CI log formats can change.
  Freeze identities and requalify affected capabilities; never infer missing units.
- Larger synthetic captures may exhaust resource/time budgets. Stop and retain
  partial evidence; do not resize silently or claim an OS RAM cap.
- New dependencies alter receipts for already specified optimization slices.
  Fresh validation/receipt/preflight is mandatory; no old approval is reusable.
- Removing opt-in source tooling is rollback. Prior measurements and private
  production state are preserved; no migration, cleanup or retention deletion.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: context/source ownership table above answers who can edit each artifact |
| Interaction | required: ordered launch handoff above preserves validation, receipt, preflight and approval order |
| State | not_applicable: slice states remain canonical in MANIFEST.json; attempt state is in feature contracts |
| Data/trust | not_applicable: canonical feature contracts define synthetic/private evidence boundaries |
| Schema | not_applicable: shared evidence-format table in lifecycle feature owns additive benchmark records |
| Dependency/deployment | required: slice dependency table above; runtime deployment is excluded |
| Quantitative | not_applicable: no observed benchmark distributions or improvement claims exist |

**Text Equivalent:** The lifecycle foundation precedes both measurement consumers.
Distribution and continuous-validation own distinct code and tests. Validation
precedes receipt, actual preflight and exact approval; no stage implies the next
has succeeded. Source delivery is separate from measurement completeness and
runtime activation. Canonical owner: current Discovery primary and respective
context maintainers; update these tables with changed ownership or handoff order.
