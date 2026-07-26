# dotfiles-ai Distribution Changelog

## 2026-07-26 - DAI-010 Guest Terminal Parity

- Added Linux-only managed Bash startup and the personal Starship prompt while
  keeping host terminal targets under the personal chezmoi source. Starship
  `1.26.0` installs from a checksum-pinned archive with atomic replacement.
- Reconciled Catppuccin into OpenCode's persisted theme selection while
  preserving unrelated runtime state, and propagated the visual theme to guest
  Herdr without importing host credentials, Homebrew paths, or workstation-only
  plugins.
- Applied the exact committed tree to both configured guests. Chezmoi verify,
  Bash syntax, Starship config identity, version, and resolved OpenCode theme
  passed in each workspace; host verify and no-overlap checks passed.
- Validation: 214 passed, 1 skipped; rendering, shell syntax, checksum install,
  live host/guest apply, and independent review passed after hardening Linux
  ignore rules and atomic installation. Release is not applicable. Existing
  accepted risk `DAI-007-AR1` is unchanged. Intended Final Push: `origin/main`.

## 2026-07-25 - DAI-009 Dynamic Workspace Shell Aliases

- Added optional unique `shell_alias` values to version 3 workspace
  configuration. Invoking a configured alias follows the same validated path as
  `sandbox-vm shell WORKSPACE` and preserves command arguments.
- Added chezmoi reconciliation for machine-local alias symlinks. Apply refuses
  unmanaged collisions and removes only stale links still targeting the managed
  controller.
- Configured and applied two machine-local aliases. Both commands reached their
  configured guests, host chezmoi is drift-free, and workspace health passed.
- Validation: 212 passed, 1 skipped; Python compilation, rendered shell syntax,
  template rendering, sanitation, local apply, alias smoke tests, and direct
  security review passed. Release is not applicable. Existing accepted risk
  `DAI-007-AR1` is unchanged. Intended Final Push: `origin/main`.

## 2026-07-25 - DAI-008 Dynamic Workspaces

- Replaced fixed public sandbox identities with a version 2 machine-local list
  of arbitrary workspace names, instances, host-to-guest mappings, read/write
  modes, optional Git submodule protection, optional references, federation,
  and a configured Build destination.
- Replaced two duplicated Lima templates and shell wrappers with one generic
  renderer and bounded `sandbox-vm render|validate|shell|create|update`
  commands. Dynamic federation and typed handoff now validate configured source
  IDs rather than a fixed source count.
- Migrated this machine's untracked TOML without changing existing VM names or
  mounts. Full host apply succeeded, obsolete generated targets were retired,
  both configured templates passed bounded Lima validation, workspace health
  passed, and host `chezmoi status` is empty.
- Validation: 208 passed, 1 skipped; Python compilation, template rendering,
  sanitation, dry-run/apply, no-drift, and direct security review passed.
  Independent review was unavailable because its external-worktree policy
  denied access. Existing accepted risk `DAI-007-AR1` is unchanged. Release is
  not applicable. Intended Final Push: `origin/main`.

## 2026-07-24 - DAI-007 Lima Sandbox

- Added two isolated, locally named Fedora Lima runtimes, explicit host mounts,
  VM-local Herdr/OpenCode state, bounded updates, sparse allocation reporting,
  and protected submodule paths in one configured workspace.
- Added source-namespaced federated history with strict scalar schemas, filter-
  bound continuation identity, canonical manifest integrity, and bounded source
  availability. Host deployment and runtime probes remain active.
- Added VM lifecycle surfaces for the two configured instances while guest Herdr
  and OpenCode keep native names. Removed the inherited host-home mount and added a boot-time
  systemd verifier that reapplies protection before publishing readiness after
  live VZ validation exposed both defects.
- Live Fedora provisioning also proved Lima preserves the macOS account UID;
  guest identity now binds to the unique `.guest` home instead of assuming UID
  `>=1000`.
- Deployment: recreated the protected workspace from the corrected template and verified
  initial boot plus cold restart. Both declared roots remained writable, the
  inherited home mount was absent, every protected submodule and Git metadata
  overlay was read-only, sudo was non-executable, and OpenCode stayed gated on
  the boot verifier. Sparse host allocation was about 2.01 GB.
- Created the writable workspace and verified its single writable root, absent
  inherited home mount, non-executable sudo, isolated empty database, tools, and
  boot verifier before and after a cold restart. Sparse allocation was about
  2.01 GB; live three-source federation and stopped-workspace restoration passed.
- Kept the wrapped real executable basename as `opencode` so Herdr can detect,
  track, and restore auto-approved guest sessions.
- Final recreation verified Herdr detects wrapped OpenCode as canonical and
  reports it idle with `--auto`; after a cold restart Herdr restored the exact
  workspace, tab, and pane. Session-ID resume remains pending authenticated use
  because the smoke session never acquired an eligible OpenCode session ID.
- Workspace shell commands now default guest shells to portable `xterm-256color`
  instead of inheriting unavailable host-specific terminfo such as
  `xterm-kitty`; `LIMA_TERM` remains an explicit override.
- Final authenticated restart restored exact OpenCode session identity in its
  original workspace, tab, and pane with the canonical `opencode --auto`
  process. All three federated sources remained
  available. The operator explicitly accepted broader work-account credential
  scope as `DAI-007-AR1`, owned by the operator and reviewed by 2026-08-18 or
  before rotation; VM controls and provider repository authorization compensate
  until a repository-scoped credential is available.
- Final gates: immutable lifecycle audit and independent review found no issues;
  207 tests passed with 1 skipped; live sandbox health and maintenance contracts
  passed. Deployment credential scope remains failed with approved accepted risk
  `DAI-007-AR1`. Intended Final Push: `origin/main`.

## 2026-07-22 - DAI-006 Recovery Health

- Recovered large sessions with the proven prompt-free OpenCode mini interface,
  explicit project identity, no visible-history replay, a 120-second readiness
  window, and unchanged exact-pane/argv ambiguity rejection.
- Watchdog reconciliation now emits bounded JSON and exits nonzero for degraded
  events, including durable blocked workers that still have a visible Herdr
  agent. Healthy, recovered, and lock-contended runs remain zero.
- Validation: 14 R&D tests passed on Python 3.12, 3.13, and 3.14; rendered Python
  parsed, exact chezmoi verification passed, and independent review found no
  remaining issue. Gate Commits: `7606dac`, `c5a82e7`, `d567eb4`, `e3ab763`,
  `838a8ea`, `8fd16f0`. Gate Exceptions: none.
- Deployment: exact runner apply recovered worker `dbsctr-97efefcc` into stable
  single-pane `w7:t2M`; exact mini argv remained idle and a repeated watchdog
  returned no events. Launchd run 1122 exited zero. Weekly cadence remains
  unhalted with its next eligible tick on 2026-07-27. Release is not applicable.
  Intended Final Push: `origin/main`.
- Delivery correction: DAI-006B recomposed the reviewed final tree from the
  advanced `origin/main` after Final Push safely rejected an unrecorded upstream
  merge commit; no history was rewritten and no evidence guard was bypassed.
  Recomposed Gate Commit: `63a9c34`.

## 2026-07-19 - DAI-004 Adaptive Cadence

- Added bounded human/JSON analytics, authoritative failed outcomes, immutable
  merge references, exactly-once benchmark effect finalization, deterministic
  monthly cohorts, and one-step weekly, twice-weekly, and daily cadence decisions.
- Added a durable private scheduler SQLite ledger with semantic integrity,
  transactional spawn reservations, a hard three-worker cap, persistent
  three-failure/malformed-state halt, and history-preserving manual reset. The
  fixed daily launchd tick now evaluates cadence without rewriting TOML or jobs.
- Pending merges, incomplete/insufficient effects, and active work are reported
  but excluded from the denominator. Cost is reported when authoritative and
  never controls cadence or safety; ordinary workers remain draft-PR-only.
- Validation: 17 distribution tests and rendered compilation on Python 3.12,
  3.13, and 3.14 passed, covering concurrent admission, thresholds, retry
  history, halt/reset, malformed state, exact finalization, pending/incomplete
  exclusion, regression, and report-only cost. Independent review was unavailable
  because the reviewer could not access the isolated worktree; direct primary
  review hardened ownership, durability, event semantics, and worker identity.
  Gate Commit: `b0568dc`. Gate Exceptions: none. Deployment: exact runner apply;
  live analytics conservatively observed three historical failures, then explicit
  reset restored an unhalted weekly schedule while preserving those events. The
  first complete real 30-day effect remains scheduled. Intended Final Push:
  `origin/main`.

## 2026-07-19 - Adaptive Cadence Discovery

- Approved future CLI/JSON analytics and a private monthly cadence ladder with
  immutable outcome events, transactional three-worker admission, repeated-
  failure halt, manual reset, unchanged user TOML, and report-only cost.
- Validation: 52 affected tests, diff checks, and two independent review rounds.
  Contract Gate Commits: `dcea012`, `bacdaaa`, `7c336b0`, `a02bfce`. Gate
  Exceptions: none. Intended Final Push: `origin/main`.

## 2026-07-18 - DAI-005 Native OpenCode R&D Scheduling

- Replaced Hermes gateway, cron, supervisor skill, updater, and runtime ownership
  with an opt-in launchd spawner and watchdog around Herdr, OpenCode, and the
  existing DBSCTR ledger. Shared scheduling defaults remain disabled.
- Preserved fresh full-history workers, single-pane terminal ownership, explicit
  Discovery proceed, exact-session recovery, and human-merge-only draft PRs.
- Normalized custom Build IDs to lowercase filename-derived `build-gpt` and
  `build-claude`; model selection no longer masquerades as agent selection, and
  Claude delegation remains hard-limited to Bedrock Sonnet 5 subagents.
- Validation: 160 passed, 1 skipped; enabled/disabled rendering, plist parsing,
  real Herdr 0.7.3 nested responses, exact registration, fallback cleanup,
  recovery ambiguity, PR reconciliation, and independent review passed.
- Deployment: launchd loaded the 09:00 spawner and 300-second watchdog; worker
  `dbsctr-bdfc3d4d` registered in single-pane `w7:t1A`, began full-history
  review, and a repeated watchdog run was a no-op.
- Retirement: both Hermes cron jobs, gateway, Herdr integration, updater,
  executable, `~/.hermes`, and source-owned reconciliation state are absent.
  Gate Exceptions: none. Intended Final Push: `origin/main`.
- Delivery correction: DAI-005B recomposed the reviewed final tree from
  `origin/main` into one fully recorded Gate Commit after DAI-005 Final Push
  rejected unrecorded intermediate commits.

## 2026-07-18 - DAI-003G Full-History Improvement Lenses

- Changed autonomous R&D from one unreviewed page to every sanitized history
  continuation with no reviewed-status filter. Review markers remain available
  only as filters and are never changed by autonomous lens runs.
- Required a bounded running shortlist and a plain-language evidence, impact,
  interface, and non-goal summary before any claim or Discovery questions.
  Correlation remains supporting evidence rather than a standalone proposal.
- Refreshed validated live cohort evidence during history save while preserving
  archive-only members, so existing incomplete archives cannot erase richer live
  metrics and retained sessions remain replayable.
- Validation: 130 passed, 1 skipped; compilation, diff checks, mixed live/archive
  persistence, command rendering, independent review, targeted deployment, and
  live full-history worker startup passed.
- Deployment: managed helper and `/dbsctr-improve`; stale first-page Discovery
  worker abandoned and replaced by registered worker `dbsctr-4f6c2a91` in its own
  tab. Gate Exceptions: none. Intended Final Push: `origin/main`.

## 2026-07-18 - DAI-003F R&D Runtime Hardening

- Added one persistent single-pane Hermes console and one final single-pane tab
  per OpenCode worker. Argv-safe OpenCode starts in a disposable staging tab so
  Herdr's required split never remains in the operator layout.
- Added the managed user-local binary directory to launch and worker PATH, and
  accepted colon-form Herdr workspace, tab, and pane presentation IDs without
  widening worker, session, or cycle identifiers.
- Added exact resumed-process fallback reconciliation using recorded workspace,
  tab, pane, one-pane topology, physical cwd, and foreground argv.
- Validation: 116 passed, 1 skipped; rendering, Python compilation, diff checks,
  independent review, targeted deployment, quoted-command and real Herdr staging
  smokes, exact-session resume, and repeated watchdog checks passed.
- Deployment: helper, supervisor, watchdog, and LaunchAgent plist applied without
  restarting Herdr. Explicit worker PATH is active now; LaunchAgent PATH applies
  at the next normal Herdr restart. The worker reached private review, then a
  separate concurrent-database snapshot issue blocked persistence for follow-up.
- Gate Exceptions: none. Intended Final Push: `origin/main`.

## 2026-07-18 - DAI-003 Autonomous R&D Loop

- Replaced the fixed review session with one fresh native-Build OpenCode tab per
  daily run in a managed Herdr workspace, while preserving global private review
  and limiting public changes to this source.
- Added transactional non-expiring worker, opportunity, scope, recovery, and PR
  outcome state to the private SQLite ledger, with exact-session autoheal and
  explicit retry or abandonment after three failures.
- Added a five-minute zero-token watchdog gate, isolated GitHub degradation,
  capability-first Discovery workflow, branch-only `draft_pr` delivery, and
  Final-Push-only verified PR binding. Automatic merge, ready, release, and
  deployment remain impossible.
- Added README quickstart and the complete Hermes operator runbook.
- Validation: 157 passed, 1 skipped; render, shell, Python compile, resolved
  OpenCode config, draft-only local-remote fixture, independent review, targeted
  deployment, gateway, cron, Herdr, and empty-ledger health checks passed.
- Deployment: local managed targets; Hermes jobs `e4ccd3101611` and
  `e3290c4b76b8` active. Gate Exceptions: none. Intended Final Push:
  `origin/main`.

## 2026-07-17 - DAI-002 Hermes Supervisor PoC

- Added opt-in Hermes bootstrap, gateway supervision, Herdr integration, daily
  DBSCTR review scheduling, checked updates, and machine-local repository policy.
- Bound reviews to one dedicated native Build session and fail closed on
  ambiguous identity, custom primaries, unrelated permissions, or new authority.
- Added bounded `Allow once` handling for review persistence and compaction only
  after successful persistence.
- Added runtime self-repair when the Hermes launcher cannot report a version.
- Validation: 149 passed, 1 skipped; rendered shell and plist checks passed;
  managed dry-run reported no drift.
- Runtime smoke: cron execution `314956082b7d40f791a390fe2fe10d84`
  marked 3 sessions and 1 cycle reviewed, then compacted only the dedicated
  worker from 15.3K to 3.2K tokens.
- Gate Exceptions: none.

## 2026-07-13 — v0.1.0

- Added a standalone public chezmoi source for DBSCTR V3.10, OpenCode, and
  Herdr configuration.
- Added curated machine-local TOML overrides without committed account IDs,
  credentials, or paths.
- Added opt-in 1Password session integration and a credential-free macOS Aqua
  LaunchAgent.
- Added installation, preview, cutover, rollback, update, and retirement
  guidance.
- Validation: 92 passed, 1 skipped; JSON, shell, plist, public-safety, parity,
  and runtime checks passed.
- Independent review found no remaining cutover blocker.
- Deployment restored Herdr workspaces under `dev.dotfiles-ai.herdr-server` but
  required a visible server restart.
- Gate Exceptions: none.
- Intended Final Push: `origin/main`.
