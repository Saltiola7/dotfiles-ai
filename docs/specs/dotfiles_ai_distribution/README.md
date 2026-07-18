# dotfiles-ai Distribution

**Status:** DAI-003 autonomous R&D loop implemented and deployed

## Engineering Profile

### Defaults

| Field | Value |
|---|---|
| Deliverable | Public standalone chezmoi source for DBSCTR, OpenCode, Herdr, and opt-in Hermes supervision |
| Languages/frameworks | Go templates, TOML, JSON, Markdown, Python, Bash, launchd plist |
| Modules | Python, Security |
| Runtime/platform support | Apple Silicon macOS; chezmoi; OpenCode; Herdr; Hermes; Python `>=3.12` tests |
| Public compatibility | Stable local TOML keys and managed target paths; sanitized defaults |
| Trust/data classification | Public configuration; credentials and machine identifiers remain local |
| Operational owner | Saltiola7 maintains releases, compatibility, and migration guidance |
| Product Intent | `docs/specs/dotfiles_ai_distribution/PRODUCT.md` |

### DAI-003 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: adds concurrent autonomous review workers, durable private coordination, branch publication, and draft-PR creation |
| Delivery intent | Merge and deploy the capability-first global review-to-draft-PR loop locally |
| Scope | Daily fresh OpenCode workers, atomic improvement claims, Discovery handoff, exact-session recovery, draft-PR delivery, and operator runbook |
| Overrides | Review evidence may come from the global OpenCode database, but public changes target only this source and omit private project provenance; merge, release, and deployment remain human-controlled |

## Bounded Context

`dotfiles_ai_distribution` owns portable defaults, local configuration shape,
rendered target ownership, installation, migration, rollback, release, and
maintenance for the DBSCTR/OpenCode/Herdr workbench.

Adjacent contexts remain authoritative for lifecycle semantics, OpenCode
control-plane behavior, and shell authentication behavior.

## Goals

- Reproduce the maintainer's current working AI development configuration.
- Permit curated machine-local customization without committing it.
- Keep optional 1Password integration fail-open for Herdr startup.
- Transfer managed targets from personal dotfiles without downtime or overlap.
- Provide an opt-in Hermes supervisor that can continue already-authorized
  DBSCTR work while preserving human judgment at Discovery boundaries.
- Turn distinct, sanitized global-session improvement patterns into concurrently
  discoverable changes and human-merge-only draft pull requests for this source.

## Non-goals

- Managing unrelated shell, AWS, editor, Kitty, or personal secret bundles.
- Installing OpenCode, Herdr, 1Password, Graphify, RTK, or provider credentials.
- Treating Hermes, Herdr, or OpenCode status as DBSCTR lifecycle authority.
- Modifying repositories observed in the global OpenCode database; project-level
  patterns may produce only generalized improvements in this source.
- Automatically merging pull requests, releasing artifacts, or deploying changes.
- Managing general repository navigation beyond Hermes's explicit supervision
  allowlist.
- Supporting Linux or Windows in the first release.

## Behavior

### Fresh installation

- Given a developer has a valid local TOML, when the standalone chezmoi source
  renders and applies, then complete OpenCode, DBSCTR, and Herdr targets are
  installed without personal identifiers.

### Credential-neutral Herdr

- Given 1Password is absent or unconfigured, when Herdr and shell startup run,
  then neither blocks or attempts interactive authentication.

### Existing-user cutover

- Given personal dotfiles currently own the targets, when parity validation
  passes and ownership transfers, then live files remain present and exactly
  one chezmoi source owns each target.

### Opt-in Hermes bootstrap

- Given Hermes is enabled in machine-local data and is absent or its launcher
  cannot report a version, when this source applies, then it downloads the
  current official installer to a temporary file, installs noninteractively
  with bundled skills, and preserves Hermes-owned configuration and runtime
  state.
- Given Hermes is disabled, when this source applies, then no installer,
  integration, gateway, schedule, or update job runs.

### Supervised DBSCTR review

- Given the review schedule fires, when Hermes invokes the managed supervisor
  skill, then it explicitly requests one bounded unreviewed page or, when none
  exists, one historical cohort from the global OpenCode database and persists
  review completion before compacting the designated review session.
- Given the designated global review pane has no active Cycle Record, when its
  review snapshot is available, then Hermes may continue that review; active
  Cycle Records remain required for supervised implementation panes.
- Given a resumed idle OpenCode process has not yet emitted its native session
  ID, when exactly one Herdr pane reports foreground argv `opencode -s
  <configured-session>`, then Hermes may adopt that pane; otherwise it pauses
  without guessing from labels, recency, screen content, or directories and
  without invoking review helpers directly.
- Given the designated pane is in Plan, uses a custom Build primary, or its
  primary cannot be verified, when the schedule fires, then Hermes pauses and
  requests one-time `/agents` selection of native Build; it never cycles agents
  with order-dependent keystrokes.
- Given one submitted review reports a blocker or no processed cohort, when
  Hermes observes the final output, then it reports and stops without retrying
  `/dbsctr-review` in that invocation.
- Given the review pane requests permission for `dbsctr_review_complete` or
  `dbsctr_review_history_save`, when the visible default is `Allow once`, then
  Hermes approves once; every other permission or ambiguous screen pauses for
  the user, and `Allow always` is never selected.
- Given an allowlisted Herdr OpenCode pane has an active DBSCTR cycle, when its
  workflow is blocked on an already-authorized lifecycle operation, then Hermes
  may continue it; questions requiring Discovery or new authority pause and are
  reported to the user.
- Given a pane is outside the machine-local repository allowlist, when Hermes
  inventories Herdr, then it does not read, control, or resume that pane.

### Autonomous R&D workers

- Given the daily schedule fires, when the managed improvement workspace is
  healthy, then Hermes starts one unfocused native-Build OpenCode tab with a new
  session even when earlier workers are still active or awaiting Discovery.
- Given the Mac misses one or more daily occurrences, when the Hermes gateway
  resumes, then the recurring schedule produces at most one catch-up worker.
- Given a worker reviews the global OpenCode database, when it selects an
  improvement, then the private ledger atomically claims one sanitized,
  deterministic opportunity identity before Discovery or implementation.
- Given another worker already owns the opportunity or overlapping declared
  scope, when a claim is attempted, then the new worker selects another finding
  without reading private provenance from the existing claim.
- Given all configured local and external research lenses are exhausted without
  a defensible distinct finding, when the worker cannot proceed truthfully, then
  it blocks in Discovery for operator guidance rather than manufacturing one.
- Given Discovery has unresolved material questions, when the worker reaches the
  boundary, then it waits in its own Herdr tab until the operator answers and
  explicitly instructs it to proceed.
- Given the operator authorizes the discovered scope, when required DBSCTR gates
  pass, then the worker pushes only its isolated feature branch and creates a
  draft pull request against the recorded base branch. It never merges, marks the
  pull request ready, releases, or deploys.
- Given a worker pane disappears, when the five-minute watchdog finds its exact
  durable session identity, then Hermes recreates the pane with that session up
  to three times. Ambiguous or exhausted recovery remains claimed and blocked
  until explicit retry or abandonment.
- Given a draft pull request is merged or closed by a human, when the watchdog
  observes its state, then it records that terminal outcome for future dedupe and
  leaves the Herdr tab under manual ownership.

### Latest-track maintenance

- Given Hermes is enabled, when the configured update schedule runs, then the
  managed updater requests a Hermes backup, applies the latest supported update,
  lets Hermes restart running gateways, runs `hermes doctor`, and retains logs.

## Interfaces And Contracts

- Tracked `.chezmoidata.toml` supplies public defaults.
- `config.example.toml` documents the separate local chezmoi config and curated
  `[data.dotfiles_ai]` overrides.
- The actual config lives at `~/.config/dotfiles-ai/chezmoi.toml` with separate
  persistent state.
- `[data.dotfiles_ai.hermes]` selects enablement, executable, non-secret provider
  and model, review workdir, managed workspace label, daily cron, watchdog
  interval, delivery, update calendar, GitHub account, and the single writable
  source repository. Paths and account names remain machine-local.
- The official Hermes installer owns `~/.hermes/hermes-agent`, `bin`, Node,
  Python, virtual environments, sessions, memories, logs, credentials, and
  mutable runtime databases.
- This source may bootstrap missing Hermes configuration and apply targeted
  stable policy, but it does not continuously replace all of
  `~/.hermes/config.yaml`.
- Saved Hermes spawner and watchdog cron IDs are reconciliation identities; a
  stale or ambiguous ID fails closed instead of creating duplicate jobs.
- The private SQLite review ledger owns opportunity, worker, recovery, declared
  scope, and pull-request outcome state. Hermes memory and Herdr labels are never
  coordination authority.
- Draft-PR delivery records the base branch, feature branch, remote push URL,
  configured GitHub account, and returned pull-request identity. Tokens remain in
  the GitHub CLI credential store and never enter config, argv, logs, or reports.
- The supervisor uses Herdr's structured agent inventory and native OpenCode
  session IDs through individual commands without inline shell parsers. DBSCTR
  Cycle Records and review records remain authoritative.
- Private review access remains behind OpenCode's managed `/dbsctr-review`
  command and typed tools; Hermes never calls `dbsctrctl review-*` or reads the
  OpenCode database directly.
- Hermes may approve only operations already authorized by an active DBSCTR
  review or build cycle. Discovery questions, scope expansion, conflicts,
  exceptions, and new external-write authority pause for the user.
- OpenAI Codex OAuth is authenticated through `hermes auth add openai-codex` as
  the gateway's macOS user. OpenCode OAuth files are not copied or reused.
- Cron creation follows noninteractive `hermes config set` of the selected
  provider/model so Hermes records a coherent provider snapshot.
- Public templates contain no usernames, home paths, account IDs, UUIDs,
  credential values, or private repository names.
- Vendor-managed OpenCode plugins remain vendor-managed and are validated, not
  copied.
- Removal from personal source never uses `.chezmoiremove` for transferred live
  targets.

## Validation Strategy

| Authority | Scope |
|---|---|
| `pytest` | DBSCTR, OpenCode, Herdr, auth, and public-safety contracts |
| `chezmoi data/cat/apply --dry-run` | Local data and rendered targets |
| `opencode debug config` | Resolved control plane |
| `bash -n`, `plutil -lint` | Scripts and LaunchAgent |
| Git/content scan | Public identifiers, credentials, and ownership overlap |
| Runtime status | One healthy Herdr server and current OpenCode integration |
| Hermes static contracts | Bootstrap, schedule reconciliation, updater, skill policy, and public-safety tests |
| Hermes runtime | `hermes --version`, `hermes doctor`, gateway status, Herdr integration status, cron status and manual dry-run |

## Risks

- Global target overlap can make apply order silently change configuration.
- LaunchAgent handoff can interrupt persistent Herdr panes.
- Local account identifiers can leak if templates are copied without conversion.
- External plugins can drift independently of this repository.
- The initial current-user Hermes PoC is not sandboxed; a compromised prompt can
  act with the user's rights wherever explicit policy and OS permissions allow.
- Hermes tracks latest upstream releases, so a bad update can interrupt the
  gateway despite backup and health checks.
- Hermes cron CLI output and mutable configuration are upstream contracts that
  may drift; reconciliation fails closed when expected identifiers disappear.
- OpenCode database metadata can include private sessions and credentials;
  review access stays host-side and exposes no raw database to containers or
  other users.

## Operations And Maintenance

- The maintainer owns compatibility with current chezmoi, OpenCode, Herdr, and
  supported Python versions.
- Security and compatibility reports use the repository issue tracker.
- Updates require preview before apply; breaking local-TOML or target ownership
  changes require migration and rollback notes.
- Hermes updates run with backup and health evidence. Rollback uses Hermes's
  retained backup or a reviewed version change; uninstall preserves data unless
  the operator explicitly requests full removal.
- Disable Hermes schedules and gateway supervision before retiring managed
  policy. Never delete Hermes credentials, memories, sessions, or runtime data
  through normal chezmoi retirement.
- LaunchAgent handoff can terminate active panes; capture a Herdr snapshot and
  expect a brief restart even when session restoration succeeds.
- Retirement restores ownership to the prior source before disabling this
  source and booting out its LaunchAgent.
