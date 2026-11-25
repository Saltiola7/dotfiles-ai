# macOS workstation retirement

Status: source delivered, four slices open. The Try Omarchy VM replaced the
mac-mini as the AI workstation, and this initiative made that replacement
permanent in source. The mini is no longer a place where dotfiles-ai is
developed, but it is not excluded from dotfiles-ai: the owner keeps applying
it there (see the decisions of 2026-11-24 below).

## Why now

The lima sandbox VM was found still running on the mini at boot
(load-bearing pid 1115), kept alive by a declarative chain: the mini's
dotfiles-ai config still named `sandbox.atuin_workspace = "personal"`, which
rendered the `dev.dotfiles-ai.atuin-workspace` LaunchAgent, which ran
a foreground `limactl start` of the sandbox VM under RunAtLoad + KeepAlive.
Machine-side state (instance, LIMA_HOME root, agent, plist) was torn down
during discovery; this initiative removes the source machinery so it cannot
be re-created at the next apply.

The replacement services were verified live on the VM during discovery:
atuin runs as the self-hosted fleet server (podman quadlet, syncing all five
machines) and PM/DBSCTR PostgreSQL runs as the pm-postgres quadlet (healthy).
The exited migration-validation containers from 2026-11-15 evidence the
cutover test.

## Context map

| Context | Home | Change |
|---|---|---|
| dotfiles_ai_distribution | Saltiola7/dotfiles-ai | lima subsystem + darwin LaunchAgents deleted; root docs updated; the owner's apply and merged-worktree pruning on the mini |
| dbsctr_knowledge_store | Saltiola7/dotfiles-ai | dial-down: experimental/dormant documented, darwin delivery retired, DKS plans kept as record |
| continuous_validation | Saltiola7/dotfiles-ai | lima execution path removed only; CV is a new experimental feature whose VM-native development proceeds separately |
| personal_dotfiles_residue | Saltiola7/dotfiles | stale LIMA/COLIMA exports, ssh include, Spotlight path — one small PR |

## What retires (dotfiles-ai)

- The lima sandbox subsystem: `sandbox-vm`, `sandbox.json`, `lima/` instance
  templates, the atuin-workspace LaunchAgent + loader, sandbox data keys,
  sandbox shell aliases, `LIMA_SANDBOX.md`, `test_lima_sandbox.py`.
- All darwin workstation LaunchAgents and loaders: dbsctr-embedding,
  dbsctr-code-embedding, dbsctr-knowledge-reconcile, dbsctr-reranker,
  dbsctr-spawner, dbsctr-watchdog, pm-postgres-backup,
  history-projection-refresh, herdr-server, and `configure-pm-postgres`
  (the darwin sandbox path; the linux quadlet path stays).
- CV's lima execution environment: `local_engine.py`, `engine/lima.yaml`.

## What survives (verified consumers)

`state-root-exec` (hermes, codex, herdr-host scripts; active on the VM),
`install-dbsctr-embedding` (OS-neutral), `enable-pm-postgres` and
`enable-atuin-server` (linux quadlet paths), all `remote-*` install scripts
(fleet remote user environments), the herdr-host build path, and
dagger's `_local_engine` socket validation (podman on the VM, unrelated to
lima).

## Operator-gated deferral

The herdr desktop **binary** and its installed state on the mini stay until
the operator confirms completed migration; only declarative plumbing and
auto-start retire here. The obsidian LaunchAgents on the mini are drift
(never managed by current source); no repository apply can remove them, and
this initiative no longer removes anything by hand.

## Owner decisions of 2026-11-24

- **The mini keeps applying dotfiles-ai** (INT-018). Its dotfiles-ai
  configuration stays. The teardown step is withdrawn: nothing is unloaded or
  deleted by hand. The owner applies the merged source once, and that apply
  removes the retired agents and lima files through normal chezmoi removal.
- **dotfiles-ai is no longer developed on the mini** (INT-019), because macOS
  cannot be tested in CI. Work that exists only on the mini is recovered to
  the workstation read-only first.
- **macOS is not tested in CI** (INT-020). Defects are found through the
  owner's direct apply and fixed afterwards; the owner previews each apply
  delta read-only before applying.
- **No bulk deletion on the mini** (INT-021). Checkouts, uncommitted work and
  conversation history stay.
- **Merged worktrees may go** (INT-022). dotfiles-ai worktrees on the mini
  whose branch is already merged into `main` are redundant. A read-only
  inventory lists each one's merge state, uncommitted changes, unpushed
  commits and whether conversation sessions reference it, because the owner
  may still need old context from some of them. Only worktrees on a list the
  owner approves are removed, through the kernel's removal check.

## Accepted risks

- **pm-postgres backup gap** (INT-005): the VM quadlet has no backup timer;
  the pm-kernel refactor in a parallel operator session owns the follow-up.
  This initiative must not touch pm-kernel internals.
- **Public repository** (INT-013): deletions and docs must pass the
  repository's publication checks; no private hosts, credentials, or
  machine-local paths beyond what policy allows.

## Non-goals

Company-VM scope, colima on pi400, blackarch bundles, any new feature
work, pm-kernel/postgres schema changes, and herdr desktop binary removal
(operator-gated).

## Validation strategy

1. Full test suite green in dotfiles-ai (managed-set tests updated for the
   retired targets) and in personal dotfiles.
2. `chezmoi apply` on the VM: clean, no removed targets still managed, both
   quadlets healthy before and after.
3. Mini apply evidence, recorded by the owner: after applying the merged
   source, no retired dotfiles-ai LaunchAgent is loaded and no lima process
   runs; the dotfiles-ai configuration is still present; the personal
   dotfiles apply is unaffected.
4. Convergence: shared ext working tree fast-forwarded to main; both
   machines apply from the same source without the retired machinery.
5. Worktree pruning evidence: the approved list, the inventory before and
   after, and confirmation that every removed worktree was merged, clean and
   without sessions the owner chose to keep.

## Delivery record

| Slice | State | Evidence |
|---|---|---|
| `retire-workstation-source` | delivered | PR #328 (branch `dbsctr/retire-workstation`, cycle DAI-035), merge `5d8681b0`: all ten darwin LaunchAgents and their loaders, the lima subsystem, the atuin-workspace agent and the CV lima path deleted. |
| `mini-teardown-deployment` | rejected | Withdrawn by INT-018. Its statements INT-011 and INT-016 stay as the record of the earlier plan. |
| `personal-dotfiles-residue` | ready | Not started; the stale exports are still on the default branch. |
| `vm-convergence-verification` | ready | Not recorded. |
| `mini-apply-by-owner` | ready | Not started. |
| `mac-worktree-pruning` | ready | Not started. |

## Engineering Profile overrides (this cycle)

Risk: **elevated** (public repo compatibility + live mini production state).
Delivery intent: **merge + deploy** (the owner's apply on the mini is the
deployment step; the build session stays read-only there).
Affected: dotfiles-ai distribution/knowledge/CV docs, personal dotfiles
residue. Base profiles under `docs/specs/*/PROFILE.md` are otherwise
unchanged.
