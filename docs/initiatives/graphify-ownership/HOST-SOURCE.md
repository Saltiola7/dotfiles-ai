# Host Graphify declaration handoff

Home: `Saltiola7/dotfiles`, existing `host_tool_maintenance` context. Elevated
risk; source-only feature branch and draft PR into configured `main`. Status:
Discovery-owned, discovering; depends on **delivered** `global-source` in the
[Initiative](README.md). No implementation or live removal is recorded here.

## Authority and bounded scope

This coordinator-owned contract is normative for the cross-repository handoff.
The host repository's committed `docs/specs/host_tool_maintenance/PROFILE.md`
remains its validation authority; [HOST.plan.json](HOST.plan.json) is applied in
that repository. Its committed profile and root-level `interactive_installers.sh`
have been verified; recheck their freshness and native Git custody before promotion.
Reuse the existing context; do not create another profile or duplicate the
distribution's [global contract](../../specs/dotfiles_ai_distribution/features/graphify-ownership.md).

After the dependency is delivered, the host source must:

1. Remove the `graphifyy` package declaration from `Brewfile`.
2. Delete source `run_onchange_install-graphify.sh.tmpl` without replacing it
   with another installer or retirement hook.
3. Remove only the obsolete Graphify installer comment in the existing root-level
   `interactive_installers.sh` source.
4. Add a focused `tests/test_ai_config_ownership.py` regression, a short root
   README pointer to the distribution's `docs/UPDATES.md`, and host context
   completion evidence in its existing README/CHANGELOG as applicable. Do not
   recreate retired backlog tables or require PM tickets.

Those files are the entire implementation closure. The README links the
distribution-owned runbook; it does not duplicate its recipe or recovery steps.
Do not remove unrelated declarations, rewrite shell selection or change Python,
uv, DKS, provider settings or dependency versions.

## Behavior and preservation

| Order | Given / when | Required owner action and retained state |
|---|---|---|
| 1 | Global source not delivered, host profile/custody unverified, or exact source path unresolved | Discovery retains `host-source`; no Build receipt or mutation |
| 2 | Dependency delivered and host source is reviewed | Host removes only the package/installer/comment declarations; distribution is the documented global owner |
| 3 | Updated source is rendered or inspected in disposable fixtures | No host Graphify installer or global package declaration remains; unrelated managed targets retain their prior contract |
| 4 | Existing installation, skill, graph/cache, DKS runtime or cycle receipt exists | Preserve it byte-for-byte; source deletion is not uninstall or live removal |
| 5 | Live cleanup or environment migration is requested | Return to separate activation Discovery/approval; source delivery grants no deletion authority |

**Text Equivalent:** Undelivered dependency or unresolved host authority blocks
Build. Once promoted, remove only competing source declarations and publish an
owner pointer. Fixture inventory proves non-reintroduction, not live migration.
Installed tools, skills, graphs, DKS and cycle evidence remain untouched; any
cleanup requires a separately approved exact plan. Scope and canonical source:
this host handoff contract. Owner: host maintainer with coordinator review; update
when declaration paths, ownership, dependencies or preservation change.

No uninstall command, `.chezmoiremove` entry, live deletion, environment migration,
service operation or arbitrary cleanup belongs to this slice. Preserve disabled
hash-pinned DKS 0.9.48, existing graphs and active-cycle exact-version commitments.
Material findings return `readiness_reopened`; Build must not rewrite this
contract, lifecycle policy or schema to make an implementation fit.

## Validation and source gates

Establish the non-reintroduction regression in
`tests/test_ai_config_ownership.py`; inspect rendered managed targets and script
plans without executing a full apply or package bundle. Run that affected suite,
the host profile's applicable source checks, Brewfile/template syntax checks and
README/runbook-link verification. Compare unrelated target ownership against the
fixture baseline. Checks must not uninstall software, access credentials, call
providers or run tasks in real projects.

| Gates | Applicability | Gate Result |
|---|---|---|
| Domain, Behavior, Spec, Contract, Test-driven implementation, Refactor | required | pending |
| Review/Integrate; Maintain/Retire | required | pending |
| Release | not_applicable: no independent package/release | not run |
| Deploy; Operate | not_applicable: declaration-only draft source, no live change | not run |

No exceptions approved. Retain failed evidence; recovery is a reviewed source
revert without replaying the obsolete installer. Primary owns publication checks,
Git delivery, dependency promotion, fresh receipt/preflight and exact launch
approval. Remaining host readiness inputs: delivered dependency and fresh checks
of the verified host profile and `interactive_installers.sh` path; no competing
owner choice is open.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: ordered behavior/preservation table |
| Interaction | required: dependency, promotion and removal ordering in that table |
| State | required: blocked/promotion/source-only guards in that table |
| Data/trust | required: retained live-state boundary in that table |
| Schema | not_applicable: no schema change |
| Dependency/deployment | required: delivered global dependency and separate activation in that table |
| Quantitative | not_applicable: no comparative measurements |
