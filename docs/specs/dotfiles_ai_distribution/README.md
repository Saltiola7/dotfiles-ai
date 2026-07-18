# dotfiles-ai Distribution

**Status:** DAI-002 Hermes supervisor PoC in progress

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

### DAI-002 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: installs a mutable external agent runtime and grants it control of current-user Herdr/OpenCode sessions |
| Delivery intent | Merge and deploy the opt-in Hermes bootstrap, gateway, supervision policy, schedules, and tests locally |
| Scope | Latest supported Hermes installer, machine-local allowlist and schedules, one global review cohort per run, active DBSCTR session babysitting |
| Overrides | Local-user PoC is intentionally unsandboxed; pause for Discovery questions; no autonomous merge, arbitrary repository mutation, or draft-PR delivery in this cycle |

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

## Non-goals

- Managing unrelated shell, AWS, editor, Kitty, or personal secret bundles.
- Installing OpenCode, Herdr, 1Password, Graphify, RTK, or provider credentials.
- Treating Hermes, Herdr, or OpenCode status as DBSCTR lifecycle authority.
- Automatically implementing review findings or publishing draft pull requests
  before those DBSCTR delivery contracts are implemented.
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

- Given Hermes is enabled in machine-local data and is absent, when this source
  applies, then it downloads the current official installer to a temporary file,
  installs noninteractively with bundled skills, and preserves Hermes-owned
  configuration and runtime state.
- Given Hermes is disabled, when this source applies, then no installer,
  integration, gateway, schedule, or update job runs.

### Supervised DBSCTR review

- Given the review schedule fires, when Hermes invokes the managed supervisor
  skill, then it processes one bounded unreviewed page or one historical cohort
  from the global OpenCode database and persists review completion before
  compacting the designated review session.
- Given the exact configured Herdr review tab is absent, ambiguous, or lacks a
  native OpenCode session ID, when the schedule fires, then Hermes pauses and
  reports the missing prerequisite without invoking review helpers or the
  OpenCode database directly.
- Given the designated pane is in Plan or its primary cannot be verified, when
  the schedule fires, then Hermes pauses and requests one-time `/agents`
  selection of a Build primary; it never cycles agents with order-dependent
  keystrokes.
- Given one submitted review reports a blocker or no processed cohort, when
  Hermes observes the final output, then it reports and stops without retrying
  `/dbsctr-review` in that invocation.
- Given an allowlisted Herdr OpenCode pane has an active DBSCTR cycle, when its
  workflow is blocked on an already-authorized lifecycle operation, then Hermes
  may continue it; questions requiring Discovery or new authority pause and are
  reported to the user.
- Given a pane is outside the machine-local repository allowlist, when Hermes
  inventories Herdr, then it does not read, control, or resume that pane.

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
  and model, review workdir, cron, delivery, update calendar, and an explicit
  logical-name/path repository allowlist. Paths remain machine-local.
- The official Hermes installer owns `~/.hermes/hermes-agent`, `bin`, Node,
  Python, virtual environments, sessions, memories, logs, credentials, and
  mutable runtime databases.
- This source may bootstrap missing Hermes configuration and apply targeted
  stable policy, but it does not continuously replace all of
  `~/.hermes/config.yaml`.
- One saved Hermes cron job ID is the reconciliation identity; a stale or
  ambiguous ID fails closed instead of creating a duplicate review job.
- The supervisor uses Herdr's structured agent inventory and native OpenCode
  session IDs. DBSCTR Cycle Records and review records remain authoritative.
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
