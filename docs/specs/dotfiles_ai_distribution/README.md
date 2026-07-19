# dotfiles-ai Distribution

**Status:** DAI-005 native OpenCode R&D scheduling deployed

## Engineering Profile

| Field | Value |
|---|---|
| Deliverable | Public standalone chezmoi source for DBSCTR, OpenCode, Herdr, and opt-in native R&D scheduling |
| Languages/frameworks | Go templates, TOML, JSON, Markdown, Python, Bash, launchd plist |
| Modules | Python, Security |
| Runtime/platform support | Apple Silicon macOS; chezmoi; OpenCode; Herdr; launchd; Python `>=3.12` tests |
| Public compatibility | Stable local TOML keys and managed target paths; sanitized defaults |
| Trust/data classification | Public configuration; credentials and machine identifiers remain local |
| Operational owner | Saltiola7 maintains releases, compatibility, and migration guidance |
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
- Supporting Linux or Windows.

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
- Given Discovery has unresolved material questions, then the worker waits in its
  own Herdr tab until the operator answers and explicitly instructs it to proceed.
- Given explicit proceed and passing DBSCTR gates, then the worker pushes only its
  isolated feature branch and creates a draft pull request. It never merges,
  marks ready, releases, or deploys.

### Recovery And Completion

- Given a nonterminal worker's pane disappears, when the watchdog finds no exact
  native session, then it recreates `opencode -s SESSION --agent build` in a new
  single-pane tab and records recovery; three failures leave it blocked.
- Given Herdr omits resumed native session metadata, then only the exact recorded
  pane, workspace, tab, managed cwd, single-pane topology, and foreground argv
  may be adopted. Every ambiguous shape blocks.
- Given a worker is alive and idle, blocked, or awaiting Discovery, then the
  watchdog sends no prompt, answers no question, and selects no permission.
- Given a draft pull request is merged or closed by a human, then the watchdog
  records the terminal outcome and leaves its Herdr tab under manual ownership.

### Approved Future Longitudinal Analytics And Adaptive Cadence

The following behavior and interfaces become current only after DAI-004 is
completed and deployed. DAI-005 remains the current scheduler contract until
then.

- Given retained benchmark windows are incomplete, when analytics runs, then it
  reports `insufficient` and holds cadence rather than extrapolating.
- Given a complete monthly evaluation, cadence may move by at most one step among
  weekly, twice-weekly, and daily. It steps up only with at least two improved
  observed merges, no regressions, and no more than 20 percent failed outcomes;
  it steps down after any regression or at least 50 percent failed outcomes.
- A monthly cohort contains each worker whose first relevant terminal or failure
  event occurred after the prior evaluation cutoff and no later than the current
  cutoff. Precedence is reverted, blocked, abandoned, closed without merge,
  merged with a complete effect, then insufficient. Failed outcomes are reverted,
  blocked, abandoned, and closed without merge; improved, neutral, regressed,
  and failed outcomes form the denominator. Insufficient and still-active work
  are reported but excluded. An empty denominator holds cadence.
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

### Provider-affine Build Agents

- Given the operator selects `build-gpt` or `build-claude`, then the lowercase
  filename-derived ID selects that custom primary exactly. Selecting a model
  alone never changes the active primary agent.
- Given `build-claude` delegates, then only Bedrock `explore-bedrock`,
  `scout-bedrock`, or `builder-bedrock` may run, each on Claude Sonnet 5.
- Given the runtime remains native Plan, then OpenAI Plan permissions and
  subagents remain expected regardless of the model displayed.

## Interfaces And Contracts

- Shared `.chezmoidata.toml` defaults `[dotfiles_ai.rnd].enabled=false`.
- Machine-local `~/.config/dotfiles-ai/chezmoi.toml` may enable scheduling and
  supplies source path, workspace label, daily hour/minute, watchdog interval,
  and non-secret GitHub account/repository.
- `~/.local/bin/dbsctr-rnd` provides only `spawn` and `watchdog`.
- LaunchAgent labels are `dev.dotfiles-ai.dbsctr-spawner` and
  `dev.dotfiles-ai.dbsctr-watchdog`; disabled apply removes only matching labels
  and plists.
- The private SQLite ledger owns opportunities, workers, recovery attempts,
  declared scope, pull-request outcomes, benchmark references, and scheduler
  state. Launchd and Herdr are advisory.
- After DAI-004 deployment, `dbsctr-rnd analytics` returns a bounded human summary
  by default and JSON with an explicit flag. `dbsctr-rnd reset-schedule` is the
  only halt recovery command.
- Scheduler state records the current cadence, last monthly evaluation, outcome
  counters, halt reason, and next eligible spawn time without private provenance.
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
| Runtime probes | LaunchAgent state, one fresh worker, exact registration, no-op healthy watchdog, and retained Discovery boundary |

## Risks And Maintenance

- Current-user OpenCode workers are not sandboxed; explicit policy and OS
  permissions remain the security boundary.
- Herdr JSON and OpenCode session metadata may drift; reconciliation fails closed.
- Local identifiers can leak if templates are copied without conversion.
- Disabling scheduling must preserve OpenCode sessions, ledger records, worktrees,
  claims, and pull requests.
- OpenCode config is loaded once; agent-ID changes require an OpenCode restart.
- Retirement removes Hermes jobs, gateway, executable, credentials, and runtime
  data only under this cycle's explicit destructive authorization.
