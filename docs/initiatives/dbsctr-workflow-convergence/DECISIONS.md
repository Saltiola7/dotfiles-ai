# Decisions and resolved contracts

**Discovery complete; specification ready, not implemented.** All 52 stable
INT statements and three contexts are `ready`. All ten slices are Build-owned
and specification-ready; only dependency-free `safety-inventory` is machine
`ready`. Nine are `captured` awaiting verified prerequisite delivery under the
current CLI, not unfinished Discovery. No dependency is delivered by assertion.

[MANIFEST.json](MANIFEST.json) owns IDs, coverage and the delivery DAG.
[BUILD-HANDOFF.md](BUILD-HANDOFF.md) names exact source write closures and the three
source plans. Q IDs below preserve decision traceability; there is no known
remaining user-intent conflict or material technical design decision. Capability
limits have explicit retain/block behavior; fixtures prove implementation later.

## Resolved decision and Build acceptance ledger

| ID / INT coverage | Frozen decision and evidence authority | Build acceptance / conservative limit |
|---|---|---|
| Q-01 / INT-005–INT-008, INT-020–INT-021 | [Storage](../../specs/dotfiles_ai_distribution/features/workflow-storage-policy.md): one TOML owner, defaults < global < exact-repository overrides; generated private `workflow-policy.json` and native Worktrunk `.toml.tmpl`. Select `ROOT/{{ repo }}-{{ repo_path \| hash }}/{{ branch \| sanitize }}`; DVC separately uses full SHA-256 of canonical common directory. Global/per-repository naming selects task/context/cycle (`dbsctr` default), Discovery/initiative (`discovery` default), optional integration/outcome. | Native short-hash, sanitize/case-fold or occupied collisions refuse; no custom digest allocator. Conflicting clones sharing a native project selector refuse rendering. Native macOS volume UUID/Linux findmnt UUID and mountpoint bind external roots; unsupported/replaced roots block without fallback. Exercise schema, rendering, naming, replacement and rollback fixtures. |
| Q-02 / INT-009–INT-010, INT-014 | Storage plus [preservation](../../specs/dbsctr_v3_lifecycle/features/workflow-preservation-retirement.md): shared immutable repository cache, independent local mutable state/locks, code-only bootstrap and explicit targeted closure on the same qualified filesystem. | Reflink-only; no copy/hardlink/symlink fallback, full pull, GC, blind cache migration or unique-output overwrite. Test independent edits and unsupported filesystems separately; retain existing caches/results. |
| Q-03 / INT-011–INT-012 | Preservation: strict version-1 declared-output manifest binds Git/DVC metadata, complete object scope, approved destination and trusted exact-repository standing upload consent. Unchanged approved declaration/targets/destination allows new object versions without repeated asks; scope/destination changes require approval. | DVC 3.67.1/dvc-data 3.18.2 cloud `{}` is not directory-member proof. First release retains unqualified directories/cache with `remote_directory_closure_unverified`; no DVC internals/custom backend verifier. Test present `.dir`/absent member with cold/warm caches, supported file/non-DVC cases separately; presence is not payload-integrity proof. |
| Q-04 / INT-012–INT-019 | Preservation: fresh ultimate-default/PR/head/ancestry plus all artifact dispositions, applicable independent data evidence, no consumers and exact removal authority replace the eligible-cycle 24-hour hold. `agent-worktree --remove ABSOLUTE_WORKTREE_PATH` holds parent cooperative reservation through fixed native `wt remove --foreground --no-delete-branch` and branch observation. | Hook locks do not span removal or grant identity. Fixture descriptor propagation through native hooks; unavailable propagation/process visibility blocks automatic removal. Known consumers block, never kill. Local branch deletion is separate exact-tip CAS under the reservation; remote default-off opt-in uses already-configured GitHub after-merge deletion only after final-default/data preservation. No repository-setting mutation/ref DELETE fallback; incompatible auto-delete blocks merge. |
| Q-05 / INT-018–INT-021 | [Native handoff](../../specs/opencode_control_plane/features/workflow-native-handoff.md): preserve work, identify unique clean primary, fresh fetch/ff-only, then native `session_move` for the current conversation without caller-supplied identity. Idle completed checkouts need no conversation. | Preserve history/attachments/compaction and partial-success evidence; missing route retains. CLI arguments/environment never authenticate actor identity. Current registration needs task HEAD at approved base: retain committed code-only Discovery authority and create one code-only Build checkout for exact import if needed, not phase/data/venv copies or premature docs publication. |
| Q-06 / INT-022–INT-023 | Preservation plus [integration/CI](../../specs/dbsctr_v3_lifecycle/features/workflow-integration-ci.md): record exact delivery target separately from fresh ultimate default; intermediate delivery retains refs/work and reports `completed_unmerged` for bounded delegated reconciliation. | Test final-default ancestry of all gate commits, changed target/default and unknown outcomes. No automatic abandonment or historical-cycle rewriting. Native branch outcomes remain separately authorized from worktree removal. |
| Q-07 / INT-024–INT-028 | Integration/CI: reusable `dbsctr-pr-review`, existing functionality/callers/shared-library authority first, minimum correct solution, appropriate modularity and no new root without agreement. Mechanical means uniquely intent-preserving; material ambiguity pauses RCA/intent interview. “95% intent” means agreed outcomes/non-goals/semantics/acceptance, not numeric confidence. | One checkpoint binds an ordered batch of 1–32 PRs from one repository to one target unless standing auto policy covers it. Revalidate resulting base and affected evidence after every merge; changed head/order/external base/material plan invalidates checkpoint scope. Test classifications and exact approval binding. |
| Q-08 / INT-034–INT-036, INT-038–INT-039 | Integration/CI: trusted-base-owned version-1 component/reverse-dependency/check mapping with producer/workflow identity; conservative union/broad checks or block for unknown paths/maps. Exact tested head/base/merge parents, policy/map/spec/command/toolchain/environment identities bind evidence. | Only success passes; explicitly trusted unrelated pending may remain with opt-in. Unknown/skipped/missing evidence blocks. Poll 30 seconds, watch at most 30 minutes, at most three mechanical repairs per persistent fingerprint. Test self-exemption, producer forgery, graph cycles, stale bases, cancellation and restart budgets. Consumers retain CI refactors; no universal runner/full-repository every-gate rule. |
| Q-09 / INT-029–INT-033, INT-037 | Integration/CI: default-off exact-repository delivery, ordinary mode default; operator-owned exact admin mode is standing consent for eligible native PR merges without repeat asks. Integrator role allows listed feature/integration refs only. Authentication remains native authority. | Genuine failure waiver always needs explicit user approval, exact identities/expiry and visible failed evidence; mandatory security/data-loss/auth checks never waive. Admin is not a check waiver or credential grant; unavailable native safeguards block. Test role/default denial, dual-policy refusal, drift/expiry and non-waivable protections. |
| Q-10 / INT-001–INT-004, INT-013–INT-017, INT-043, INT-048 | Preservation and [feedback](../../specs/dbsctr_v3_lifecycle/features/workflow-regression-feedback.md): metadata-first native inventory includes native/legacy validated cycles, explicit repository seeds and bounded partial coverage; private full report and path-free agent projection. Review/incident/backlog/telemetry audit is availability reconciliation, not PM ticket or raw-ledger access. | Inventory: 5 seconds/repository, 1 second/item, 100 items/page, 256 repositories/invocation; no full `du`/dataset traversal. Cursor invalidates on scope/source drift. Test bounds/privacy/unknown disposition and optional size failure. Initial all-repository inventory is report-only; later legacy remediation needs fresh bounded approval. |
| Q-11 / INT-040–INT-043, INT-047–INT-048 | Feedback: normalized existing typed feature switches, no second flag file; versioned source/config/feature snapshots and compatible rollback. Queue 256 × 16 KiB, aggregate 4 MiB, 30-day retention; redact before persistence/export. Exact repository `feedback` defaults local; standing destination/sanitized-scope consent enables bounded native GitHub flush, including ordinary opted-in cycle feedback. | Test atomic old/new queue, one-second lock bound, coalescing/drop/expiry, incompatible reader rollback and sentinels. Flush ≤30 seconds/three attempts, ambiguous create queries dedup marker before retry; no daemon/per-issue repeat consent inside unchanged scope. Native Incident remains typed unavailable, never fabricated. No causal/performance claim without comparable authorized evidence. |
| Q-12 / INT-044–INT-048 | [Guidance](../../specs/opencode_control_plane/features/workflow-agent-guidance.md): canonical installed Caveman and Ponytail referenced once through managed AGENTS; minimal current OpenAI/Anthropic reference deltas for GPT-6 Astra, GPT-6.1 Sol and Opus 5.5; preserve native permissions/provider affinity and compaction authority reread. | Test no duplicate full prompts, explicit missing-skill availability, denied routes and no global model/effort switch. Prompt source depends on safety inventory, not whole regression implementation; existing read-only availability types suffice. Source/public model facts are not installed-route or budget measurements. |
| Q-13 / INT-049–INT-052 | Guidance: default-off staged offline public/synthetic replay, baseline versus one available filter at a time, no mandatory factorial. Pin source/filter/rubric/fixture identity; preserve raw evidence and authority/opaque-state bypass. | Fixture 9–16 cases, ≤256 KiB; three paired replays/case when available. Require 100% expected-fact recall, unchanged gate outcomes and zero synthetic secret leaks; partial/unavailable prevents qualification. No installs, proxy/model/API requests, default stacking or byte-derived cost claims. Later activation requires separate installed-route/bypass evidence and approval. |

All six linked contracts are specification-ready. The source write closures and
implementation acceptance belong to the ten bounded slices in BUILD-HANDOFF;
this resolution table neither implements them nor reports fixtures passed.

## Evidence, precedence and delivery authority

- Public source baseline remains
  `493fac03ea0b7959d38dc375f6e246995a41bfe1`; primary verified upstream unchanged.
  [SOURCE-RECONCILIATION.md](SOURCE-RECONCILIATION.md) preserves source observations,
  not private host/adopter facts or runtime conclusions. Existing sibling layout,
  24-hour hold, unknown-ignored-data and process guards are observed source facts.
- Pinned Worktrunk `v0.80.0` commit
  `b49ca7eea9b03145791a5b94eccaf9c59412ed37` supplies native project/path selectors
  (`repo_path`, `owner`, `remote_repo`) and three-character base-36 hash, not full
  SHA. The selected native layout supersedes the draft full-SHA checkout idea;
  the separate DVC cache identity remains full SHA. Source support is not runtime
  rendering or race qualification.
- Conditional new-cycle precedence in reconciled automatic-delivery and three
  native-workspace specifications selects these contracts only for applicable new
  opted-in cycles. Existing active authority, old receipts, failed evidence,
  unfinished relocation and prior Initiative delivery states remain untouched.
  Context indexes and Product journeys 18–20 reflect this distinction.
- The manifest DAG is scheduling authority: storage precedes consumers of generated
  preservation/delivery/feedback policy; safety precedes prompt guidance; prompt
  precedes compression. Serialize shared source/test writers. Material Build
  findings return `readiness_reopened`, not unilateral normative changes.
- Current CLI lines 3603–3609 prohibit `ready` slices with undelivered predecessors.
  One machine-ready plus nine captured is therefore the correct representation of
  ten specification-ready source slices. No delivered dependency is invented.

## Plans, import and verification

First source scope is elevated, bounded metadata inventory only under
[CORE-SOURCE](CORE-SOURCE.plan.json). Storage/DVC/handoff/cleanup/integration/CI/
feedback are critical; guidance/evaluation are elevated, using the owning
[DISTRIBUTION-SOURCE](DISTRIBUTION-SOURCE.plan.json), CORE or
[CONTROL-PLANE-SOURCE](CONTROL-PLANE-SOURCE.plan.json) plan. Six kernel gates,
Review/Integrate and Maintain/Retire are required. Release/Deploy/Operate are
reasoned source-only not-applicable, not waived activation obligations.

The first slice artifacts enumerate exactly 25 changed/new Discovery documents;
include that whole closure in its receipt/import to avoid partial authority.
Parent Profiles retain existing automatic allowance. Later source receipts use
current main authority after first import merges, their own feature/plan/handoff
and genuine predecessor-delivery evidence. After compaction re-read Git authority;
Build alone prepares fresh receipt/preflight and obtains exact plan approval before
registration. This ledger asserts no registration, approved preflight or gate pass.

Primary verifies manifest/reference/DAG/import closure, committed Profiles/plans,
configured publication checks on every candidate document, link and visual parity.
Runtime/disposable fixtures are Build acceptance; unsupported cases retain/block
as specified. Later host activation and fresh legacy-remediation batch each need
their own plan/approval, not an implicit extra implementation slice. No private
inventory, RTK statistics, runtime benefit or cost measurement enters this ledger.

## Visual Evidence

Reuse [README Visual Evidence](README.md#visual-evidence), its Text Equivalents,
canonical sources, Discovery-primary ownership and update triggers; context
contracts own detailed schemas and failure tables.

| Concern | Decision |
|---|---|
| Boundary | required: referenced ownership flow and context map |
| Interaction | required: referenced preservation ordering and bootstrap boundary |
| State | required: referenced readiness/retention table; specification versus dependency versus runtime states |
| Data/trust | required: referenced public/private evidence flow and contract privacy boundaries |
| Schema | not_applicable: context schemas remain canonical, no duplicate persistence model |
| Dependency/deployment | required: referenced manifest slice table and Dependency Text Equivalent |
| Quantitative | not_applicable: fixed acceptance bounds are not measured results; no benefit chart |
