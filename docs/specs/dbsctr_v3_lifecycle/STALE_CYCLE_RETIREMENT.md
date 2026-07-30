# Stale Cycle Retirement

## Scope

Retire stale DBSCTR-created cycle worktrees without fabricating successful gates,
deleting cycle records, deleting branch refs, or touching dirty worktrees.

## Behavior

- `dbsctrctl cycle-retire --cycle-id ID --confirm ID --disposition KIND
  --reason TEXT` accepts only an exact confirmed active cycle with a clean,
  identity-matched DBSCTR-created worktree outside the caller's worktree.
- `empty` requires no Gate Commits and a worktree HEAD equal to the cycle baseline.
- `integrated` requires every recorded Gate Commit and the current worktree HEAD
  to be ancestors of the fetched protected base branch.
- `superseded` requires a bounded explicit reason. It preserves the cycle record,
  commit identities, and local branch ref for later inspection.
- Retirement records a crash-recoverable removal marker, removes only the linked
  worktree and its exact active pointer, then changes cycle state to `retired`.
- Dirty, missing, current, foreign, branch-changed, malformed, or mismatched cycles
  fail closed. Normal completed-cycle cleanup remains unchanged.

## Validation

Synthetic Git fixtures cover all three dispositions, exact confirmation, dirty
rejection, target ancestry, branch retention, record retention, and retry after
interrupted worktree removal.
