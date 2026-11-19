# macOS workstation retirement

Status: ready for build. The Try Omarchy VM replaced the mac-mini as the AI
workstation; this initiative makes that replacement permanent in both source
repositories and on the machine. The mini becomes a thin host: personal
dotfiles only, the Try Omarchy app, deskflow, and backups.

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
| dotfiles_ai_distribution | Saltiola7/dotfiles-ai | lima subsystem + darwin LaunchAgents deleted; root docs updated; teardown deployment |
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
(never managed by current source) and are removed explicitly in teardown.

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
3. Mini teardown evidence: no dotfiles-ai LaunchAgents loaded (including
   drift obsidian agents), no lima processes, plists gone, dotfiles-ai
   chezmoi config retired, personal dotfiles apply unaffected.
4. Convergence: shared ext working tree fast-forwarded to main; both
   machines apply from the same source without the retired machinery.

## Engineering Profile overrides (this cycle)

Risk: **elevated** (public repo compatibility + live mini production state).
Delivery intent: **merge + deploy** (mini teardown is the deployment step).
Affected: dotfiles-ai distribution/knowledge/CV docs, personal dotfiles
residue. Base profiles under `docs/specs/*/PROFILE.md` are otherwise
unchanged.
