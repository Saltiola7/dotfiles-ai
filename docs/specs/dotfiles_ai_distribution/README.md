# dotfiles-ai Distribution

**Status:** DAI-011 federated R&D reliability deployed

## Engineering Profile

| Field | Value |
|---|---|
| Deliverable | Public standalone chezmoi source for DBSCTR, OpenCode, Herdr, and opt-in native R&D scheduling |
| Languages/frameworks | Go templates, TOML, JSON, Markdown, Python, Bash, launchd plist |
| Modules | Python, Security, Cloud |
| Runtime/platform support | Apple Silicon macOS host; Fedora 44 aarch64 Lima guests on VZ; chezmoi; OpenCode; Herdr; launchd; Python `>=3.12` tests |
| Public compatibility | Stable local TOML keys and managed target paths; sanitized defaults |
| Trust/data classification | Public configuration; credentials and machine identifiers remain local |
| Operational owner | Project maintainers own releases, compatibility, and migration guidance |
| Product Intent | `docs/specs/dotfiles_ai_distribution/PRODUCT.md` |

### DAI-005 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: replaces a live autonomous supervisor and permanently retires its runtime |
| Delivery intent | Deploy native launchd/OpenCode automation locally after affected gates pass |
| Scope | Opt-in scheduling, fresh worker spawning, exact-session recovery, provider-affine Build identities, Hermes retirement, and operator guidance |
| Overrides | Shared scheduling defaults remain disabled; this machine enables them locally; merge, release, and deployment remain human-controlled |

### DAI-004 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: private analytics automatically controls local worker cadence |
| Delivery intent | Merge and deploy analytics, scheduler state, runner behavior, and operator commands locally |
| Scope | CLI/JSON effect summaries, monthly cadence ladder, concurrency cap, safety halt, and manual reset |
| Overrides | User TOML remains unchanged; cost is report-only; ordinary workers retain draft-only delivery and human Discovery |

### DAI-006 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: changes recovery and health behavior for live autonomous workers |
| Delivery intent | Deploy the corrected runner locally after affected gates pass |
| Scope | Large-session recovery readiness, watchdog exit health, operator guidance, and one blocked-worker recovery |
| Overrides | Session identity remains exact; recovery may not weaken ambiguity rejection or inject a prompt |

### DAI-007 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: creates filesystem and credential boundaries around unrestricted AI execution and migrates live repository paths |
| Delivery intent | Merge and deploy two local Fedora Lima client environments, host controls, and federated R&D transport |
| Scope | Two locally named VM profiles, VM Herdr, always-auto OpenCode, explicit mounts, protected submodules, host review federation, and configured implementation handoff |
| Overrides | Host OpenCode, Herdr, database, scheduling, and private ledger remain authoritative; VM credentials and databases remain isolated; egress is unrestricted by accepted design |

### DAI-008 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: migrates public configuration and VM filesystem security contracts |
| Delivery intent | Deploy dynamic local workspace configuration after all gates pass |
| Scope | Arbitrary workspace names, mount mappings and access, optional Git protection and references, dynamic federation, and configured Build handoff |
| Overrides | Existing instance names and paths remain machine-local; schema version 2 intentionally replaces fixed keys without compatibility aliases |

### DAI-009 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: extends the public machine-local workspace schema and manages executable command aliases |
| Delivery intent | Deploy dynamic workspace shell aliases locally after all gates pass |
| Scope | Optional per-workspace shell aliases, safe command reconciliation, invocation routing, tests, and operator guidance |
| Overrides | Alias names remain machine-local; existing files are never overwritten; schema version 3 replaces generated version 2 configuration on apply |

### DAI-010 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: changes interactive guest startup and the OpenCode UI loaded by running sandbox environments |
| Delivery intent | Deploy portable terminal and OpenCode visual parity to every configured workspace |
| Scope | Explicit OpenCode theme, checksum-pinned Starship, guest-only Bash startup, personal Starship configuration, tests, and operator guidance |
| Overrides | Visual and startup parity is portable; macOS paths, Homebrew integrations, credentials, and workstation-only shell plugins remain host-only |

### DAI-011 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: changes the live autonomous review data path and private history evidence retained on three runtimes |
| Delivery intent | Deploy reliable federated review and prove one controlled scheduled worker locally |
| Scope | Concurrent source capture, capture-backed continuation, typed-tool runtime normalization, regression coverage, live three-source validation, and explicit worker cleanup |
| Overrides | Federation has no aggregate adapter timeout; each source command retains its 120-second deadline and output bound; launch, Discovery, and delivery authority remain unchanged |

### DAI-013 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: changes interactive shell history and deploys a network-synchronized client to every managed guest |
| Delivery intent | Deploy durable Atuin history to every configured Lima workspace |
| Scope | Checksum-pinned Atuin installation, guest-only non-secret configuration, Bash initialization, tests, and live personal/mgm validation |
| Overrides | Login and encryption keys remain local to each VM; one login is required after creating or rebuilding a VM |

### Provider-Native Evaluation Initiative Overrides

| Field | Value |
|---|---|
| Risk | Elevated: persists new private cross-source cycle projections and evaluates provider harness outcomes |
| Delivery intent | Define contracts on deployed DAI-011 commit `c24f7e5`; implement only after lifecycle and control-plane identity contracts pass |
| Scope | Existing weekly worker, immutable source captures, dedicated five-cycle report persistence, replay, retention, and operational evidence |
| Overrides | Keep weekly unhalted cadence; no second scheduler, source rescan, host-history cohort save, automatic tuning, or guest-to-host PR outcome bridge |

## Bounded Context

`dotfiles_ai_distribution` owns portable defaults, local configuration shape,
rendered targets, installation, migration, rollback, and maintenance for the
DBSCTR/OpenCode/Herdr workbench. Adjacent contexts own lifecycle semantics,
OpenCode control-plane behavior, and shell authentication.

## Goals

- Reproduce the maintainer's working AI development configuration without
  committing machine-local identifiers or secrets.
- Keep optional 1Password integration fail-open for Herdr startup.
- Provide machine-local opt-in daily OpenCode R&D workers with deterministic
  launchd scheduling and recovery.
- Review sanitized global history, pause for human Discovery, and create only
  human-merge draft pull requests for this source.

## Non-goals

- Installing OpenCode, Herdr, provider credentials, or unrelated developer tools.
- Treating launchd, Herdr, or OpenCode status as DBSCTR lifecycle authority.
- Modifying repositories observed in global OpenCode history.
- Automatically answering Discovery, merging, marking ready, releasing, or deploying.
- Supporting Windows.
- Supporting Linux as a general-purpose host; Fedora is supported only as the
  managed Lima guest runtime.

## Behavior

### Installation And Opt-in Scheduling

- Given a valid local TOML, when the source renders and applies, then complete
  OpenCode, DBSCTR, and Herdr targets contain no personal identifiers.
- Given `[data.dotfiles_ai.rnd].enabled=false`, when the source applies, then no
  R&D LaunchAgent is managed or loaded; exact previously managed jobs are safely
  booted out without affecting OpenCode tabs or durable worker state.
- Given scheduling is enabled with valid source, GitHub, hour, minute, and
  interval values, when the source applies, then launchd loads one daily spawner
  and one interval watchdog in the Aqua session.
- Given the Mac sleeps through daily occurrences, when it wakes, then launchd
  coalesces missed calendar events into at most one delayed invocation.

### Autonomous R&D Worker

- Given the daily schedule fires, when `dbsctr-rnd spawn` runs, then it creates
  or reuses exactly one configured Herdr workspace, starts native Build with
  `/dbsctr-improve` in a disposable staging tab, moves only the returned agent
  pane into a dedicated single-pane tab, and registers its exact native session.
- Given earlier workers are active or awaiting Discovery, when the schedule
  fires, then one additional fresh worker still starts.
- Given launch or identity is ambiguous, then spawning fails closed, closes only
  an unchanged shell-only staging tab, and never starts a substitute worker.
- Given a worker applies a named lens, then it scans every matching history page,
  including reviewed sessions, saves sanitized cohorts without changing markers,
  ranks concrete findings, claims one distinct proposal, and presents plain-
  language evidence before Discovery.
- Given a worker starts one federated lens pass, then each available source scans
  its database exactly once into a private immutable capture and every continuation
  reads that capture without rescanning live history.
- The host capture excludes the active worker session and message family before
  persistence, so an autonomous review never reviews or invalidates itself.
- Given host and multiple federated workspaces are available, then their bounded
  capture commands run concurrently while the returned manifest remains in configured
  source order. One slow or invalid source cannot erase another source's result.
- Given a workspace may be stopped, then collection holds one owner-validated
  per-instance lifecycle lock, rechecks its current state, and restores only an
  instance that this collection started. Transitional states fail closed.
- Given a valid source takes longer than the generic analytics deadline, then the
  typed federation call waits for its source-bounded command instead of killing the
  aggregate operation. Per-command time and output bounds remain enforced.
- Given Discovery has unresolved material questions, then the worker waits in its
  own Herdr tab until the operator answers and explicitly instructs it to proceed.
- Given explicit proceed and passing DBSCTR gates, then the worker pushes only its
  isolated feature branch and creates a draft pull request. It never merges,
  marks ready, releases, or deploys.

### Recovery And Completion

- Given a nonterminal worker's pane disappears, when the watchdog finds no exact
  native session, then it recreates `opencode --mini WORKDIR -s SESSION --agent
  build --no-replay` in a new single-pane tab, allows up to 120 seconds for
  large-session readiness, and records only exact identity; three failures leave
  it blocked.
- Given Herdr omits resumed native session metadata, then only the exact recorded
  pane, workspace, tab, managed cwd, single-pane topology, and foreground argv
  may be adopted. Every ambiguous shape blocks.
- Given a worker is alive and idle, blocked, or awaiting Discovery, then the
  watchdog sends no prompt, answers no question, and selects no permission.
- Given watchdog reconciliation reports a recovery failure, ambiguity, unknown
  state, pull-request check failure, or exhausted blocked worker, then it emits
  bounded JSON diagnostics and exits nonzero so launchd health reflects the
  degraded loop. Empty and successful-recovery runs exit zero.
- Every external watchdog and spawner dependency command has a 180-second
  deadline; expiry becomes a bounded runtime failure instead of retaining the
  reconciliation lock indefinitely.
- Given a draft pull request is merged or closed by a human, then the watchdog
  records the terminal outcome and leaves its Herdr tab under manual ownership.

### Longitudinal Analytics And Adaptive Cadence

- Given retained benchmark windows are incomplete, when analytics runs, then it
  reports `insufficient` and holds cadence rather than extrapolating.
- Given a complete monthly evaluation, cadence may move by at most one step among
  weekly, twice-weekly, and daily. It steps up only with at least two improved
  observed merges, no regressions, and no more than 20 percent failed outcomes;
  it steps down after any regression or at least 50 percent failed outcomes.
- Immutable merge and activation events are benchmark inputs, not cadence
  outcomes. After an activated merge's 30-day window closes, the ledger appends
  exactly one `effect_finalized` event keyed by attempt identity, benchmark
  definition version, and activation identity. It references its merge event and
  records improved, neutral, regressed, or insufficient without rewriting prior
  evidence. A uniqueness constraint prevents duplicate finalization.
- A monthly cohort contains each immutable failed or `effect_finalized` outcome
  event recorded after the prior evaluation cutoff and no later than the current
  cutoff, ordered by recorded time then opaque event ID. Failed outcomes are
  reverted, blocked, abandoned, and closed without merge; improved, neutral,
  regressed, and failed outcomes form the denominator. Insufficient, pending
  merges, and still-active work are reported but excluded. An empty denominator
  holds cadence. A blocked event remains a historical failure; explicit retry
  starts a new attempt identity, whose later finalized effect is distinct and
  never rewrites the prior monthly decision.
- Given three consecutive blocked, abandoned, or reverted outcomes or malformed
  authoritative state, spawning enters a persistent fail-closed halt. Only an
  explicit operator reset can resume it. Given three existing nonterminal
  workers, the current spawn is a bounded no-op without setting that persistent
  halt. Worker count validation and spawn reservation occur in one SQLite
  transaction so concurrent ticks cannot admit a fourth worker.
- Given launchd invokes the fixed daily tick, the runner consults private
  scheduler state and either starts one worker or returns a bounded no-op reason.
  It never rewrites machine-local TOML or reloads launchd to tune cadence.
- Given authoritative cost exists, analytics reports it. Cost and missing cost
  never change cadence, halt spawning, or weaken another safety rule.
- Given an ordinary R&D worker passes every DBSCTR gate, it still creates only a
  draft pull request. Adaptive scheduling never grants merge, release, deploy,
  Discovery-answering, or permission-selection authority.

### Provider-Native Five-Cycle Evaluation

- Given one weekly federated worker has captured each source once, when it finds
  five unused completed cycles eligible under one exact harness identity and
  rubric version, then it atomically saves one private report before transient
  source captures expire.
- One eligible member has structured source and cycle IDs, exact root-session
  correlation, one primary provider/model/agent/core/overlay identity,
  same-provider children, and available required metrics. Members are selected by
  completion time then cycle ID; context, risk, delivery, and child-agent
  distributions are recorded as confounders.
- Given a report is saved, then replay reads only its immutable member projections,
  source/capture/page/member digests, aggregates, availability, confounders, and
  recommendations. It never rescans a live database or depends on retained
  transient captures.
- Given two workers attempt the same eligible cohort, then the private writer lock
  derives one canonical report identity before considering prose. The winner
  commits once; the loser returns the existing report and does not select another
  cohort in that invocation.
- Given a source's `privacy_epoch_digest` changes after privacy forget, then the next
  available federated maintenance pass conservatively deletes every host report
  containing that source, its no-reuse rows, and affected backups before saving
  new evaluation. Explicit report forget provides immediate host-side deletion.
- Given a source is unavailable or its privacy epoch has not been revalidated
  within eight days, then every report containing that source is quarantined and
  replay fails closed. Revalidating the same digest restores replay; a changed
  digest deletes affected report and backup state transactionally.
- Given fewer than five eligible unused cycles exist, then the worker reports the
  count and waits for the next normal weekly run. It does not spawn another worker,
  change cadence, halt scheduling, or loosen eligibility.
- A report may recommend a prompt, model, agent, routing, or lifecycle change but
  cannot claim, implement, deploy, or schedule that change. A separate approved
  DBSCTR cycle remains required.

### Provider-affine Build Agents

- Given the operator selects `build-gpt` or `build-claude`, then the lowercase
  filename-derived ID selects that custom primary exactly. Selecting a model
  alone never changes the active primary agent.
- Given `build-claude` delegates, then only Bedrock `explore-bedrock`,
  `scout-bedrock`, or `builder-bedrock` may run, each on Claude Sonnet 5.
- Given the runtime remains native Plan, then OpenAI Plan permissions and
  subagents remain expected regardless of the model displayed.

### Dynamic VM Workspaces

- Given any locally named workspace, when Lima starts its configured instance,
  then Fedora 44 runs natively through VZ with a sparse disk and exposes only
  that workspace's declared host-to-guest mappings.
- Given a configured mount, its whole directory is read-only or writable as
  declared. A writable Git mount with `protect_git_submodules=true` keeps every
  declared submodule worktree and Git metadata directory root-mounted read-only
  before OpenCode may start.
- Given a protected submodule manifest is stale, a read-only overlay is absent,
  or unrestricted passwordless sudo is available, then sandbox startup fails
  closed before an auto-approved agent runs.
- The dedicated guest agent account cannot execute `/usr/bin/sudo`; root-owned
  provisioning remains the only privileged mutation path.
- Given the operator detaches, then VM Herdr keeps panes running. Given a clean
  VM stop and restart, then VM Herdr restores layout and resumes the exact
  OpenCode session with auto-approval still effective.
- Given a VM is dedicated to sandboxed agents, then every VM OpenCode session
  auto-approves permissions not explicitly denied. Host OpenCode behavior is
  unchanged.
- On every guest boot, a root oneshot waits for the declared virtiofs mounts,
  reapplies configured read-only overlays, verifies effective sudo denial, and only then
  publishes the boot-scoped readiness marker required by OpenCode.
- Given a workspace declares a shell alias, when chezmoi applies the host
  configuration, then that command enters the configured workspace exactly as
  `sandbox-vm shell WORKSPACE` and preserves additional arguments.
- Given an alias is removed or renamed, when chezmoi reapplies, then only an old
  managed symlink still targeting `sandbox-vm` is removed. An existing unmanaged
  command blocks apply rather than being overwritten.
- Given a guest applies the managed source, then its Bash login shell initializes
  the same Starship prompt configuration as the personal dotfiles and OpenCode's
  supported TUI configuration selects the configured theme.
- Given any configured Lima guest applies the managed source, then Atuin is
  installed from a checksum-pinned release, Bash records history through Atuin,
  and `Ctrl-R` opens Atuin search against the configured HTTPS sync service.
- Given a guest has logged in once, when later updates reapply the source, then
  its VM-local login and encryption keys remain untouched and automatic sync
  continues every ten minutes. A new or rebuilt VM remains usable locally and
  requires an explicit per-VM login before remote sync succeeds.
- Given the same source applies on macOS, then guest shell targets remain ignored
  so the personal chezmoi source retains sole ownership of host terminal files
  and Atuin configuration.

### Federated Host R&D

- Given host R&D reviews history, then it scans the host database locally and
  invokes exporters inside federated workspaces concurrently with at most four
  bounded source tasks.
  Database files, transcripts, paths, secrets, and credentials never cross the
  VM boundary.
- Given a VM was stopped before collection, then the host may start it for the
  export and restores its prior stopped state afterward. A running VM remains
  running.
- Given evidence from multiple runtimes, then source IDs namespace opaque
  identities and each source retains independent snapshot, ceiling, database,
  and exclusion digests. Missing or malformed sources make the review explicitly
  incomplete rather than silently local-only.
- Given a federated continuation, then its source state binds the immutable capture
  ID, normalized query, source database identity, and next cursor. Changed capture,
  query, database, or page identity fails closed.
- Given Discovery is approved explicitly, then host R&D records one sanitized
  handoff and launches a visible Build session in the configured workspace Herdr. That VM's
  guest-owned `dotfiles-ai` clone owns the DBSCTR cycle, validation, branch, and
  draft pull request; observed projects remain read-only evidence sources.

## Interfaces And Contracts

- Shared `.chezmoidata.toml` defaults `[dotfiles_ai.rnd].enabled=false`.
- `[dotfiles_ai.sandbox]` contains `enabled`, `build_workspace`, resource
  ceilings, and an ordered `workspaces` list. Each workspace contains a unique
  `name`, unique `instance`, optional unique `shell_alias`, `federate`, and one or more mount mappings with
  `host`, `guest`, `writable`, `protect_git_submodules`, and optional reference
  metadata plus an optional relative reference subpath. Shared workspaces are
  empty and management is disabled.
- Shared defaults disable Lima management. Machine-local sandbox data declares
  instance names, host mount roots, protected repository and submodule manifest,
  resource ceilings, and repository-scoped identities without credentials.
- `sandbox-vm shell WORKSPACE` enters the selected VM; ordinary guest `herdr`
  and `opencode` commands retain their native names. `sandbox-vm status|update` owns bounded
  host-to-VM operations; unknown instances and undeclared paths fail closed.
- VM updates pull the guest-owned `dotfiles-ai` source with `--ff-only`, apply
  Linux-compatible targets idempotently, and report that existing OpenCode
  processes retain their loaded config.
- Linux guests manage `.bashrc`, `.bash_profile`, `.common_profile`,
  `.config/starship.toml`, and non-secret `.config/atuin/config.toml`; macOS
  ignores those targets. Starship `1.26.0` and Atuin `18.17.1` are installed
  from checksum-pinned aarch64 Linux releases.
- `[dotfiles_ai.atuin].sync_address` is a machine-local HTTPS base URL propagated
  to every workspace. Authentication, session, and encryption material is never
  rendered, copied between trust boundaries, or committed.
- `[dotfiles_ai.opencode].theme` renders into OpenCode's supported
  `~/.config/opencode/tui.json` and is propagated to guest Herdr visual
  configuration. Runtime KV state remains OpenCode-owned.
- `sandbox-vm review` accepts the bounded history filters plus limit, cursor,
  and typed continuation state. It returns schema version `2`, an
  ordered `sources` array, and one `manifest_digest`. Each source contains only
  `source_id`, `availability`, and either the existing sanitized history page or
  one bounded error class. Continuations submit each source's original snapshot,
  ceilings, database digest, exclusion digest, query digest, and capture ID. The manifest
  digest binds the ordered source envelopes and normalized requested filters.
- Initial source collection invokes `dbsctrctl review-history --capture` once.
  Later pages invoke the same interface with only `--capture-id`, limit, and
  cursor. Empty databases remain available sources with an immutable empty capture.
  These explicitly mutating private captures are tagged `federated`; unreferenced
  captures older than 24 hours are pruned when the next capture is created.
- The typed federation adapter retains the 256 KiB aggregate output bound but has
  no aggregate wall-clock timeout. `sandbox-vm` retains a 120-second deadline for
  each host or guest exporter and bounds concurrent source work to four tasks.
  The typed adapter reads the managed sandbox config independently and rejects a
  helper manifest whose source membership or order differs from configured federation.
- Deployment cannot claim federated R&D operational from unit tests or a direct
  helper call alone. The live gate must invoke the installed typed adapter, read
  host and every configured federated workspace through all continuations, verify
  stable source identities, then launch one controlled R&D worker, observe its
  complete-history phase, and explicitly abandon, forget, and close its test tab.
- Typed `dbsctr_vm_handoff` accepts schema version `1`, host claim identity,
  approved context, risk, affected repository-relative paths, validation, and
  explicit `proceed=true`. It asks before directly invoking fixed Lima and Herdr
  argument vectors; the general `sandbox-vm` CLI exposes no handoff command.
  Text fields use fixed size and unsafe-content bounds. It returns only the target
  source, Herdr presentation IDs, OpenCode session ID when available, and launch
  status.
- `sandbox-vm shell` resolves only configured workspace instances and preserves
  argument boundaries. Invoking `sandbox-vm` through a configured alias resolves
  that alias to one workspace and follows the same shell path. Alias values must
  be unique command-safe identifiers, cannot shadow `sandbox-vm`, and remain
  machine-local.
- Chezmoi reconciles alias symlinks under `~/.local/bin` from a private manifest.
  It never replaces an unmanaged path and removes a stale path only when it is
  still a symlink to the managed `sandbox-vm` executable.
- Machine-local `~/.config/dotfiles-ai/chezmoi.toml` may enable scheduling and
  supplies source path, workspace label, daily hour/minute, watchdog interval,
  and non-secret GitHub account/repository.
- `~/.local/bin/dbsctr-rnd` provides `spawn`, `watchdog`, `analytics`, and
  `reset-schedule`. `analytics --json` returns the bounded structured report;
  human output is the default. `--finalize-json` binds one retained benchmark to
  its merged attempt, while `--failure-json` accepts only an outcome matching the
  authoritative worker state (including a reverted merged attempt).
- Read-only typed `dbsctr_provider_evaluation` lists bounded report summaries or
  replays one exact report ID. Write-capable
  `dbsctr_provider_evaluation_save` accepts a rubric version, validated federated
  manifest digest, and bounded findings/recommendations; it asks the helper to
  resolve the private terminal receipt, derive, and atomically persist the cohort.
  It accepts no caller member list, metrics, or aggregates and remains denied to
  read-only and Builder subagents.
- `dbsctrctl provider-evaluation-save` and `provider-evaluation` are the helper
  authorities beneath those tools. Save executes under the existing private
  writer lock; ordinary reads never initialize, repair, or migrate state.
- `dbsctr-rnd watchdog` always emits its bounded JSON result. It exits nonzero
  when any event is degraded and zero when reconciliation is healthy or another
  watchdog already owns the lock.
- LaunchAgent labels are `dev.dotfiles-ai.dbsctr-spawner` and
  `dev.dotfiles-ai.dbsctr-watchdog`; disabled apply removes only matching labels
  and plists.
- The DBSCTR private ledger owns opportunities, workers, recovery attempts,
  declared scope, pull-request outcomes, captures, and benchmark references. A
  separate mode-`0600` private scheduler SQLite ledger owns only reservations,
  sanitized outcome references, and cadence state. Launchd and Herdr are advisory.
- The DBSCTR private ledger adds separately versioned
  `provider_evaluation_reports`, `provider_evaluation_members`,
  `provider_evaluation_receipts`, and `provider_evaluation_sources` storage rather
  than reusing host-only `history_reports`. One transaction writes exactly five
  ordered member projections and their report, or none.
- Provider evaluation report schema `1` contains rubric name/version/digest, exact
  harness identity, ordered structured `source_id`/`cycle_id` members, completion
  time, telemetry and gate digests, ordered source capture/page/member digests,
  aggregates, per-field availability, confounders, findings, recommendations, and
  creation time. It contains no account/user role, email, client label, prompt,
  transcript, command argument, error message, URL, credential, or path.
- Rubric version `1` requires exact harness activation identity, exact root-cycle
  correlation, completion time, elapsed time, gate failure count, gate reopening
  count, and remediation-round count. Tool/error/delegation/provider-error/
  approval/retry/token/cost metrics are optional with explicit availability.
- Report identity hashes rubric version, exact harness identity, and ordered
  members. A uniqueness constraint prevents one cycle from appearing in another
  report under the same rubric and harness identity. Repeated save is idempotent;
  a changed payload under the same identity fails closed.
- The distribution-owned save interface accepts rubric identity and bounded
  findings/recommendations plus the final manifest digest, not members or
  aggregates. The typed adapter records a transient terminal receipt keyed by
  that digest from the first schema-v2 response, including single-page responses
  whose continuation state is null. Save completes any unseen pages from the
  immutable captures, validates source order and every
  manifest/page/member digest, derives eligible members and aggregates, and then
  writes under the private lock. Incomplete, expired, changed, or caller-shaped
  evidence fails without persistence.
- Report replay validates the stored payload and member projection without the
  live OpenCode databases or source captures. Backup, restore, semantic integrity,
  and explicit forget include the new report tables transactionally.
- `dbsctrctl review-privacy-epoch` returns one digest derived only from durable
  local forget/tombstone state. The terminal receipt records it at capture
  completion and revalidates it before save without rescanning the OpenCode
  database. Capture `exclusion_digest` remains
  worker-specific self-exclusion identity and never controls report deletion.
- Reports store each source privacy epoch digest. Changed-digest maintenance removes
  every report containing that source and purges affected backups; no-reuse rows
  are removed because source-local suppression prevents the forgotten cycle from
  reappearing. If the source is unavailable, propagation remains pending and is
  reported rather than guessed complete.
- Source-verification rows record only source ID, privacy epoch digest, availability,
  and verification time. Unavailable or older-than-eight-day state quarantines
  related reports at read time; replay never claims privacy currency from an
  expired source check.
- `dbsctr-rnd reset-schedule` is the only halt recovery command; it preserves
  outcome history and cadence while clearing the halt, stale reservations, and
  next-eligible cutoff.
- Scheduler state records the current cadence, last
  monthly evaluation, immutable outcome-event cutoff and counters, attempt/event
  identities, halt reason, and next eligible spawn time without private
  provenance.
- Commands use argument vectors and structured JSON. The runner never reads the
  OpenCode database or calls private review helpers directly.
- GitHub tokens stay in the `gh` credential store and enter only a child process
  environment for PR status checks.
- Public templates contain no usernames, home paths, account IDs, credentials,
  private repository names, or traceable review provenance.

## Validation Strategy

| Authority | Scope |
|---|---|
| `pytest` | DBSCTR, OpenCode, R&D runner, Herdr, auth, and public-safety contracts |
| `chezmoi data/cat/apply --dry-run` | Enabled/disabled local data and rendered targets |
| `opencode debug config/agent` | Exact primary IDs, models, permissions, and provider-local routes |
| `python -m py_compile`, `bash -n`, `plutil -lint` | Runner, loader, and LaunchAgents |
| Runtime probes | LaunchAgent state and exit status, large-session exact recovery, one fresh worker, exact registration, no-op healthy watchdog, and retained Discovery boundary |

## Risks And Maintenance

- Current-user OpenCode workers are not sandboxed; explicit policy and OS
  permissions remain the security boundary.
- Writable mounts intentionally expose their declared client source trees to
  deletion or corruption by VM agents. Unmounted host paths remain inaccessible.
- VM agents may use unrestricted network egress and every credential supplied to
  that VM. Repository-scoped credentials are the normal remote-write boundary.
- Accepted risk `DAI-007-AR1`: a configured workspace provider credential can
  write every repository authorized by that provider account rather than only
  its intended mounted repository. The operator owns and approved this exception;
  VM isolation, denied sudo, protected read-only mounts, and provider-side
  repository authorization are compensating controls. Review by 2026-08-18 or
  before credential rotation, whichever comes first; replace it with a
  repository-scoped credential when available.
- Sparse VM disks consume host storage on demand and never shrink automatically;
  status and update operations must report host and instance allocation.
- Read-only submodule overlays on virtiofs are trusted only after runtime tests
  prove mount ordering, alternate-path resistance, denied writes, and persistence
  across reboot. Failure blocks auto mode.
- Herdr JSON and OpenCode session metadata may drift; reconciliation fails closed.
- Local identifiers can leak if templates are copied without conversion.
- Disabling scheduling must preserve OpenCode sessions, ledger records, worktrees,
  claims, and pull requests.
- OpenCode config is loaded once; agent-ID changes require an OpenCode restart.
- Exact host shell replication is unsupported because workstation-only package,
  credential, and macOS path integrations do not belong inside isolated guests.
- Retirement removes Hermes jobs, gateway, executable, credentials, and runtime
  data only under this cycle's explicit destructive authorization.
