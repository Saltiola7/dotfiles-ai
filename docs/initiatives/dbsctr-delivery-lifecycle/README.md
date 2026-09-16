# DBSCTR Delivery Lifecycle

This Initiative makes successful DBSCTR delivery converge back to a clean base
checkout without requiring operators to reason about stale feature branches and
worktrees. Automatic merge remains disabled unless machine-local Chezmoi policy
enables it.

The coordinator repository is `Saltiola7/dotfiles-ai`. The canonical machine
ledger is [`MANIFEST.json`](MANIFEST.json).

## Canonical Continuation Discovery

The operator also approved same-repository canonical-session continuation across
the existing lifecycle, OpenCode and distribution contexts. Its decisions,
source evidence, proposed contracts, acceptance and reopened readiness are in
[`CANONICAL-CONTINUATION.md`](CANONICAL-CONTINUATION.md). This is not delivered
behavior or an implementation approval. The continuation slices do not depend on
automatic merge. Native session identity remains unchanged; execution-target
selection is separate from conversation home.

The prior cycle-session retirement journey below remains the automatic-delivery
scope. Reconcile `base-session-handoff` before promoting it so that it does not
require replacing conversations already rooted in a canonical checkout.

### Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: continuation authority is represented in the linked Discovery contract, not duplicated here |
| Interaction | not_applicable: handover ordering is canonical in the linked Discovery contract |
| State | not_applicable: the manifest and linked transition table own readiness and runtime states |
| Data/trust | not_applicable: the linked contract owns private evidence and native-session boundaries |
| Schema | not_applicable: this index defines no storage schema |
| Dependency/deployment | required: delivery dependency tables below and in the linked Discovery contract |
| Quantitative | not_applicable: no measured comparison is claimed |

The Initiative owner updates these references when scope, ownership or dependency
changes. **Text Equivalent:** Automatic merge, its configuration and legacy
base-session handoff remain sequential. Canonical continuation follows a separate
core-to-OpenCode-to-rollout dependency chain, with no automatic-merge prerequisite.

## Success

- An enabled cycle creates a ready pull request and binds every merge action to
  its exact head commit.
- Normal repositories use GitHub auto-merge and retain branch protection.
- Administrator merge runs only for an exact configured repository after all
  required checks report success.
- A verified merge fast-forwards a compatible clean base checkout, then removes
  only the clean DBSCTR-owned cycle worktree and branch.
- Dirty, changed, diverged, unmerged, failed, or ambiguous state remains
  untouched and reports a bounded blocker.
- Control returns to a stable base-checkout session after the cycle session
  exits; session identity is not silently rebound to another repository path.

## Context Map

| Context | Responsibility | Dependency |
|---|---|---|
| `dbsctr_v3_lifecycle` | Merge policy, exact-head verification, post-merge synchronization, and safe cleanup | None |
| `dotfiles_ai_distribution` | Chezmoi policy rendering and unattended maintenance invocation | Lifecycle delivery contract |
| `opencode_control_plane` | Stable base-session handoff and cycle-session retirement | Lifecycle and distribution runtime |

The user approved this complete context map and automatic-after-CI policy on
2026-08-29. Administrator merge is restricted to an exact repository allowlist.

## Delivery Slices

| Slice | Execution owner | Outcome | Depends on |
|---|---|---|---|
| `verified-merge-core` | `build` | Disabled-by-default exact-head merge and post-merge cleanup primitives | None |
| `chezmoi-delivery-policy` | `build` | Machine-local opt-in and exact administrator repository allowlist | `verified-merge-core` |
| `base-session-handoff` | `build` | Return control to the stable base checkout after verified cleanup | `chezmoi-delivery-policy` |
| `canonical-continuation-core` | `build` | Delivered isolated core; live enrollment remains off | None |
| `canonical-continuation-opencode` | `build` | Delivered adapter and native same-conversation qualification | `canonical-continuation-core` |
| `canonical-continuation-rollout` | `build` | Ready for targeted host qualification, then configured guests | `canonical-continuation-opencode` |

## Safety Boundary

`--admin` is not a global fallback. It is valid only for an exact configured
repository after GitHub reports every required check successful. Missing policy,
authentication, checks, merge identity, checkout identity, or ancestry fails
closed. Automatic delivery never force-pushes, resolves conflicts, resets a
checkout, removes dirty work, or bypasses failed or pending checks.

## Non-Goals

- No universal administrator bypass.
- No squash or rebase merge support in the first delivery contract.
- No mutation of repositories that do not opt in.
- No attempt to move one OpenCode session identity between worktree paths.
