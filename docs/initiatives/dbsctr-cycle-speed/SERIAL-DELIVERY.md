# Serial Delivery

## Scope And Authority

The existing four-context map remains approved: lifecycle, OpenCode control
plane, distribution, and DKS, all in dotfiles-ai. One invoking primary performs
Discovery and implementation serially. No child sessions or subagents launch.
Adjacent Codex and unrelated PRs receive ownership review only. Preserve existing
dirty and unmerged work; prefer verified resumption to duplicate implementation.

There are twelve sequenced delivery units. Historical reporting repair and the
refresh scheduler are delivered, leaving ten. This is not a promise that every unit is
ready. Discovery owns contracts and can split a unit only after material scope is
reconciled. Concurrency implementation and activation are deferred until
separately approved; its benchmark requirements remain unchanged.

## Sequence And Readiness

| Order | Slice | Readiness work before launch |
|---|---|---|
| 1 | historical-reporting-repair | Delivered in PR #144, merge `3b79749a1e8c6eb0fc7c261a75bdcffa5a4cbecf` |
| 2 | history-projection-refresh-schedule | Delivered in PR #148, merge `0773ed9f2d3525ca8106a5f9b7f02a2acac6f9e7` |
| 3 | dks-routing-disable | Delivered in PR #156, merge `943c4f31e731f5ec5d7ab4e8d03df4efd0541fce` |
| 4 | dks-host-disable | Exact runtime targets and residual classes ready; fresh approval required |
| 5 | dks-state-retirement | Irreversibly delete proven DKS state after fresh destructive confirmation |
| 6 | history-incident-runtime-recovery | Select numeric subprocess deadline independent of deferred DKS work |
| 7 | performance-audit-v2 | Bind fixed-source reducers, immutable cohorts, and report-only behavior |
| 8 | opencode-runtime-adapter | Specify authoritative events, pauses, crashes, and duplicate-event handling |
| 9 | federated-cycle-trends | Complete source bounds, capture/replay contracts, and availability handling |
| 10 | validation-evidence-reuse | Complete exact identity eligibility and invalidation contracts |
| 11 | agent-context-budget | Specify measurable retrieval/compaction rules without dropping safety evidence |
| 12 | dks-routing-value-gate | Qualify paired fixed-source behavior after DKS/runtime/privacy prerequisites |

This order is an execution constraint, not a replacement for manifest dependency
edges. A completed specification does not make implementation or deployment done.
Existing ready labels still require fresh receipt and source checks after any
manifest revision; none authorizes launching all units as an unattended batch.
The first scheduler Build receipt was retired empty after exact status fields and
retention were found unresolved. No implementation change was preserved from it.
The approved replacement cycle delivered the scheduler in PR #148. DKS PR #130
was then reconciled onto current main and retained its tests and exact busy output,
but live contention returned in 7.87 seconds because PostgreSQL session cleanup
outlived the two-second lock budget. Its candidate deployment was rolled back and
the PR closed with its branch and Cycle Record preserved. The operator chose full
production retirement instead of remediation. DKS optimization, privacy,
recovery, and value-gate slices remain blocked until controlled re-enable.

## Reporting Repair Boundary

Given a retained record with a missing historical checkout, read-only reporting
must validate stored schema, IDs, locator syntax, capability availability, and
cross-representation compatibility without treating filesystem presence as proof
of structural validity. Missing runtime capability remains unavailable, not zero.

Given an operation requiring live execution authority, its worktree and source
identity checks remain mandatory. Retired status must not bypass malformed-record
checks. No repair rewrites private cycle records to make a test pass or recreates
old source checkouts as a permanent dependency.

The lifecycle feature contract `historical-reporting-repair.md` preserves
fail-closed malformed-member handling and existing denominators, with explicit
historical intent restricted to completed-cycle enumeration and History
correlation. Current implementation's retired-record validation bypass is evidence
of a gap, not the desired compatibility contract.

## Delivery And Gates

Each behavioral cycle names its committed context PROFILE.md and exact writable
paths. Elevated risk is the default proposal for permission, privacy, data,
runtime, and operational changes. Kernel and Review/Integrate gates are required;
Deploy, Operate, and Maintain/Retire apply to managed-runtime changes. Release is
not applicable when no separately versioned artifact is published. Final
applicability is recorded per slice, not inferred from this prose.

Generate a fresh digest-bound receipt immediately before promotion and obtain
exact approval. Same-repository Build uses typed Initiative begin without a child
launcher. Deliver a feature branch and verify required CI, expected head, and
protected-base freshness before merging. The operator permits administrator merge
only after those checks pass. Failed evidence, changed head, or stale base blocks
merge; administrator privileges do not waive them. Verify the merge result before
dependent work begins.

## Validation And Completion

- Reconcile delivered History core to merged source; do not relaunch R5.
- Daily refresh remains host-explicit, default-off, 04:30 local, low priority,
  single flight, and at most sixty minutes. Prior valid snapshots retain explicit
  age; a missed refresh does not create synchronous model-visible work.
- Keep unavailable evidence distinct from empty data, and privacy invalidation
  immediate. Failure cannot replace a valid snapshot with incomplete preparation.
- Use affected repository-selected tests, rendered configuration, process fixtures,
  and controlled live smokes. Keep configured full CI authoritative for integration.
- Compare autonomous timing only with complete comparable cohorts; no speed claim
  follows merely from lower query latency or a green draft PR.
- Evidence reuse preserves separate gate decisions and exact commit, paths,
  command, authority, toolchain, and environment identity.

## Visual Evidence

| Concern | Decision | Canonical source and review question |
|---|---|---|
| Boundary | not_applicable: existing context map and scope prose are sufficient | Scope And Authority; who owns each change? |
| Interaction | not_applicable: ordered sequence table is clearer than a duplicate graph | Sequence And Readiness; what proceeds next? |
| State | not_applicable: existing Initiative states remain unchanged | Manifest; what is captured versus delivered? |
| Data/trust | not_applicable: repair and privacy invariants are explicit in prose | Reporting Repair Boundary; what must remain validated? |
| Schema | not_applicable: no public result schema is defined by this coordination artifact | Per-slice contracts remain authoritative |
| Dependency/deployment | not_applicable: manifest edges and delivery preconditions are canonical | Delivery And Gates; when may a dependency proceed? |
| Quantitative | not_applicable: cycle count is a planning count, not a measured performance chart | Scope And Authority; what is included? |

Owner: Discovery coordinator. Revisit this plan when scope, dependency, readiness,
delivery authority, or the operator's serial-execution constraint changes.
