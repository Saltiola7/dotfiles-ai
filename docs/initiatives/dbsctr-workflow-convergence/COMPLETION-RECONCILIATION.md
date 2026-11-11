# Completion reconciliation — approved Discovery extension

## Intent and decisions

Repair successful-cycle dead ends and prevent recurrence with equal priority.
Discovery defines ready/done; Build satisfies the effective contract across any
required PRs and approved amendments. Automatically reconcile uniquely provable
bookkeeping and retain unaffected evidence. Logical completion never requires
physical cleanup. Investigate adjacent defects and assign every finding a bounded
disposition rather than quietly extending implementation scope.

The operator approved the following existing context map and Initiative home:

| Context / home repository | Ownership |
|---|---|
| dbsctr_v3_lifecycle / dotfiles-ai | Authority, DAG provenance, affected evidence, preflight and successful completion |
| opencode_control_plane / dotfiles-ai | Truthful primary guidance, classified diagnostics and supported recovery journey |
| dotfiles_ai_distribution / dotfiles-ai | Coherent managed activation and one privately nominated consumer recovery |

Public source contains generic contracts and synthetic scenarios only. Private
consumer identities, transcript details, credentials and runtime results stay
with their existing private owner. No PM ticket or new telemetry store is created.

## Normative contracts and precedence

- [Lifecycle reconciliation](../../specs/dbsctr_v3_lifecycle/features/workflow-completion-reconciliation.md)
- [Primary journey](../../specs/opencode_control_plane/features/workflow-completion-journey.md)
- [Managed rollout](../../specs/dotfiles_ai_distribution/features/workflow-completion-rollout.md)

These select a new qualified route, not retroactive reinterpretation of old
receipts. They supersede blanket invalidation and mutual exclusion only for this
route, retaining existing failure invalidation, native proof, privacy and
destructive-action controls. Original slices keep their recorded delivery states.
Captured ordinary Git reachability is reconciled as described in GIT-REACHABILITY.md.

## Definition of ready

- All requirements mapped to the three contracts and manifest slices.
- Stable evidence/provenance/compatibility interfaces and concrete acceptance cases.
- Existing source and publication authorities identified; passing exact artifact
  checks before publication or receipt.
- Explicit source-only versus rollout plans; no unresolved material design question.
- Fresh Build receipt/preflight and exact approval still required for each launch.

## Definition of done

Core and journey source are merged with required gates and regression cases;
compatible installed tooling is independently qualified; the nominated consumer
completes through supported public interfaces with its actual effective done
contract satisfied. Historical approvals, failures and evidence remain readable.
No workaround retires successful work, rewrites history or removes a checkout.
Source-only slices are done at their own approved delivery target; Initiative
outcome is not done until rollout and consumer qualification pass.

## Delivery slices / Build handoff

| Slice | Owner | Dependency | Acceptance / applicability |
|---|---|---|---|
| completion-reconciliation-core | lifecycle | delivered safety-inventory | Multi-PR amended-cycle public-CLI recovery, scoped evidence and staged deletion; CORE-SOURCE plan |
| completion-reconciliation-journey | control plane | core delivered | Primary reports proven state and actionable gaps; CONTROL-PLANE-SOURCE plan |
| completion-reconciliation-rollout | distribution | core and journey delivered | Compatible install and one truthful consumer recovery, no cleanup; COMPLETION-ROLLOUT plan |

Build source write closures:
- Core: existing lifecycle CLI, shared Discovery/DBSCTR references, lifecycle
  fixture/tests and lifecycle-owned docs. Reuse existing private custody, evidence
  and delivery proof machinery. No consumer code edits.
- Journey: existing OpenCode guidance/typed consumer only where required by the
  report contract, instruction tests and control-plane docs. No new adapter service.
- Rollout: existing distribution rendering/installation tests and owned docs;
  exact live managed targets selected privately at launch. No broad host apply.

The primary serializes shared CLI/guidance writers. No parallel Build cycles.
Recommended implementation primary: Build-GPT on the existing approved provider
route. Independent critical-risk review remains required. Discovery does not start
cycles or implement the repair. Dependent slices remain captured until delivered
predecessors permit fresh promotion; specification completeness is separate.

## RCA evidence and risk

See [source-backed RCA](COMPLETION-RCA.md). The main risk is laundering unknown
changes or stale execution evidence into success. DAG classification, immutable
preimages, independent native proof, conservative unknown-scope handling and final
acceptance prevent that. Another risk is replacing an old strict dead end with an
unbounded reconciliation search; bounded results must explain missing capability.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: approved context map above |
| Interaction | not_applicable: canonical protocol is in lifecycle contract |
| State | not_applicable: canonical transitions are in lifecycle contract |
| Data/trust | not_applicable: lifecycle and rollout contracts own private transfer rules |
| Schema | not_applicable: no new schema in this index |
| Dependency/deployment | required: delivery table above |
| Quantitative | not_applicable: no performance claim |

**Text Equivalent:** Lifecycle core precedes the native primary journey; both
precede managed rollout and private consumer recovery. Discovery authority remains
separate from Build launch, installed capability and successful delivery. Owner:
Initiative primary; update with scope, dependencies or acceptance changes.
