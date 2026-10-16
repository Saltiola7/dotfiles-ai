# Build handoff — workflow convergence

**Discovery complete; source delivery in progress.** This file is a resumption
index, not a launch approval. Re-read `MANIFEST.json`, `DECISIONS.md` and referenced
contracts from Git after compaction. Validate them with `initiative-check`; never
use a conversation summary, old digest or runtime identity as readiness authority.

## Verified source delivery — 2026-10-16

`safety-inventory` delivered through [PR #214](https://github.com/Saltiola7/dotfiles-ai/pull/214):
Gate Commit `12ae5da073690c597293907fe9d85ca83c0b548c`, merge
`2c638e10e76800a0cf151cf7a7933dccb0a0bcfc` into `main` from base
`493fac03ea0b7959d38dc375f6e246995a41bfe1`. Native ancestry confirms the exact
head is a merge parent; Python 3.12/3.13/3.14 test jobs and remote-user smoke all
passed before the explicitly approved merge. No deployment, upload or removal.
The manifest now records this source prerequisite as delivered and promotes
`storage-config` to ready. Other source slices remain unimplemented; historical
readiness counts and first-launch instructions below describe the Discovery
checkpoint, not current execution state. No normative scope/dependency changed.

`prompt-authority` is also dependency-satisfied by the same verified inventory
delivery. Promote it to `ready` for serial primary work while storage-config CI
is pending; this does not mark storage delivered or unlock its dependents. The
manifest DAG, not the display row order, permits this independent source slice.
No implementation or launch approval is implied by the readiness promotion.

`storage-config` subsequently delivered through
[PR #215](https://github.com/Saltiola7/dotfiles-ai/pull/215), exact final head
`b14ead55f9ce61b0bcb538d9aa56b15b00f754c8`, merged into `main` as
`8b3d46fc6a9510d9ea75f79dcd9b08613aa82e8e` from base
`2c638e10e76800a0cf151cf7a7933dccb0a0bcfc`. Native Git verifies both merge parents
and head ancestry. All three Python jobs and remote-user smoke passed. The source
delivery includes the approved CI-only Worktrunk pin correction and manual update
runbook; no host activation, upload, migration or cleanup occurred. Mark storage
delivered and its dependency-satisfied source consumers ready. Prompt source is
published in PR #216 but not verified integrated here; retain its ready state.
These delivery facts supersede earlier checkpoint descriptions above without
changing requirements, risk, acceptance, source ownership or dependency edges.

## Invariants

- Public generic contracts only. Private repository identity, content, branches,
  paths, configuration, inventories and results never enter this public project.
- Existing active/dirty/unmerged/unknown work stays retained. Do not revive old
  cycles, move active checkouts, bulk-commit unknown data, stop processes or run GC.
- Worktrunk owns native allocation/removal. New work is code-only; independent
  environments/data copies are not a phase boundary. Shared DVC cache is immutable,
  mutable state independent, hydration targeted/reflink-only with no copy fallback.
- No arbitrary 24-hour delay once preservation is proven. Unknown evidence still
  blocks deletion. Clean DVC cloud status does not prove directory-member closure;
  unqualified directory cases retain data/cache and report the capability limit.
- Optional automation is exact-repository opt-in. Administrator merge is a
  configured mode, not a CI waiver. Only trusted affected classification may omit
  unrelated pending checks; genuine failures need explicit scoped exceptions.
- One intent checkpoint may cover an ordered batch of up to 32 PRs. Resolve
  mechanical conflicts and rerun checks; material semantics/scope changes reopen
  Discovery and an intent interview. No new root directories without agreement.
- Configuration provides compatible rollback and feature identity; no flag
  service. Feedback stays local unless exact destination/scope consent enables
  bounded publication. Native Incident mutation remains unavailable, not forged.
- Canonical Caveman/Ponytail are referenced once. Provider deltas stay minimal;
  RTK/trim1 remain default-off research/evaluation, with no install, proxy, paid
  model request, opaque-state transformation or default stacking.

## Source delivery order and ownership

All ten source specifications are ready. The CLI marks only dependency-satisfied
slices `ready`; the rest remain `captured` **solely awaiting verified prerequisite
delivery**, not an unfinished interview. All source execution owners are Build.
Record real predecessor delivery before promoting dependents and obtaining fresh
receipts. Do not label implementation complete merely to unlock a dependency.

| Order / slice | Risk / plan | Source write ownership (plus its context completion evidence) |
|---|---|---|
| 1 `safety-inventory` | elevated / CORE-SOURCE | `dot_local/bin/executable_dbsctrctl`; `tests/test_native_workspace_records.py`, `tests/test_workspace_remove_check.py`, `tests/test_native_cli_projection.py`, `tests/test_dbsctrctl.py`; metadata inventory only, no cleanup/upload activation |
| 2 `storage-config` | critical / DISTRIBUTION-SOURCE | `.chezmoidata.toml`, `config.example.toml`, `.chezmoiignore`; replace `private_dot_config/worktrunk/config.toml` coherently with `.toml.tmpl`; new `private_dot_config/dotfiles-ai/workflow-policy.json.tmpl`; `.chezmoitemplates/opencode.json.tmpl`; `tests/test_portable_distribution.py`, `tests/test_worktrunk_native_policy.py`, `tests/test_remote_user_environment.py` |
| 3 `dvc-preservation` | critical / CORE-SOURCE | `dot_local/bin/executable_dbsctrctl`, `dot_local/bin/executable_worktree-dvc-setup`; `tests/test_worktree_dvc_setup.py`, `tests/test_native_dvc_removal.py`, `tests/test_workspace_remove_check.py`; targeted consent/evidence and explicit unsupported-directory retention, not a custom remote verifier |
| 4 `native-handoff` | critical / CONTROL-PLANE-SOURCE | `private_dot_config/opencode/AGENTS.md`, `dot_agents/skills/dbsctr/SKILL.md`, `dot_agents/skills/discovery/SKILL.md`; native lifecycle/permission/helper tests listed in the handoff contract; no custom identity or continuation plugin |
| 5 `merge-cleanup` | critical / CORE-SOURCE | `dot_local/bin/executable_dbsctrctl`, `dot_local/bin/executable_agent-worktree`, DBSCTR skill; `tests/test_agent_worktree.py`, `tests/test_workspace_remove_check.py`, `tests/test_native_dvc_removal.py`, `tests/test_native_workspace_records.py`, `tests/test_workspace_adoption.py`; parent-supervised native removal and distinct guarded branch outcome |
| 6 `integration-review` | critical / CORE-SOURCE | Shared CLI, DBSCTR/integrate/QA skills; new `dot_agents/skills/dbsctr-pr-review/SKILL.md`; existing lifecycle/integration tests named in its contract; no consumer CI refactor |
| 7 `ci-contracts` | critical / CORE-SOURCE | Same CLI/skill/test closure as integration-review; trusted dependency/check schemas, exact evidence, bounded watch/repair and exception tests; `.github/workflows/test.yml` remains a read-only configured authority |
| 8 `regression-telemetry` | critical / CORE-SOURCE | Shared CLI, review/performance-audit skills; `tests/test_dbsctrctl.py`, `tests/test_native_cli_projection.py`, `tests/test_dbsctr_lifecycle.py`, `tests/test_portable_distribution.py`; local bounded feedback/compatibility, native Incident unavailable |
| 9 `prompt-authority` | elevated / CONTROL-PLANE-SOURCE | Managed `AGENTS.md`, DBSCTR skill/provider references/performance-audit guidance; existing control-plane/lifecycle/helper/permission tests in its contract; no broad model/agent-route change |
| 10 `compression-evaluation` | elevated / CONTROL-PLANE-SOURCE | Existing control-plane tests hold the small public/synthetic fixture and report schema; guidance/performance-audit references only where necessary; no installed plugin/filter change |

The manifest owns dependency edges, not row order alone. Serialize overlapping
CLI/skill/test writers. Source implementation may record completion evidence in
its context README/CHANGELOG and delivery facts; it may not rewrite normative
scope, acceptance or dependency requirements. Material findings return
`readiness_reopened`. Expansion beyond the listed closure needs Discovery review
and the corresponding approval amendment, not opportunistic edits.

Plans are committed as `CORE-SOURCE.plan.json`, `DISTRIBUTION-SOURCE.plan.json`
and `CONTROL-PLANE-SOURCE.plan.json` beside this file. They bind the three existing
Engineering Profiles. All kernel gates, Review/Integrate and Maintain/Retire are
required. Release is not applicable to source consumption; Deploy/Operate are
not applicable to these source-only PRs. Those omissions do not waive later host
activation, data migration or live remediation gates. No Gate Exceptions exist.

## First Build launch after compaction

1. Re-read all authority and run `dbsctrctl initiative-check --manifest
   docs/initiatives/dbsctr-workflow-convergence/MANIFEST.json --json` in the
   authority checkout. Confirm `safety-inventory` is the next ready slice.
2. Preserve this committed Discovery checkout/ref. Current kernel registration
   requires clean task HEAD at its approved remote base; do not reset unmerged
   Discovery or weaken that constraint. Allocate **one** code-only Build checkout
   through native Worktrunk from freshly fetched `origin/main`, with a unique
   task cycle/branch and its intended upstream. Do not hydrate data or copy `.venv`.
3. Move this conversation with the native session tool only when selecting that
   Build checkout. Changing a shell working directory does not move the session.
4. Use the existing Initiative source/import route, pointing to this retained
   Discovery authority checkout and `CORE-SOURCE.plan.json`. The first receipt
   declares the full changed-document closure to avoid partial cross-context
   authority import. Those documents are read-only authority for the core builder,
   not permission to implement other contexts in its first cycle.
5. Generate a **fresh** `initiative-receipt --manifest ... --slice
   safety-inventory --json`; verify plan/repository identities and run exact
   `dbsctrctl begin ... --preflight` in the selected task checkout.
6. Present that preflight's scope, risk, destination and launch digest. Obtain
   explicit chat approval for that exact plan before registering with
   `--expected-launch-digest ... --approval agent-confirmed`. No registration,
   preflight success or approval is asserted by this handoff.
7. Start with failing bounded metadata-inventory tests. Keep every deletion,
   upload, merge, host apply and new automatic action disabled in this cycle.

The fixed source baseline is not an excuse to ignore newer upstream changes.
Fetch/reconcile authority before approval if defaults or contracts changed; retain
failed preflight evidence. No premature docs-only push is required just to obtain
an upstream. Once imported authority is merged, later slices use current primary
Git authority and recorded predecessor delivery, with fresh receipts each time.
The small authority checkout stays preserved until its own work/evidence is safely
integrated and eligible; do not create one new authority checkout per phase.

## Validation and activation boundaries

Reuse a compatible existing validation interpreter/environment read-only where
qualified; do not create or synchronize a `.venv` per phase by habit, and never
mutate an environment used by an active session. Verify imports/editable packages
resolve the **selected task source**, not an older primary checkout. A genuinely
different lock/runtime/dependency set may justify a separately approved environment
using repository-native tooling; report missing capability instead of silently
installing tools or adding an environment manager. CI's ephemeral environments
retain their own toolchain identity and are not host workspace copies.

Use affected repository-selected pytest, Python compilation, rendered chezmoi,
shell/configuration syntax, permission-negative tests and native disposable
fixtures. Do not install tools or run repository-wide QA by default. Publication
authority is the existing tracked-tree privacy test; include every new/imported
document in its inventory. Missing tools/evidence remain unavailable, never zero.
Review nontrivial diagrams in the eventual GitHub PR as part of integration.

The fixed failure oracles are in each contract: partial inventory is not empty;
missing `.dir` members do not pass; short-hash/path collisions refuse; replaced
mounts do not fall back; unknown artifacts/processes retain; revoked authority,
self-exempting CI maps and stale heads block; waivers stay failed evidence;
feedback overflow and unavailable attribution stay visible; filters lose no
required evidence or gate outcomes and never process real authority.

After the relevant source delivery, prepare a separate exact host-activation plan with Deploy,
Operate and Maintain/Retire required, all source prerequisites and current
machine-local policy snapshots. Storage/cleanup activation may follow its first
five prerequisites; it need not wait for optional telemetry/prompt/compression
work. Do not bundle unrelated feature activation. No guest/remote rollout, active relocation,
service restart, cache migration or disk-wide removal is implied. Optional
compression stays off even if source fixtures pass. Native Incident registration
is not part of activation. Initial legacy cleanup is a **fresh bounded inventory
and disposition plan**, requiring its own exact approval; retain everything
active, unmerged, unknown or unpreserved. No all-disk wildcard deletion or GC.

## Discovery validation checkpoint

Before this editorial receipt, the configured publication/instruction and native
Initiative-import/approval fixture set passed **89 tests**:

```text
pytest tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers
       tests/test_opencode_control_plane.py tests/test_dbsctr_lifecycle.py
       tests/test_initiative_local_launch.py tests/test_initiative_cli_approval.py -q
```

Primary structural checks verified exact **25-file** first-import closure, all
three source plans against committed Profiles and the CLI's gate vocabulary, and
local links across **21 Markdown documents**. `initiative-check` reports 52 ready
statements, three ready contexts and only `safety-inventory` launch-promotable.
A bounded read-only review found no material contract contradictions; primary
independently verified its unavailable shell checks. Final publication validation
is repeated after staging this receipt. No implementation or live gate is passed;
rendered GitHub diagram review remains an integration check in the eventual PR.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: source ownership table distinguishes context builders and primary approval |
| Interaction | required: ordered launch and activation steps above |
| State | required: readiness versus dependency wait versus runtime activation distinction above |
| Data/trust | required: invariants and publication/activation boundaries |
| Schema | not_applicable: reference canonical versioned context contracts and existing plan schema |
| Dependency/deployment | required: manifest edges and source/activation ordering above |
| Quantitative | not_applicable: no measured speed, storage or cost benefit |

**Text Equivalent:** Read committed authority after compaction, implement the
bounded inventory first, then promote only prerequisites verified delivered.
Each source slice has one owning primary and explicit source paths; overlapping
writers serialize. Fresh receipt, preflight and exact approval precede every
registration. Source PR success never activates cleanup or proves data durability.
Host activation and any legacy remediation are separate exact plans. Owner:
Discovery primary; update on scope, dependency, approval or validation changes.
