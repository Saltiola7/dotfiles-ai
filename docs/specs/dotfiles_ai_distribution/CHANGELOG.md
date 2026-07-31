# dotfiles-ai Distribution Changelog

Historical `Intended Final Push` values record the policy at the time. Current
delivery requires a feature branch and verified draft pull request into protected
`main`.

## 2026-07-31 - DAI-021 Continuous Per-Lens R&D

- Replaced the single global lens slot with six independent source-controlled
  slots. Five ordinary lenses exclude improvement-worker session families;
  `review_session_governance` alone reviews them and audits lens usefulness.
- Added durable per-pass page, source, selected-session, selected-review-session,
  excluded-review-session, and unattributed-session telemetry. Typed federation
  removes out-of-scope candidates before model access. Yield immediately reopens only its lens;
  no-yield retains daily-to-weekly-to-monthly backoff per lens.
- Hermes now fills every eligible lens every five minutes. Noncritical P1-P3
  claims may cross Discovery only with explicit autonomous readiness and no
  material uncertainty; P0 and critical or uncertain work block. Draft pull
  request remains the maximum delivery authority. Implementation and live
  validation are in progress.
- Autonomous/operator authorization is durable in the improvement ledger, and
  pass telemetry is accepted only from a private scope/manifest receipt derived
  by the typed adapter from the actual filtered pages.

## 2026-07-31 - DAI-016-F1 Autonomous R&D Launch Repair

- Replaced plugin-loading OpenCode session discovery with the supported `--pure`
  metadata path, added bounded invalid-JSON diagnostics, and made every post-claim
  failure release scheduler ownership and terminate/reap its process group.
- Pinned the exact argparse-safe direct-launch and release commands in the Hermes
  supervisor skill. Added a rendered subprocess E2E covering reserve, discovery,
  live process registration, malformed output, setup failure, post-spawn failure,
  cleanup, and a real installed-OpenCode capability check.
- Split federated history bounds to 300 seconds for the 1.26-million-part host
  database and 120 seconds for workspaces. A controlled Hermes run registered
  worker `dbsctr-5b6f2dc3` and session `ses_049adff6dffeRK2xyOrMZGZMe4`, captured
  644 sessions across seven pages with all three sources available, saved a
  truthful insufficient provider evaluation, and persisted a P2 `yield` claim
  while retaining daily cadence. No Discovery or implementation started.
- Affected QA passed 29 R&D, 38 Lima, and 59 downstream tests; independent review
  found no remaining launch findings. Deployed `dbsctr-rnd`, `sandbox-vm`, and the
  active Hermes supervisor skill with empty second dry-runs. Gate Commits:
  `24d0fd0`, `9a251eb`, `4db52d4`. Gate Exceptions: none. Intended Final Push:
  feature branch and draft pull request into protected `main`.

### DAI-016-F2 CI Session-List Contract

- CI proved that OpenCode 1.18.10 returns successful empty stdout when no stored
  sessions exist. Session discovery now treats that response as an empty set while
  retaining fail-closed handling for non-empty malformed JSON. The subprocess E2E
  fixture distinguishes both contracts instead of relying on a populated local
  session database. The complete 29-test R&D suite passed locally, the corrected
  runner was deployed with an empty second dry-run, and Gate Commit `12d83c6`
   updates draft PR 13. Gate Exceptions: none.

### DAI-016-F3 Launch Cleanup Review

- Independent review found reservation-release failure could skip termination of
  an already-started unregistered worker. Failure cleanup now bounds process-group
  termination and reaping before independently releasing scheduler ownership,
  reports combined failures, and bounds blocked-state recording. Regression
  coverage proves cleanup still reaps the process when reservation release fails
  and kills descendants when the process-group leader has already exited.
- The subprocess fixture now emits actual zero-byte stdout for an empty OpenCode
  session inventory while retaining separate malformed non-empty JSON coverage.
- Focused QA passed 31 R&D tests and union affected QA passed 268 tests with one
  optional Lima skip. Final independent review found no remaining runtime defect;
  commits `5aa248a..857e7af`. Gate Exceptions: none.

## 2026-07-30 - V3.35 Documentation Reconciliation

- Made DAI-020, Hermes orchestration, explicit P2/P3 promotion, private history,
  and current protected delivery authoritative in the profile, Product Intent,
  root guide, and runbook. Archived the completed DAI-015 start plan without
  changing its content. No runtime configuration was applied.

## 2026-07-29 - DAI-020 Final Integration

- Added exact-SHA no-fast-forward integration on ephemeral `rnd/batch/<id>`
  branches, operator-confirmed draft-PR publication, atomic P2/P3 promotion, and
  `/dbsctr-integrate`. Enabled 10 MB Herdr pane history with owner-safe private
  daily snapshots and 30-day pruning. Full QA passed 269 tests with one optional
  Lima skip; primary security review tightened recorded-tip, source/base drift,
  and symlink checks. Independent review was unavailable because the reviewer
  sandbox could not read the isolated worktree. Implementation commit: `748265d`.
  Gate Exceptions: none. Intended Final Push: feature branch and draft pull
  request into `main`; local deployment follows verified merge.

## 2026-07-29 - DAI-019 Proposal Priority Governance

- Added migration-safe P0-P3 priority to durable improvement claims. P0/P1 may
  enter Discovery automatically, while P2/P3 remain queued or may be abandoned
  and are visible through the report-only `/dbsctr-backlog` skill. Legacy queued
  claims migrate to P2 and already-active claims to P1. Full QA passed 265 tests
  with one optional Lima skip; fixed-commit audit and independent review found no
  remaining issues. Commits: `3e293b8..3cb3e19`. Intended Final Push: feature
  branch and draft pull request into `main`.

## 2026-07-29 - DAI-018 Adaptive Lens Governance

- Added one recoverable capture-day owner and five fixed versioned R&D lenses.
  Three daily no-yield passes back off to weekly, four weekly passes back off to
  monthly, and a distinct claim or UTC-quarter rollover restores daily cadence
  without expiring claims. Schema-v1 scheduler data migrates to v3 while legacy
  effect analytics remain intact. Full QA passed 261 tests with one optional Lima
  skip; fixed-commit audit and independent review found no remaining issues.
  Commits: `83b0cd8..c834fd3`. Intended Final Push: feature branch and draft pull
  request into `main`.

## 2026-07-29 - DAI-017 CI Determinism

- Limited feature delivery to one pull-request matrix while retaining direct
  `main` push coverage, and increased the generated concurrency benchmark test
  signal to remain above its ten-percent activation threshold under runner
  contention. Independent review found no issues. Commits:
  `a4027d5..079276b`. Intended Final Push: existing feature branch and draft pull
  request into `main`.

## 2026-07-29 - DAI-017 CI Reliability Follow-up

- Preserved bounded-command failures across late macOS process cleanup races and
  made Final Push reuse only the exact same-repository draft PR despite fork
  branch-name collisions. Full QA passed 259 tests with one optional Lima skip;
  fixed-commit audit and independent review found no remaining issues. Commits:
  `6446290..c7d9981`. Intended Final Push: existing feature branch and draft pull
  request into `main`.

## 2026-07-29 - DAI-017 CI Portability

- Split deterministic rendering checks from external-tool integration checks,
  kept Lima validation capability-optional, and made pinned OpenCode parser
  validation required in CI. Full QA passed 258 tests with one Lima skip;
  fixed-commit audit and independent review found no remaining issues. Commits:
  `fc20e0f..ae54056`. Intended Final Push: existing feature branch and draft pull
  request into `main`.

## 2026-07-28 - DAI-017 PR-Only Protected Delivery

- Protected configured `main` from direct cycle delivery while retaining
  automatic Gate Commits on isolated or existing published teammate feature
  branches. Same-repository draft PR identity now separates repository ownership
  from the authenticated collaborator account.
- Protected-base advancement requires one exact reconciliation merge and fresh
  evidence for every required gate. Affected QA passed 189 tests with one existing
  skip; fixed-commit audit and independent review found no remaining issues.
  Commits: `706711d..b7dedfe`. Intended Final Push: feature branch and draft pull
  request into `main`.

## 2026-07-28 - DAI-016 Hermes-First Orchestration

- Installed checksum-pinned Hermes `0.19.0` with isolated authenticated host,
  personal, and client profiles; configured Codex `gpt-5.6-sol`, bounded canonical
  backlog roots, profile-local cron/Kanban state, and reservation-bound direct
  OpenCode Discovery launch without Herdr scheduling authority.
- Host and both guest gateways passed inference, restart, receipt, and active-job
  checks before native launchd retirement. Guarded global cleanup and shared DVC
  cache relinking reclaimed about 75 GiB while preserving dirty active work.
  Affected QA passed 193 tests with one existing skip. Commits:
  `269125b..dc6d284`. Intended Final Push: `origin/main`.

## 2026-07-27 - DAI-015 Native Tailnet Guest Access

- Added default-off Tailscale settings and stdin-only one-off enrollment without
  committed keys, tags, peer names, account identifiers, or secret references.
  Managed Fedora guests use checksum-pinned `1.98.9` static clients, private
  mode-`0700` state/runtime directories, and persistent rootless userspace
  services; guest `sudo`, root SSH, kernel TUN, routing, and DNS stay unchanged.
- Affected and full QA passed 239 tests with one unrelated skip. Both configured
  guests enrolled under separate private tags, remained online with active user
  services, accepted ordinary SSH and native Herdr `0.7.5` attach, and retained
  compatible persistent Herdr servers. Tailnet policy validation passed an
  owner-only grant plus a negative SSH assertion, with zero reusable auth keys.
  Intended Final Push: `origin/main`.

## 2026-07-26 - DAI-014 Direct Guest Herdr Entry

- Workspace shell aliases now launch guest Herdr when called without arguments;
  explicit commands and direct `sandbox-vm shell` behavior remain unchanged.
- Added checksum-pinned Bash preexec `0.6.0` so Atuin history hooks and Starship
  share one dispatcher. Affected QA passed 64 tests, and both configured guests
  loaded the Atuin widget, history hooks, and rendered Starship prompt in a PTY.
  Intended Final Push: `origin/main`.

## 2026-07-26 - DAI-013 Durable Guest Atuin

- Added checksum-pinned Atuin `18.17.1`, guest-only non-secret sync configuration,
  and interactive Bash initialization for every configured Lima workspace.
  Machine-local sync addresses flow through the existing workspace configuration;
  login, session, and encryption keys remain isolated inside each VM.
- Affected QA passed 64 tests plus Python, Bash, installer, JSON, and chezmoi
  validation. Both configured guests retained their existing authentication,
  completed a live sync, and loaded the Atuin search binding in a pseudo-terminal.
  Recreated guests require one explicit login. Intended Final Push: `origin/main`.

## 2026-07-26 - Provider-Native Evaluation Delivery

- Extended the existing weekly worker with a terminal schema-v2 receipt and one
  typed report save. Dedicated private tables atomically persist exactly five
  unused cycles, source/capture/page/member evidence, required and optional
  metrics, confounders, and sanitized recommendations.
- Added source-local privacy epochs, eight-day replay quarantine, changed-epoch
  and explicit-forget backup purge, semantic backup/restore validation, and
  capture-independent replay. The existing cadence and DAI-011 one-capture
  continuation path remain unchanged. The first real report is tracked as
  DAI-012-F1 until five eligible activated cycles exist. Independent review
  verified selective backup retention and bounded one-use receipts with no
  remaining material findings.

## 2026-07-26 - Provider-Native Evaluation Discovery

- Defined weekly helper-derived five-cycle evaluation, terminal capture receipts,
  dedicated atomic report persistence, loaded activation identity, deterministic
  membership, and privacy-epoch quarantine/forget behavior.
- Kept DAI-011 schema-v2 federation, one-scan continuations, concurrency, source
  deadlines, transient retention, and weekly cadence unchanged. Implementation
  and deployment remain pending. Intended Final Push: `origin/main`.

## 2026-07-26 - DAI-011 Federated R&D Reliability

- Replaced repeated live history scans with one private immutable capture per
  source and capture-backed continuation. Host and configured VM sources now run
  concurrently with configured ordering, per-source 120-second deadlines,
  aggregate output bounds, exact capture/query/database identity, active-worker
  exclusion, descriptor-safe VM lifecycle locks, and 24-hour transient retention.
- Removed the invalid 30-second aggregate typed timeout, normalized runtime-health
  tool output, independently verified configured source order, and canonicalized
  manifest identity through scalar page digests to avoid Python/JavaScript number
  serialization drift.
- The autonomous command now uses 100-item pages, treats its captures as pass
  evidence instead of resaving namespaced cohorts against a changing database,
  and may run only read-only `gh issue list` and `gh pr list` forms without an
  operator. All other GitHub operations remain confirmation-gated.
- Live deployment read the host and both configured workspaces through the
  installed typed adapter over 19 pages in 51.92 seconds. The final controlled worker
  completed five full capture pages, performed repository duplicate checks,
  claimed one sanitized proposal, and reached the required Discovery pause. Its
  worker record, isolated scheduler files, and presentation tab were explicitly
  cleaned afterward.
- The live gate also exposed an already hung launchd watchdog. Runner dependency
  commands now expire after 180 seconds; the operator approved restarting only
  that managed service, whose replacement exited zero, and manual reconciliation
  returned no events. Production cadence remains weekly and unhalted with its
  prior next-eligible timestamp. Release is not applicable. Gate Exceptions: none.
  Intended Final Push: `origin/main`.

## 2026-07-26 - DAI-010 Guest Terminal Parity

- Added Linux-only managed Bash startup and the personal Starship prompt while
  keeping host terminal targets under the personal chezmoi source. Starship
  `1.26.0` installs from a checksum-pinned archive with atomic replacement.
- Declared Catppuccin through OpenCode's supported `tui.json` configuration and
  propagated the visual theme to guest Herdr without mutating OpenCode runtime
  state or importing host credentials, Homebrew paths, or workstation-only plugins.
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
