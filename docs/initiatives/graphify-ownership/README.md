# Graphify ownership

Status: source specification ready; implementation, qualification and publication
checks pending. Coordinator: distribution maintainers. Method: DBSCTR V3 revision
3.29. Both source slices are elevated risk and deliver feature-branch draft pull
requests into their configured `main`; neither authorizes live activation.

## Approved context map

| Existing context | Home repository | Owned boundary |
|---|---|---|
| `dotfiles_ai_distribution` | `Saltiola7/dotfiles-ai` | Global native Graphify CLI/dependencies, matching packaged OpenCode skill and update runbook |
| `host_tool_maintenance` | `Saltiola7/dotfiles` | Remove duplicate global package/installer declarations and point to the distribution owner |

The operator approved this complete map. Reuse the distribution
[Engineering Profile](../../specs/dotfiles_ai_distribution/PROFILE.md) and
[Product Intent](../../specs/dotfiles_ai_distribution/PRODUCT.md), especially
installation, ownership-transfer and maintenance outcomes. The host repository's
committed `docs/specs/host_tool_maintenance/PROFILE.md` remains its validation
authority; this coordinator does not copy or replace it. Disabled hash-pinned DKS
Graphify 0.9.48 is an unchanged adjacent runtime, not the global CLI owner.

## Material coverage

`MANIFEST.json` owns stable statement IDs, kinds, dispositions and exact artifact
coverage. No transcript or machine-specific inventory is publication authority.

| Statements | Contract / coverage |
|---|---|
| INT-001–INT-006 | Approved owners, one native installer, missing-only supported-platform bootstrap, retained healthy runtime, fail-before-write and isolated skill installation; global feature contract |
| INT-007–INT-009 | Exact 0.9.97 candidate/grammar recipe, isolated qualification and bounded adapter compatibility; global feature contract |
| INT-010–INT-011 | One update runbook and declaration-only host handoff; feature contract and `HOST-SOURCE.md` |
| INT-012–INT-015 | DKS/graphs/cycle preservation, credential-free fixtures, source-only delivery and non-goals; both source contracts |
| INT-016–INT-019 | Serial slice ownership, dependency/lock risks, gate applicability and complete Git authority; this Initiative and source plans |
| INT-020 | Exact live activation/recovery plan remains open; `mac-activation` only |

## Ordered ownership transition

| Order / slice | Owner and guard | Allowed outcome / retained state |
|---|---|---|
| 1. `global-source` | Build, after primary verifies custody, publication and fresh launch authority | Implement the [global source contract](../../specs/dotfiles_ai_distribution/features/graphify-ownership.md), qualify exact candidate in disposable fixtures and deliver a reviewed source-only draft; preserve installed runtimes and real graphs |
| 2. Host readiness | Discovery; `global-source` must be **delivered**, not merely ready | Verify host profile and exact writable closure against its repository; promote `host-source` only after fresh authority checks |
| 3. `host-source` | Build only after promotion and exact launch approval | Deliver [declaration removal](HOST-SOURCE.md), ownership regression and README pointer; no uninstall or live deletion |
| 4. `mac-activation` readiness | Discovery; both source slices delivered | Resolve exact target, actual runtime/uv receipt, active-cycle commitments, preimages, checks and recovery; obtain separate exact activation approval |
| 5. Live changes | Separately approved activation owner | Only then consider native upgrade or ownership/removal operations; source readiness never implies activation |

**Text Equivalent:** First deliver and qualify the distribution source without
changing a live installation. Only delivered global source permits host-source
promotion. Host delivery removes declarations, not installed files. Both source
deliveries precede Discovery for an exact live plan and its separate approval.
Failures preserve prior runtimes, graphs, receipts and original evidence. Scope:
this two-repository ownership transition. Canonical sources: `MANIFEST.json` and
the two source contracts. Owner: coordinator; update when ownership, dependencies,
approval ordering or preservation changes.

`global-source` is Build-owned and specification-ready, not gate-passed or
launch-approved. `host-source` and `mac-activation` remain Discovery-owned and
discovering. Independent slice orchestration is not authorized; the primary
serializes handoffs and shared artifacts. Material compatibility findings return
`readiness_reopened` rather than silently changing normative contracts.

## Verification and handoff

This manifest's slices track this work; the current source has retired canonical
backlog tables. Do not recreate those tables or make PM tickets lifecycle authority.

The source applicability proposals are [SOURCE.plan.json](SOURCE.plan.json) and
[HOST.plan.json](HOST.plan.json). All kernel, Review/Integrate and Maintain/Retire
gates are required; every source Gate Result is pending. Release, Deploy and
Operate are not applicable for the profile-bound source-only reasons in those
plans. No Gate Exception is approved. Activation requires a separate applicability
plan including its actual deployment/operation obligations.

All manifest artifact paths resolve inside the coordinator repository. The
global-source artifact set includes the complete changed-document closure,
including the host handoff documents; the host profile path in `HOST.plan.json`
is deliberately resolved in the host repository, not listed as a nonexistent
coordinator artifact. The primary must review and source-control this closure,
run the existing public-tree publication authority with additions included,
validate the manifest, issue a fresh receipt/preflight and obtain exact launch
approval. Helpers own none of those operations or lifecycle state.

Open work is evidence/activation, not a new global-source behavior choice:
candidate/native-adapter qualification, dependent host promotion and the exact
live target/recovery plan. The committed host profile and root-level
`interactive_installers.sh` source have been verified. Preserve unmerged Discovery authority; use
the existing same-repository import route rather than publishing documentation
early to manufacture launch readiness.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: ordered ownership transition table |
| Interaction | required: ordered ownership transition table |
| State | required: slice guards and transitions in that table |
| Data/trust | required: retained-state and approval boundaries in that table |
| Schema | not_applicable: existing schema-1 Initiative shape; no new runtime schema |
| Dependency/deployment | required: delivered dependencies and separate activation in that table |
| Quantitative | not_applicable: no measured performance or fleet-health claim |
