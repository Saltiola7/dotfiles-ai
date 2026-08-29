# DBSCTR Delivery Lifecycle

This Initiative makes successful DBSCTR delivery converge back to a clean base
checkout without requiring operators to reason about stale feature branches and
worktrees. Automatic merge remains disabled unless machine-local Chezmoi policy
enables it.

The coordinator repository is `Saltiola7/dotfiles-ai`. The canonical machine
ledger is [`MANIFEST.json`](MANIFEST.json).

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
