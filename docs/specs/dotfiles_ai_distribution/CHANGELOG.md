# dotfiles-ai Distribution Changelog

## 2026-09-01 - Portable Rollout Runtime

- Added an owner- and symlink-safe bootstrap for one full public revision,
  checksum-pinned user-local chezmoi, structural foundation validation, and
  content-free `auth_pending`, `ready`, and `failed_retryable` refreshes without
  starting authentication.
- Required a usable configured root `mise.toml` before client mutation and proved
  repository-bound `mise run remote-dev -- iap` forwarding from another working
  directory. CentOS receives a regular gcloud launcher while existing Fedora
  symlink behavior remains unchanged.
- Affected validation passed 46 tests; CI-equivalent full validation passed 681
  tests, one expected skip, and 21 subtests. Shell/Python syntax, Git diff hygiene,
  and a disposable CentOS Stream 10 x86_64 bootstrap, retry, empty reapply,
  `auth_pending`, simulated `ready`, integrity failure, update, and rollback passed.
  Authentication, sessions, and history survived rollback; no live login, shared
  VM, cloud runtime, private endpoint, personal source, or production home was
  accessed. The named disposable Podman machine was removed.
- Gate Commits: `042cf96`, `d6388fe`, `b3ca452`, `86b81fd`, `c4052d3`, and
  `247982e`. Gate Exceptions: none. Release and DVC are not applicable. Intended
  Final Push: feature branch and draft pull request into protected `main`.

## 2026-09-01 - Portable Rollout Runtime Readiness

- Split public user bootstrap, content-free authentication-state refresh, and
  strict client preflight from the private two-user deployment slice.
- Required one immutable public revision, owned non-symlinked paths, structural
  failure as `failed_retryable`, incomplete login as `auth_pending`, complete
  probes as `ready`, and no automatic interactive authentication.
- Required a usable configured root `mise.toml`, cwd-independent task forwarding,
  disposable CentOS proof, and no shared-VM access. No runtime changed.

## 2026-09-01 - History Projection Refresh Schedule Readiness

- Specified an explicitly enabled daily 04:30 local, low-priority, single-flight
  LaunchAgent for lifecycle-owned History snapshot refresh.
- Refresh failure, overlap, timeout, sleep, restart, disablement, and rollback
  preserve the prior projection and expose only bounded content-free status.
- This Discovery change installs or loads no job; implementation and managed-host
  activation remain separately approval-gated after lifecycle refresh delivery.

## 2026-09-01 - Remote Agent Authentication

- Added a remote-only content-free agent readiness target and forced OpenCode,
  Codex, and Vertex runtime state into each invoking Unix user's home.
- Preserved credential-free render, installation, update, rollback, and shell
  startup; authentication remains an explicit per-user operation.

## 2026-08-31 - CentOS Remote User Foundation

- Added a default-off CentOS Stream 10 x86_64 user foundation with independently
  pinned OpenCode, Codex, Herdr, Atuin, Starship, 1Password CLI, Docker Compose,
  and Google Cloud CLI assets while preserving Fedora aarch64 defaults.
- Added an owner-private, lock-safe foundation state command with full-commit
  apply, same-revision retry, managed-target manifests, content-free status, and
  rollback that preserves credentials, sessions, history, and unrelated files.
- A disposable CentOS Stream 10 x86_64 container passed checksum verification,
  two empty-convergent applies, exact runtime versions, and sanitized status.
  Affected compatibility validation passed 158 tests; the repository-wide run
  passed 657 tests, one expected skip, and 21 subtests after removing inherited
  live DBSCTR state-root variables to match isolated CI execution.
- Gate Commits: `5732639`, `495ad76`, `305baed`, and `020a8e6`. Gate Exceptions:
  none. No live GCE user home, provider credential, tailnet policy, or service was
  changed. Intended Final Push: feature branch and draft pull request into
  protected `main`.

## 2026-08-31 - CentOS Remote Workspace Discovery

- Added the target contract for generic CentOS Stream 10 x86_64 user-local
  distribution, immutable-revision apply, sanitized bootstrap state,
  idempotency, and rollback.
- Kept macOS and Fedora aarch64 behavior unchanged and prohibited user, employer,
  client, project, machine, tailnet, endpoint, and credential identity in public
  source or rendered defaults.
- No package, target, service, user home, credential, or runtime changed.
  RWUE-001 remains digest- and approval-gated.

## 2026-08-29 - DAI-034 Portable Remote Workspace Client

- Added an opt-in machine-local remote-workspace profile, private environment
  rendering, and prerequisite doctor without embedding endpoint identity or
  credentials in public source.
- Added mise and Google Cloud CLI to the managed macOS packages while preserving
  repository-owned lifecycle tasks as the sole remote-operation interface.
- Full validation passed with `559 passed, 1 skipped`, plus Ruff, shell syntax,
  rendering checks, and Git diff hygiene. Gate Commit: `73f8ff1`; no live
  installation or network enrollment occurred. Intended delivery is the feature
  branch and draft pull request into protected `main`.

## 2026-08-30 - Managed Codex Distribution

- Installed the official Codex `0.151.0` Homebrew cask on the Apple Silicon host
  and the checksum-pinned aarch64 musl release in both registered Fedora guests.
- Added a dedicated CLI `CODEX_HOME`, PATH wrapper, digest-owned journaled
  projection, versioned runtime-selector schema, exact temporary-source guest
  deployment, package rollback, and reverse-order all-guest rollback without
  reading or changing authentication, sessions, logs, desktop state, or worker
  routing.
- A host target-mode preflight and the first broad guest apply failed closed;
  package and guest rollback completed before owner-approved directory hardening
  and Codex-only deployment remediation. Both guests retained their prior running
  state and clean canonical source checkout.
- Two hundred eight affected tests, Python compilation, rendered Bash/Chezmoi,
  Initiative validation, Git whitespace, official release metadata, controlled
  host/two-guest deployment, runtime smokes, and independent elevated-risk review
  passed. Gate Exceptions: none. Release is not applicable. Gate Commits:
  `38bd08eda526400884de3338f80c3757ebcbc85e`,
  `3d25ec089280bfcc8336a7ea23988964acd357a4`,
  `da8f306b1041dddd679a8da71b1ff4638f62996e`, and
  `4b131de9e2a6a48cf2574bbab1e9166d6c5db490`. Intended Final Push: feature
  branch and draft pull request into protected `main`.

## 2026-08-30 - Promoted Codex Distribution Readiness

- Recorded merged host-foundation delivery and promoted only
  `codex-distribution` to receipt-ready without changing package, configuration,
  guest, runtime, authentication, or deployment state.
- Retained Codex `0.151.0`, the Fedora aarch64 musl asset, and its digest as
  proposed implementation inputs subject to fresh Build verification. Exact
  version output remains a bounded deployment probe because upstream does not
  document its stdout shape.
- Identity, worker, history, recovery, federation, and final parity slices remain
  dependency-blocked pending fresh evidence from their predecessors.
- Initiative validation, 54 affected lifecycle and distribution tests, Python
  compilation, Git whitespace, official-source verification, and independent
  elevated-risk review passed. Gate Exceptions: none. Release, Deploy, and
  Operate are not applicable. Development Gate Commit:
  `d35d3ca7f966af70c908f2f49e33e605cd82d600`. Intended Final Push: feature
  branch and draft pull request into protected `main`.

## 2026-08-30 - Align Codex Managed Source Projection

- Aligned the captured distribution contract with the approved host-foundation
  source: project recursive `agents/**/*.toml` roles and carry the five identity
  hooks inline in `config.toml` rather than projecting a separate hook tree.
- No package, configuration, guest, runtime, authentication, or deployment state
  changed; `codex-distribution` remains captured behind host foundation.

## 2026-08-30 - Refined Codex Distribution Readiness

- Fixed distribution as the second of two sequential pull requests, responsible
  for exact host/guest installation, projection, wrapper activation, selector
  schema, all registered guest updates, and automatic future guest provisioning.
- Required existing guest-local login for authenticated probes and workers while
  prohibiting automatic login, shared API-key injection, and auth copying.
- The slice remains captured until `codex-host-foundation` is delivered. No
  package, guest, configuration, or runtime was changed in Discovery.

## 2026-08-29 - OpenCode 1.18.25 VM Parity

- Updated the checksum-pinned Linux arm64 OpenCode runtime from 1.18.23 to
  1.18.25 and routed every managed R&D worker launch and resume through the
  dedicated `build-rnd` primary.
- `sandbox-vm update-all` updated both configured workspaces. The host and both
  guests report exact 1.18.25 parity; the targeted scheduler and runtime files
  were deployed, and all 147 affected tests pass.
- An operator-approved schedule reset cleared the retained `malformed_state`,
  reservations, and launch backoff. Schema 3 health now reports no halt, no active
  attempt, and no launch backoff. Existing managed rollback restores each guest's
  prior runtime if a future ordered update fails.
- The deployed parity helper now accepts and returns the approved VM instance;
  both configured workspaces pass that instance-bound 1.18.25 parity check.
- Two pre-final-deployment launches could not resolve `build-rnd` and entered the
  bounded retry backoff. Current schema 3 health has no halt or active attempt,
  and a fresh OpenCode 1.18.25 process resolves `build-rnd` as a primary; the
  backoff remains intact rather than forcing another autonomous provider call.

## 2026-08-29 - Isolate Local Lifecycle And PM Artifacts

- Added managed global Git excludes for `.dbsctr/`, legacy plan JSON,
  `data/backlog/`, and `docs/tickets/`.
- Retired autonomous PM ticket discovery; PM now runs only by direct invocation.

## 2026-08-29 - Captured Codex CLI Distribution Contract

- Captured peer-runtime installation, a PATH-preferred `CODEX_HOME` wrapper,
  digest-owned configuration projection, macOS/Fedora package boundaries,
  explicit automation selection, and rollback without changing live systems.
- Kept desktop, host, and guest state and authentication separate and made the
  proposed release, asset, and checksum subject to fresh implementation proof.
- Initiative validation, 57 focused helper/lifecycle/distribution tests, Python
  compilation, Git whitespace, and independent elevated-risk review passed.
  Gate Exceptions: none. Release, Deploy, and Operate: not applicable. Gate
  Commit: the commit containing this entry.

## 2026-08-29 - DAI-035 R&D Launch Health

- Corrected the delivered launch-health ticket from the duplicate `DAI-032`
  identity to canonical `DAI-035`; historical branches, pull requests, and Gate
  Commit identities remain unchanged. Corrective Gate Commit: `d599d9e`.
- Cut machine-local review and backlog authority over to the moved public
  source, migrated retained scheduler state to schema 8, and added path-free
  health schema 3 with bounded 5-minute through 6-hour launch backoff.
- Preserved exact guarded Hermes gateway commands, launchd readiness, cadence,
  25 retained passes, and schema 7/8 autonomous readiness compatibility; also
  normalized the pre-existing canonical V3.37 ticket that blocked dispatch.
- Fifty-five affected R&D and PM tests, canonical tickets, rendered deployment,
  drift checks, schema migration, and guarded launchd health passed. The operator
  approved deferring pass 26 until the draft merges and the dirty configured
  source is reconciled. Gate Commits: `39cd463`, `12bf51e`; intended Final Push
  is the feature branch and draft pull request into protected `main`.

## 2026-08-28 - DAI-033-1 Host Container Runtime Retirement

- Made managed Fedora Lima workspaces with rootless Podman the only supported
  local container runtime and changed portable shell paths to derive from runtime
  `$HOME`.
- Removed host-runtime fallback guidance from current configuration, operations,
  behavior, and maintenance contracts while preserving historical records.
- Proved both guest Compose paths, zero active Camplan consumers, and healthy
  Atuin before disabling stale startup and permanently deleting the approved
  no-backup host runtime state.
- Removed the host Docker CLI, Compose, Buildx, and credential helper. Homebrew
  unexpectedly autoremoved Lima and `usage`; Lima was restored at 2.2.0 and
  `usage` at 6.5.0 before final managed-workspace and Atuin probes passed.
- Affected QA passed 78 tests, Ruff, ticket validation, Git whitespace checks,
  live runtime postconditions, and independent review. Gate Exceptions: none.
  Gate Commits: `9d7e750`, `97ca69f`, `564d033`, `d021521`, `cc37c05`,
  `205b620`, `0e8cfa3`, `80ccdd8`, `9feb34d`, `e00ad53`, `12742be`,
  `fe731c0`, `402a943`, `7dd64ed`, `1f5e038`. Intended Final Push: feature
  branch and draft pull request into protected `main`.

## 2026-08-28 - Initiative Runtime Distribution

- Added separate context profiles, managed Initiative control-plane deployment,
  and atomic release-matched Herdr skill installation from `herdr --skill`.
- Targeted Chezmoi deployment, exact source identity, idempotence, Herdr skill
  identity, and deployed helper/plugin smokes passed.

## 2026-08-27 - Portable OpenCode Package Ownership

- Made `dotfiles-ai` the sole OpenCode package owner through the official
  `anomalyco/tap/opencode` Homebrew formula and a hash-triggered, fail-loud
  chezmoi installer.
- Removed the duplicate personal Brewfile declaration in
  `Saltiola7/dotfiles#9` while retaining the existing native-binary wrapper,
  centralized state, and update authority.
- Validation: 17 portable-distribution tests, rendered Bash syntax, idempotent
  `brew bundle`, live OpenCode `1.18.23` checks, and the full suite of 486 tests
  pass. Gate Commits: `4efa7f2`, `90bcb95`. Gate Exceptions: none. Intended
  Final Push: feature branch and draft pull request into protected `main`.
## 2026-08-26 - DAI-031 R&D State Authority and Health

- Centralized scheduler state and receipt resolution without migrating or
  deleting the retained local shadow state, and added path-free schema 2 health
  reporting for authority, halt state, active attempts, and all six lenses.
- Kept registered parallel batches independent of the global review lock while
  retaining authoritative reconciliation for fresh, incomplete, and exhausted
  batches.
- Forty focused tests, rendering, deployment drift, live health, and independent
  review passed. Hermes completed all six lenses, increased retained passes from
  19 to 25, and reached `no_lens_due` with zero active attempts. Gate Exceptions:
  none. Gate Commits: `79ff5fe`, `0ab16f8`; intended Final Push is the feature
  branch and draft pull request into protected `main`.

## 2026-08-25 - DAI-030 Managed OpenCode Runtime Parity

- Centralized the reviewed OpenCode 1.18.23 Linux arm64 release and SHA-256,
  added idempotent existing-guest repair, exact parity checks, ordered all-guest
  runtime updates, and prior-state restoration without forcing unrelated guest
  dotfile changes.
- Made typed VM handoff fail before Herdr mutation on stale runtime parity and
  use the valid lowercase `dbsctr-handoff` agent while retaining hard-coded
  interactive Build authority.
- Deployed the targeted host files and checksum-pinned runtime to both configured
  guests. The guests and host report 1.18.23, both VMs returned running, both
  interactive Build parser smokes passed without inference, and targeted host
  drift is zero.
- All 97 affected tests, Python compilation, canonical ticket validation, Git
  whitespace validation, and independent review passed. Gate Exceptions: none.
  Gate Commits: `7960961`, `57b138c`. Intended Final Push: feature branch and
  draft pull request into protected `main`.

## 2026-08-25 - DAI-029 Lifecycle Artifact Reconciliation

- Reconciled five delivered OCP/OIC tickets with their committed completion
  evidence and retained an explicit missing-cost characterization as
  `unavailable`; runtime source and environments are unchanged.
- Retired clean empty AUTH-015 and DAI-022 cycle records. AUTH-014 remains
  unchanged in `finalizing` because typed retirement rejects that state, preserving
  the reproduced deadlock for the owning recovery cycle.
- All 160 focused `dbsctrctl` tests, zero-finding canonical ticket validation,
  lifecycle artifact checks, and Git whitespace validation passed. Gate
  Exceptions: none. Gate Commit: `d67435d`.

## 2026-08-23 - DAI-021-F2 Complete Six-Lens Discovery

- Replaced model-mediated history paging with deterministic source-local lens
  summaries over every immutable capture member, exact distributions, and at
  most 20 bounded evidence projections per source.
- Reused fresh query-compatible no-exclusion captures for 24 hours under the
  private writer lock, applied current worker-family exclusion at summary time,
  and bound the exact compact helper envelope through typed receipt validation.
- Deployed exact committed helpers to the host and both configured guests. The
  live scheduler completed all six lenses across all three sources, retained zero active
  attempts, and produced three distinct P1 performance-cost claims before a
  terminal no-yield pass; governance reviewed 540 attributed review sessions.
- Affected QA passed 289 tests with one optional skip before the digest repair,
  then 93 runtime/sandbox tests and exact raw-envelope security regressions.
  Independent review closed every finding. Gate Exceptions: none. Gate Commits:
  `cdcdfd2`, `5e39aca`, `e6d83c9`; intended Final Push is the feature branch and
  draft pull request into protected `main`.

## 2026-08-23 - DAI-021-F1 Restore Continuous Six-Lens R&D Dispatch

- Force-refreshed Hermes gateway definitions, pinned the launchd runtime to an
  internal macOS Python while retaining external state, removed external working
  directory and log dependencies, and required live launchd readiness before
  cron cutover.
- Serialized cron reconciliation, pruned duplicate and obsolete mode jobs,
  refreshed project-profile gateways, and retained exactly one refinement and
  one maintenance job.
- Normalized two malformed canonical tickets that blocked backlog projection.
  An isolated committed-source proof reclaimed six stale attempts, registered
  all six lens workers, and ended at `no_lens_due`; production projection remains
  fail-closed until these ticket fixes merge to protected `main`.
- Affected QA passes 102 tests, ticket validation, shell/Python syntax, and diff
  checks. Independent review found no high- or medium-severity issues; executable
  fake-launchctl coverage for project profiles remains a residual test gap.
- Post-reconciliation union QA passes 127 tests. Final Gate Commits include
  `c4a8f6c`, `57a51bd`, reconciliation commit `2e4ab64`, and reviewed union
  commit `163aada`.

## 2026-08-21 - Complete Guest Compose Tooling

- Added shared Fedora `make` provisioning and an exact idempotent
  `sandbox-vm install-make WORKSPACE` repair that restores each guest's prior
  lifecycle state and does not widen sudo authority. Both managed guests now
  report GNU Make 4.4.1, rootless Podman, and Docker Compose v2.40.3.
- Completed no-cache builds and five-service startup under serialized Podman and
  retained Colima. Postgres, Redis, Prefect, and Vite passed runtime probes; no
  enterprise container mapped the service-account token or ambient Vertex ADC.
- Preserved the original Postgres and Redis volume creation identities in both
  runtimes. Colima was stopped before both Podman guests were restored; the
  development stack and the personal Atuin health endpoint are active again.
- Repeated Django probes truthfully exposed an application-owned shared async
  Redis client defect. Colima also exposed the application's macOS GID 20 build
  collision; a process-local GID 1000 workaround proved fallback operation.
  Neither downstream defect changed dotfiles scope.
- Affected QA passed 106 tests; post-reconciliation union QA passed 319 tests
  with one optional Lima skip, plus Python compilation, diff checks, ticket
  validation, live runtime switching, and independent review. Gate Exceptions:
  none. Gate Commits: `74daa67`, `0597aea`, `c4b1bf3`; intended Final Push is the
  feature branch and draft pull request into protected `main`.

## 2026-08-19 - Pinned Local Embedding Service

- Added and deployed a default-off, loopback-only Qwen3 Embedding 8B service
  backed by exact read-only llama.cpp/model artifacts, private API access,
  semantic readiness, metrics, and launchd restart recovery. Fifty-three affected
  tests and independent post-deployment review passed; release is not applicable.

## 2026-08-18 - PM Kernel Projection Support

- Migrated distribution work records to canonical tickets, switched Hermes
  refinement to deployed `pmctl`, and added default-off PostgreSQL 19 rootless
  Podman configuration with schema-aware migration and health checks.

## 2026-08-16 - DAI-028 Lima Podman Development Runtime

- Made rootless Podman the managed runtime in both Lima workspaces, with pinned
  Docker Compose v2.40.3, a `docker` compatibility shim, enabled user sockets,
  1Password CLI 2.39.0, and Google Cloud SDK 580.0.0. Colima remains stopped as
  an explicit compatibility fallback.
- Forwarded the Keychain-backed service-account token only in workspace-shell
  memory. The replacement immutable account has `Automation` read access and
  operator-approved development-vault read/write access. Host and guest probes see
  both vaults; all 14 locally migrated development-project references resolve
  without exposing values. Their owning repository remains dirty and the migration
  is external drift pending separate delivery. Whole-template `op run` remains
  blocked by existing backlog `DBX-1`, because the configured Databricks item has
  not been provisioned.
- Authenticated guest-private Vertex ADC, pinned its configured quota project,
  proved token minting, and received `vertex-ok` from
  `google-vertex-anthropic/claude-opus-5@default`. The live guest provider object
  was reconciled without replacing other OpenCode settings; the managed template
  already owns the same object for source convergence.
- The enterprise Compose stack remains healthy after 42 hours with `db`, `redis`,
  `web`, `vite`, and `prefect` running. Containers receive neither the service
  token nor ambient Vertex ADC. OCP-35 and OCP-36 prerequisites merged through
  PRs #25 and #24 before DAI reconciliation. Implementation Gate Commits:
  `747f214`, `6797a49`, `990378e`, `c03ca4b`.
- Independent review added a fail-closed rootless check before update mutates a
  guest; an engine reporting `false` now aborts before config, Git, or chezmoi.
- PR #26 merged the reviewed source as `9056a17`; Python 3.12, 3.13, and 3.14 CI
  passed. Both guest source checkouts converged to that commit and retained
  rootless Podman, Compose v2.40.3, 1Password CLI 2.39.0, and the rendered Vertex
  provider. The development guest completed its
  managed update; the personal guest applied DAI targets but its full command
  later failed in an unrelated Hermes catalog hook whose configured backlog root
  is unavailable. Sixty focused closure tests pass.
- The private project's 14 reference changes resolve through the replacement
  service account but remain uncommitted external drift. Existing `DBX-1` still
  prevents whole-template `op run`; neither item is claimed as DAI source delivery.
- New shells use the replacement Keychain token. The prior automation-only service
  account remains active by operator decision to avoid interrupting in-flight
  cycles and shells; `DAI-028-AR2` requires revocation after their migration and
  prohibits expanding the old account's scope.

## 2026-08-12 - DAI-027 Forced Vertex ADC Renewal

- Passed gcloud's explicit default scopes in both hosted and browser modes, which
  disables its stale account-only cache shortcut while retaining positional
  account validation.
- Kept the dedicated Vertex `CLOUDSDK_CONFIG`, ambient override removal, quota
  project repair, and token proof unchanged; normal gcloud profiles remain outside
  the helper boundary.
- Twelve portability tests and independent review passed. Implementation Gate
  Commit: `e6d2da3`. Release is not applicable; intended Final Push is a feature
  branch and draft pull request into `main`.

## 2026-08-11 - DAI-026 Dual Vertex Reauthentication

- Added `vertex-reauth-browser` for automatic local-browser callback without code
  paste while retaining `vertex-reauth` as hosted code-entry fallback.
- Both commands share isolated ADC, positional account validation, canonical-path
  guard, quota-project repair, and token proof. Unknown modes, extra arguments,
  and flag-like configured accounts fail before gcloud runs.
- Twelve portability tests, rendered wrapper execution, shell syntax, and focused
  review passed. Implementation Gate Commit: `be0748d`. Release is not applicable;
  intended Final Push is a feature branch and draft pull request into `main`.

## 2026-08-11 - DAI-025 Hosted Vertex Reauthentication

- Replaced gcloud's localhost OAuth callback with hosted authorization-code entry,
  preventing stale browser tabs from consuming the callback before Google returns.
- Passed the configured account positionally so gcloud validates the returned
  identity, and rejected noncanonical ADC filenames that gcloud cannot renew.
- Preserved isolated `CLOUDSDK_CONFIG`, ambient credential removal, quota-project
  repair, and access-token proof. Focused rendering, isolation, blank-account,
  canonical-path, shell-syntax, and zero-drift deployment checks passed; 12
  portability tests passed. Deployed only the managed helper locally. Existing ADC
  remains expired until the operator completes hosted reauthentication.
- Implementation Gate Commit: `badf3fe`. Release is not applicable; intended Final
  Push is the feature branch and draft pull request into protected `main`.

## 2026-08-09 - DAI-024 Rootless Podman Atuin

- Added one default-empty machine-local Atuin workspace selector. The selected
  Fedora guest alone receives a private Lima `8889`-to-`8888` forward, pinned
  rootless Podman Quadlet, Linux-native named volume, and closed registration;
  project paths are not mounted into the container.
- Cold-exported the stopped Colima volume to a checksummed 8.7 MiB archive,
  restored it into Podman, corrected imported volume-root ownership, and moved
  the unchanged tailnet HTTPS endpoint to host loopback port `8889`. Host,
  selected-workspace, and client-workspace sync passed with 17,169 encrypted
  history records available to the converged clients; new registration is denied.
- Replaced the initial generated-autostart attempt with a sentinel-guarded
  `limactl --foreground` LaunchAgent because Lima's generated plist omits a
  non-default `LIMA_HOME`. Both Fedora workspaces now restart cleanly with one
  exact sudo grant for Lima's cidata parameter read while every general sudo
  command remains denied.
- Colima, Docker Compose, its stopped named volume, and the final cold archive
  remain rollback assets; the Colima LaunchAgent and VM are stopped. Validation:
  55 focused tests, Python/diff checks, both rendered Lima configurations,
  generated Quadlet units, pinned-image health, closed registration, three-client
  sync, both VM restart paths, external-home guarded startup, and stopped-Colima
  health passed. Implementation Gate Commit: `8e669d5`. Release is not applicable;
  intended Final Push is a feature branch and draft pull request to `main`.

## 2026-08-09 - DAI-023 Conditional Lima Home

- Added default-empty machine-local `lima_home`; absolute opt-in values propagate
  as `LIMA_HOME` to every controller-owned Lima operation while teammate defaults
  remain native.
- Added configured-workspace `start` and `stop` under the existing per-instance
  lifecycle lock. Status now reports allocation and free space from configured,
  inherited, or default effective Lima storage.
- Documented sparse migration and rollback. Deployed the Mac mini value to
  `/Volumes/ext/state/lima`; both configured instances passed live readiness and
  Atuin synchronization.
- Validation: 317 tests passed with one optional Lima skip; focused 51-test
  rendering/controller coverage and independent re-review passed. Gate Commits:
  `4a795ea`, `0ad4653`, `28ad56b`, `a01c4a1`.

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
  request remains the maximum delivery authority. Implementation, one controlled
  all-source lens pass, targeted deployment, and resumed scheduling completed.
- Autonomous/operator authorization is durable in the improvement ledger, and
  pass telemetry is accepted only from a private scope/manifest receipt derived
  by the typed adapter from the actual filtered pages. Autonomous readiness is
  canonical and bound to the exact worker, opportunity, noncritical risk, resolved
  questions, and that worker's immutable successful lens-pass manifest; replay,
  tampering, missing evidence, and critical risk fail closed.
- Scheduler schema 7 binds pending parallel-lens attempts and completed passes to the registered
  OpenCode session, preventing a reused worker ID from inheriting an earlier
  attempt. Existing improvement-ledger schema 3 now migrates to readiness schema
  4 before integrity validation.
- Added read-only `dbsctr-rnd health` output backed by bounded scheduler activity
  counters, so a completed Hermes cron invocation cannot hide repeated no-op,
  pre-launch-failure, or launch-failure outcomes. Health distinguishes its output
  envelope from scheduler-state schema 7 and reports all six configured lenses.
- Hermes configuration now writes `model.default` without replacing the
  provider-bearing model object and verifies both effective values before
  installing schedules.
- Managed OpenCode permissions expose only the DBSCTR worktree root, and typed
  reconciliation accepts an explicit same-repository linked worktree.

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
