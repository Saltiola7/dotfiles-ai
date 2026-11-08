# Remote Default Worktree Activation (RRW-007E)

## Authority and behavior

INT-074, slice `rrw-007e-worktree-activation`, follows delivered RRW-007D
(F03 `a89e8ecd`, F04/F05 `44b33a66`, F01 `0932e869`). The owner approved the
default location in advance. This critical-risk successor replaces manual initial
activation only for explicit remote apply at the qualified setup default.
Fork A retains pins, preview, rollout, live apply and VM/worktree/pane operations.

- Remote apply runs `workflow-policy initialize-default-home` after installation.
  No new flag or manual step is needed for the fresh qualified default.
- Initial creation requires Linux, configured root exactly
  `HOME/.local/state/worktrees`, no root override outside it, qualified safe
  ancestry, matching home/root device and native findmnt UUID/mountpoint identity.
  A same-spelling path on another mount refuses. Existing cache rules remain.
- Bind the existing snapshot: policy digest, Worktrunk version and root/cache
  identities. Preserve the existing source-commit binding within policy digest;
  even a source revision change can require reviewed reactivation.
- Never replace any existing entry, including a dangling symlink. Matching
  private activation stays byte/inode identical. Malformed, unsafe or stale
  activation fails visibly without repair, chmod, unlink or automatic refresh.
- A private single-link advisory lock serializes cooperating applies with bounded
  acquisition. Write/fsync complete JSON to a same-directory private temporary,
  hard-link publish without replacement, unlink temporary, fsync directory.
  Final activation is user-owned, regular, mode 0600, single-link. Other applies
  wait outside the transient two-link window. Locking is not a security boundary
  against an owner modifying files or disabling their own guard.
- Changed policy/version/mount still refuses new allocation pending review.
  Existing native membership stays reachable. `--yes` is not activation.
- Preview/render/snapshot remain read-only. The apply initializer neither creates
  a checkout nor hydrates, copies or removes work. Activation/lock are runtime
  state, never chezmoi-managed files. Non-remote profiles exclude the apply hook.
- Absent activation at nondefault roots still requires separate review.
  Rollback retains activation and validates it, rather than silently refreshing.
  Retirement and deliberate reactivation require separate owner authority.

## Validation and maintenance

Offline coverage: creation, permissions/link count, concurrent applies, matching
reapply, existing symlink/hardlink/malformed/stale/public file refusal, changed
root/mount/version/policy, unavailable identity, disabled hook and read-only
snapshot. Check affected helper and tests with configured ty.

Disposable UBI uses native findmnt/Worktrunk: default foundation apply initializes
activation; remote-branch switch succeeds without a manual activation write;
native snapshot matches; reapply retains bytes. Fixture empty-commit upgrades and
rollbacks explicitly review source-identity-only snapshot changes; production
apply never refreshes them. Keep foundation and F01 boot gates green separately.
Actual execution remains in the cycle; no live RHEL acceptance is claimed.
Maintain helper, Worktrunk compatibility and findmnt semantics together. Failed
identity never publishes; failed publication never overwrites. Retain crash/stale
evidence and existing checkouts. Bootstrap bytes are unchanged.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary | required: transition table; who creates versus refreshes? |
| Interaction | required: transition table; what precedes allocation? |
| State | required: transition table; absent, valid and stale behavior? |
| Data/trust | required: transition table; when is identity bound? |
| Schema | not_applicable: existing snapshot format |
| Dependency/deployment | required: transition table; what qualifies the root? |
| Quantitative | not_applicable: no numerical claim |

| State/action | Owner | Result |
|---|---|---|
| Explicit remote apply, absent activation, exact home-backed default | Initializer | Publish native snapshot once at 0600 |
| Matching existing activation + apply | Validator | Preserve file |
| Stale/unsafe state or unqualified initial root | Validator | Refuse; retain evidence pending review |
| Preview/render/snapshot | Read-only helper | No activation, root or checkout creation |
| Matching activation + native switch | Worktrunk | Allocate in existing namespace |

**Text Equivalent:** Only explicit remote apply initializes missing activation
for the approved default home-backed root. Matching state stays unchanged;
stale/unsafe state refuses pending review. Preview and snapshot never write;
Worktrunk alone allocates. Canonical sources: helper, apply hook and activation
tests. Owner: distribution maintainer. Update on identity or ownership changes.
