# Worktrunk Upgrade

Status: ready for build (`workstation-upgrade`). `remote-foundation-pin` is
blocked: it needs a rollout through the cross-repository RHEL remote-workspace
Initiative. The normative contract is
[`features/worktrunk-upgrade.md`](../../specs/dotfiles_ai_distribution/features/worktrunk-upgrade.md);
the material-statement ledger is [`MANIFEST.json`](MANIFEST.json).

## Why now

The Linux workstation runs Worktrunk 0.80.0 (released 2026-09-27). The latest
stable release is v0.83.0 (2026-11-21). CI already exercises a different
version, 0.81.0, so the suite does not test the version the workstation uses.

The shipped workstation configuration also cannot allocate worktrees. With
`linux_workstation.enabled` set and `remote_user_environment.enabled` unset,
the Worktrunk configuration renders, the worktree policy document does not,
and the activation script exits without acting. The owner's workstation works
today only because its policy document and activation were created by hand.

## Statements

| ID | Kind | Summary |
|---|---|---|
| INT-001 | decision | v0.83.0 is the target for the Linux workstation and CI (owner decision 2026-11-24); the remote-user foundation keeps v0.80.0 for now |
| INT-002 | requirement | The workstation pins move together: installer version and both checksums, two version guards, CI axis, README |
| INT-003 | requirement | Both architecture pins are upstream's published v0.83.0 checksums |
| INT-004 | decision | The guards accept exactly v0.83.0, v0.81.0 and v0.80.0 |
| INT-005 | requirement | The upgrade is an owner-run procedure with a rollback set, because the installer refuses to replace another version |
| INT-006 | requirement | One re-activation after the upgrade; existing worktrees stay reachable |
| INT-007 | constraint | Upgrade in a quiet window, re-activate at once |
| INT-008 | requirement | A Linux workstation gets the worktree policy document and the default-home activation without the remote-user flag |
| INT-009 | requirement | The default-home rule is unchanged |
| INT-010 | requirement | Workstation example configurations declare the worktree root |
| INT-011 | constraint | The shared remote workspace is unchanged |
| INT-012 | risk | Worktrunk 0.81.0 and later compute a custom destination after the pre-switch hook |
| INT-013 | risk | The upgrade window refuses new worktrees |
| INT-014 | decision | No step for the `worktrunk-markers` plugin: this source installs no Worktrunk agent plugin |
| INT-015 | non-goal | No macOS qualification, no second CI axis, no layout or naming change |
| INT-016 | idea | Deferred: an installer rule that replaces the previous qualified pin itself |
| INT-017 | idea | Deferred: report a half-configured worktree policy loudly |
| INT-018 | requirement | Blocked: the remote-user foundation pin follows only through the cross-repository Initiative |
| INT-019 | requirement | The lifecycle context's record of the matrix is updated in the same change |
| INT-020 | risk | The Mac runs 0.81.0 with a live activation and is not tested in CI |
| INT-021 | requirement | Explicit fresh workstation setup provisions the two missing private default directories; custom roots stay owner-managed |

## Slices

| Slice | Purpose | Depends on | State |
|---|---|---|---|
| `workstation-upgrade` | Pins, guards, CI axis and README; the owner-run upgrade procedure and one re-activation; worktree policy reachable for a Linux workstation; example configurations | none | ready |
| `remote-foundation-pin` | Move the remote-user foundation to v0.83.0 together with the workspace's activation | `workstation-upgrade` and a rollout through the cross-repository Initiative | blocked |

## Validation strategy

1. The full suite is green on the exact head in one attempt with the CI
   Worktrunk axis at v0.83.0.
2. The owner-run upgrade on the workstation: v0.83.0 is installed and
   asserted; the activation binds `wt v0.83.0`; a new worktree lands in the
   policy root with the expected layout; the pre-switch check passes; removal
   still runs the kernel's removal check.
3. Gating, on a disposable home with the shipped workstation configuration:
   an explicit apply renders the policy document and creates the activation.
   A custom root leaves activation alone and the apply succeeds. The default
   on an unexpected filesystem still refuses.
4. Rollback: verify and retain the binary, policy document and activation
   before the switch. Restore them and verify allocation on failure.

## Engineering Profile overrides

Risk: **elevated** (installer ownership, activation identity, the CI matrix).
Delivery intent: **merge**, then an owner-run deployment on the workstation.
Kernel gates, Review/Integrate, Deploy, Operate and Maintain/Retire are
required; Release is not applicable. Base profiles under
`docs/specs/*/PROFILE.md` are otherwise unchanged.

## Visual Evidence

The Visual Evidence Plan for this Initiative is in its
[normative contract](../../specs/dotfiles_ai_distribution/features/worktrunk-upgrade.md#visual-evidence):
a required Interaction view (the upgrade sequence), a required State view
(activation states) and a required deployment view (which host pins which
version); every other concern is not applicable there with its reason.
