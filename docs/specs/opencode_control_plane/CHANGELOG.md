# OpenCode Control Plane Changelog

## 2026-08-22 - OCP-37 GPT-5.6 Fast Routing

- Routed native Plan and Build, `build-gpt`, Reviewer, and `/dbsctr-gpt` to Sol
  Fast; Explore and disposable small-model work to Luna Fast; and Scout and
  Builder to Terra Fast. Existing reasoning efforts and provider affinity remain
  unchanged.
- Red/green routing checks and 53 affected tests passed with Git whitespace
  validation. A targeted managed deployment preserved unrelated host state, and
  a fresh OpenCode process resolved every exact Fast identity and effort. Current
  OpenCode processes require one normal restart. Fast priority processing uses
  twice the published standard token rates; fallback cost-card estimates do not
  yet cover Fast IDs. Gate Commit: `d49c9b4`. Gate Exceptions: none. Intended
  Final Push: feature branch and draft pull request into protected `main`.

## 2026-08-18 - PM Kernel Commands

- Migrated control-plane work records to canonical tickets and deployed
  provider-neutral `/pm-kernel`, `/backlog-migration`, and `/sprint-review`
  commands without granting live Jira mutation.

Historical `Intended Final Push` values record the policy at the time. Current
delivery requires a feature branch and verified draft pull request into protected
`main`.

## 2026-08-15 - OCP-36 Official 1Password MCP

- Added the desktop-bundled 1Password MCP to managed macOS OpenCode config using
  the pinned absolute command `/usr/local/bin/1password-mcp`; Fedora guests remain
  excluded because they lack the desktop approval boundary.
- Documented the Environment-only capability and security boundary: desktop
  approval remains authoritative, secret values are not returned, and Password
  Manager vault/item or service-account administration remains outside this MCP.
- Independent review restricted all `1password_*` tools globally and added the
  sole primary Build override as `ask`; guest-branch exclusion is covered by a
  focused template test. The command claim is limited to absolute launcher-path
  pinning because macOS denied direct provenance inspection of the root-owned
  link.
- Deployed only the MCP object to the live config, preserving unmerged OCP-35
  permissions. A fresh OpenCode process resolved the exact command and reported
  both `context7` and `1password` connected; 47 affected tests passed. A fresh
  read-only Environment probe discovered the official documentation, completed
  desktop authentication, and listed Environments successfully; none currently
  exist. No secret values were requested and no mutation occurred. The current
  interactive process requires one normal restart to load the added tool schema.
  Implementation Gate Commits: `ca24f64`, `e24d12d`, `9e7178a`, `5aeebf4`.

## 2026-08-13 - OCP-35 Exact Session Recovery

- Restored 39 pre-failure OpenCode sessions into their persisted Herdr panes
  without interrupting three emergency sessions, then captured all 42 exact
  active session identities for restart recovery.
- Added atomic minute-level active-session capture, fail-closed SQLite and pane
  validation, exact managed-wrapper resume, duplicate prevention, bounded Herdr
  calls, and launchd owner shutdown forwarding.
- Affected validation passed 44 tests, Python and Bash syntax checks, plist lint,
  Git whitespace checks, exact 42-entry live preflight, and idempotent no-op
  recovery. Gate Exceptions: none. A deliberate second Herdr restart was not run
  because it would terminate the active delivery session. Intended Final Push:
  feature branch and draft pull request into protected `main`.

## 2026-08-10 - OCP-34 Cross-Checkout Cycle Routing

- Added registry-bounded `dbsctr_attach` targeting and session-scoped routing for
  subsequent cycle tools, removing the requirement to relaunch OpenCode in an
  active cycle worktree.
- Provider Build agents inherit centralized-state paths from generated global
  permissions. Targeted deployment passed with an empty managed diff; fresh
  OpenCode resolution includes centralized worktree access. Current processes
  require one normal restart to load the new tool schema. Implementation Gate
  Commits: `fae3b76`, `22d548b`. Intended Final Push: feature branch and draft
  pull request into protected `main`.

## 2026-08-09 - OCP-33 Luna Routing

- Routed the managed `small_model` default and read-only `explore-openai` agent
  to GPT-5.6 Luna. Scout and Builder remain on Terra, Reviewer remains on Sol,
  and compaction routing is unchanged.
- Red/green routing checks and 43 affected control-plane and portability tests
  passed with Git whitespace validation. Gate Exceptions: none. Implementation
  Gate Commits: `b7339ea`, `1c8353a`. No managed configuration was applied.
  Intended Final Push: feature branch and draft pull request into protected
  `main`.

## 2026-08-08 - OCP-32 Centralized Durable State

- Added optional centralized OpenCode, DBSCTR, Hermes, and Herdr durable state,
  fail-closed drive guards, exact Build permissions, and native defaults when no
  root is configured. Existing SQLite formats and local credentials remain
  unchanged.
- Portabilized five active cycle records to schema 4, copied state with online
  SQLite backups, repaired 15 linked worktrees, and restored 39 exact sessions
  plus three intentional auto panes. The native registry and machine config are
  retained as timestamped rollback artifacts.
- Affected validation passed 315 tests with one existing skip, Python compilation,
  plist lint, Git whitespace checks, centralized environment checks, SQLite
  `quick_check`, Hermes service validation, and 42-pane readiness. Gate
  Exceptions: none. Implementation Gate Commits: `4fe1680..62f1010`. Intended
  Final Push: feature branch and draft pull request into protected `main`.

## 2026-07-31 - OCP-31 Isolated Lens Workers

- Added one-lens worker plans, deterministic review-session family attribution,
  pass telemetry, a dedicated lens-audit skill, and an explicit autonomous flag
  for evidence-ready noncritical P1-P3 Discovery. Critical or uncertain work and
  every merge/deploy decision remain operator-owned. Affected validation passed.
- Added same-repository linked-worktree targeting to typed reconciliation so a
  source-rooted Build session can safely finish an isolated cycle.

## 2026-07-30 - V3.35 Documentation Reconciliation

- Corrected the current OCP-30 and provider-native harness status, retained Opus 5
  availability as a provider-local follow-up, and replaced ambiguous writing-skill
  provenance with exact commits. No managed configuration was applied.

## 2026-07-28 - Writing Skill ACLI Boundary

- Added direct ACLI account-status, work-item view, and comment-list reads plus
  ask-gated bounded JQL search to global and native Plan contexts. Unbounded,
  browser, filter, wrapper, separator, redirection, and mutation forms are denied.
- Rendered permission contracts and isolated OpenCode configuration discovery
  passed. No live managed configuration was applied; existing OpenCode processes
  remain unchanged. Implementation and remediation commits: `761d01e`,
  `6904ff6`, `4b00081`. Intended Final Push: `origin/main`.

## 2026-07-28 - OCP-29 Hermes-Origin Discovery

- Added exact leased-reservation claiming before process start, deterministic
  native OpenCode session correlation, durable worker registration, and blocked
  cleanup on post-registration failure. Hermes can initiate Discovery without a
  Herdr pane but cannot answer Discovery or bypass DBSCTR authority.
- Host and guest Codex inference plus gateway restart checks passed before
  cutover. Affected QA passed 193 tests with one existing skip. Commits:
  `269125b..dc6d284`. Intended Final Push: `origin/main`.

## 2026-07-26 - Provider-Native Harness Delivery

- Added `/dbsctr-gpt` and `/dbsctr-claude`, provider-conditional guidance,
  Opus 5 high, exact loaded-runtime activation, telemetry schema `2`, and typed
  report-only evaluation read/save boundaries without cross-provider fallback.
- Affected QA passed with 219 tests and one existing environment skip; Python
  compilation, externalized Bun build, rendered config, targeted deployment,
  source identity, and idempotence passed. A fresh GPT-5.6 process attached the
  exact activated identity. Opus 5 remained unavailable because the Bedrock
  adapter did not consume SSO credentials and is tracked as a provider-local
  follow-up. Iterative independent review closed selective-backup, stale-receipt,
  Bedrock-family, commit-trace, and bounded-cache findings; final review reported
  no material findings. Intended Final Push: `origin/main`.

## 2026-07-26 - Provider-Native Harness Discovery

- Defined exact provider entry, Opus 5 high, provider-local review behavior,
  separately versioned exact telemetry, loaded-runtime activation identity, and
  strict no-cross-provider routing contracts.
- Reconciled against deployed DAI-011 commit `c24f7e5`; 215 affected tests passed,
  one skipped, and iterative independent review found no material issues. No
  implementation or deployment occurred. Intended Final Push: `origin/main`.

## 2026-07-26 - DAI-011 Operational Federation

- Federated review schema version `2` binds source captures and configured source
  order, removes only the aggregate wall-clock timeout, and returns serialized
  runtime-health results at the typed boundary. Autonomous review excludes its
  own host session, uses private transient captures as evidence, and allows only
  read-only GitHub issue and pull-request listing without operator interaction.
- Live installed-tool traversal and a controlled native-Build worker reached the
  human Discovery boundary; direct helper success alone is no longer accepted as
  operational evidence.

## 2026-07-24 - OCP-26 Federated VM Control

- Added typed federated history filters and configured-workspace implementation handoff.
  Both boundaries enforce exact sanitized schemas; continuation state binds the
  query, manifests are independently verified, and handoff success requires a
  valid Herdr pane identity.
- Renamed the fixed host helper to `sandbox-vm`; guest Herdr and OpenCode retain
  native names because client identity belongs to the Lima sandbox boundary.
- Updated typed VM handoff to Herdr 0.7.5's workspace/root-pane contract before
  starting `--kind opencode`; the unsupported direct `--cwd` agent launch was
  removed after live guest validation.
- Clarified that handoff success proves bounded Herdr launch acceptance, while
  guest cycle and draft-PR progress remain asynchronous and guest-authoritative.

## 2026-07-23 - OCP-25 Improvement Retirement Permission

- Added a trailing broad `ask` rule for every shell-wrapped
  `dbsctrctl improvement-forget` invocation while retaining existing improvement
  tool permissions. Rendered configuration contracts and targeted deployment
  passed. Implementation evidence: `ec9cbc4`, `732ae79`.

## 2026-07-19 - Exact Local Reference Boundary

- Replaced the duplicate generated `path/*` allow with distinct exact-root and
  recursive-subtree rules after global deny. This preserves access after
  OpenCode merges and deduplicates reference permissions.
- Validation: red rule-shape regression, 25 focused tests, targeted dry-run and
  deployment passed. Existing OpenCode processes require restart. Gate
  Exceptions: none. Intended Final Push: `origin/main`.

## 2026-07-19 - Portable Reference Permission Ordering

- Replaced configured-reference scalar denial with ordered external-directory
  rules: deny every external path first, then allow only the configured
  configured reference subtree. Empty configurations retain scalar deny behavior.
- Validation: red permission regression, 25 focused tests, targeted dry-run and
  deployment passed. Existing OpenCode processes require restart. Gate
  Exceptions: none. Intended Final Push: `origin/main`.

## 2026-07-19 - Portable Local Repository Reference

- Added an optional machine-local reference path that renders one named
  OpenCode reference without committing teammate-specific absolute paths. Empty
  shared defaults preserve the deny-by-default external-directory boundary.
- Validation: 25 focused control-plane and portability tests passed; configured
  and empty rendering passed; targeted chezmoi dry-run, deployment idempotence,
  and `opencode debug config` passed. Existing OpenCode processes require
  restart. Gate Exceptions: none. Intended Final Push: `origin/main`.

## 2026-07-19 - Compact Analytics Adapters

- Added read-only `dbsctr_history_capture`, `dbsctr_history_telemetry`, and
  `dbsctr_benchmark` tools over finalized helper contracts. Capture pages remain
  cursor-bounded, legacy telemetry becomes explicitly unavailable, and benchmark
  replay returns the immutable helper result without adapter-side classification.
- Adapters use shell-free argument vectors, a shared 256 KiB output cap,
  30-second process-group timeout, strict response schemas, and raw plus decoded
  path/URL rejection. They receive global read permission and no analytics write
  authority.
- Validation: 20 control-plane tests, Bun bundle, rendered permissions, injection,
  malformed/unsafe/oversized output, legacy availability, and deployed live
  telemetry probes passed. Independent review was unavailable because the
  reviewer could not access the isolated worktree; direct primary review found
  and fixed escaped-JSON privacy handling. Gate Commit: `0611451`. Gate
  Exceptions: none. Deployment: exact OpenCode runtime/tool/config targets.
  Existing OpenCode processes require restart. Intended Final Push: `origin/main`.

## 2026-07-19 - Advisory Runtime Health

- Added read-only `dbsctr_runtime_health` normalization over structured Herdr
  current-pane output with canonical identity checks, a two-second process-group
  timeout, one shared 64 KiB output budget, and no path or error disclosure.
- Hardened runtime attachment below shell permissions: authoritative OpenCode
  message ownership must match the supplied parentless primary session, and the
  CLI accepts no database override. Builder child sessions fail closed.
- Validation: 19 control-plane tests, focused helper attachment tests, Bun
  bundle, diff checks, and independent security review passed with no findings.
  Gate Commits: `c96093d`, `3f2a102`, `102abf5`, `51dcba4`. Gate Exceptions:
  none. Deployment: targeted helper/runtime/tool apply, idempotence, source
  identity, and live healthy-pane normalization passed. OpenCode restart is
  required for existing processes to load the new tool. Intended Final Push:
  `origin/main`.

## 2026-07-19 - Runtime And Analytics Interface Discovery

- Approved future OCP-17 advisory runtime-health behavior and OCP-18 bounded
  capture, telemetry, and benchmark adapters without claiming those ready
  interfaces are deployed.
- Validation: 52 affected tests, diff checks, and independent contract review.
  Contract Gate Commits: `dcea012`, `bacdaaa`, `7c336b0`, `a02bfce`. Gate
  Exceptions: none. Intended Final Push: `origin/main`.

## 2026-07-18 - Exact History Cohort Save

- Added optional `limit` and `cursor` fields to the typed history-save adapter,
  preserving legacy payloads while enabling source-bound continuation cohorts.
- Validation: executable adapter payload check, Bun bundle, 145 passed and 1
  skipped across Python 3.12-3.14, and independent review with no findings.
  Gate Exceptions: none. Intended Final Push: feature branch and draft pull
  request against `origin/main` only.

## 2026-07-18 - Exact Custom Build Selection

- Removed uppercase frontmatter name overrides so `build-gpt` and
  `build-claude` match their filename-derived CLI/runtime IDs. Documented that
  model selection never changes the active primary agent.
- Retained hard task allowlists: `build-claude` can delegate only to Bedrock
  Claude Sonnet 5 Explore, Scout, and Builder agents.
- Live probes confirmed uppercase IDs are absent, `build-claude` rejects an
  OpenAI Explore request, and `explore-bedrock` runs
  `amazon-bedrock/global.anthropic.claude-sonnet-5`.

## 2026-07-18 - Autonomous R&D Worker

- Added provider-neutral typed improvement status, claim, and update tools with
  native-Build-only mutation authority and explicit Builder denial.
- Added `/dbsctr-improve` for global sanitized review, holistic research,
  distinct claim, Discovery pause, explicit proceed, isolated draft-PR DBSCTR,
  and truthful no-finding escalation.
- Validation: 157 passed, 1 skipped; resolved config, fresh command/tool
  deployment, role isolation, and independent review passed. Gate Exceptions:
  none. Intended Final Push: `origin/main`.

## 2026-07-16 — Scout Context7 And Standing Build Begin

- Added the managed Context7 remote MCP with optional environment-backed
  1Password credential use, global denial, and Scout-only access. Fresh anonymous
  and authenticated connections passed, and a fresh Scout query used Context7.
- Replaced redundant typed-begin approval with standing authorization for native
  and provider-affine Build primaries. Plan and every subagent remain denied;
  only Build primaries may access helper-owned DBSCTR worktrees without prompts.
- Validation: 39 affected tests, Bun transpilation, rendered and resolved config,
  independent security review, targeted deployment/idempotence, role isolation,
  MCP connectivity, and fresh Scout use passed. Gate Exceptions: none. Gate
  Commits: `30789fa`, `9abea1b`, `791bc22`. Intended Final Push: `origin/main`.

## 2026-07-16 — V3.16 Historical Review And Backtesting

- Added typed historical scan and atomic report-save tools, fixed-cohort replay,
  composable filters, immutable scan identity, and standing local save authority
  while denying the write to read-only and Builder subagents.
- Validation: 118 affected tests passed and 1 skipped; Bun checks, rendered and
  resolved config, targeted deployment/idempotence, live history/privacy probes,
  and independent OpenAI review passed.

## 2026-07-15 — V3.14 Structured Runtime Correlation

- Typed begin now forwards stable OpenCode tool-context identity. Optional Herdr
  launch uses no-focus and returns advisory structured metadata without another
  helper mutation.
- Validation: 108 affected tests passed and 1 skipped; Bun build, resolved config,
  targeted deployment, idempotence, and structured runtime fixtures passed.

## 2026-07-15 — V3.13 Review Queue And Retention

- Propagated immutable session/part ceilings and database identity through the
  typed review tools, preserving stable completion while private detailed
  reports age into compact tombstones.
- Validation: 106 affected tests passed and 1 skipped; Bun build, resolved
  permissions, real scan, targeted deployment, and idempotence passed.

## 2026-07-15 — Trustworthy DBSCTR Review Snapshots

- Propagated one immutable review cutoff through typed scans, continuations, and
  permission-gated completion while retaining read-only Plan scans.
- Rejected changed candidate metadata and concurrent duplicate completion, and
  exposed unknown session state without prose inference.
- Validation: 102 affected tests passed and 1 skipped; Bun build, resolved config,
  authoritative database scan, targeted deployment/idempotence, and deployed
  identity passed. Independent review reported no remaining findings.
- Gate Commit: `e04aa78`. Deployment: targeted local chezmoi apply. Gate
  Exceptions: none. Intended Final Push: `origin/main`.

## 2026-07-15 — Private DBSCTR Review

- Added provider-neutral `/dbsctr-review`, read-only `dbsctr_review`, and
  permission-gated `dbsctr_review_complete` surfaces without a plugin.
- Denied completion to bounded Builders and guarded common raw helper invocation
  forms while preserving the documented non-sandbox Bash permission model.
- Validation: 95 affected tests passed and 1 skipped; Bun build, resolved config,
  targeted deployment/idempotence, deployed identity, real scan, and fresh skill
  loading passed. Independent review reported no remaining findings.
- Gate Commit: `f2eb3f1`. Deployment: targeted local chezmoi apply. Gate
  Exceptions: none. Intended Final Push: `origin/main`.

## 2026-07-13 — Retire Unsupported Pro Agents and Restore Native Build

- Confirmed `gpt-5.6-sol-pro` had not sent genuine Pro reasoning before
  OpenCode 1.17.19, then bypassed the new OAuth filter with a correctly formed
  base-Sol request and observed the ChatGPT backend reject
  `reasoning.mode: "pro"` with `unsupported_value`.
- Removed the Sol-Pro override and the `Plan-GPT-Pro`, `Plan-GPT-Pro-Max`, and
  `Build-GPT-Pro` agents, including explicit chezmoi target retirement.
- Re-enabled native Build because OpenCode 1.17.20 hard-codes native Plan exit to
  agent key `build`; retained `Build-GPT` Sol medium and Terra subagents for
  manual provider-affine execution.
- Passed 35 affected tests, JSON parsing, diff checks, independent review,
  source-bound chezmoi dry-run/apply/status, resolved-config checks, and fresh
  native Build and `Build-GPT` tool probes. No gate exceptions were used.
- Gate commits: `af14f90`, `98900a3`, `4da132f`, `dcebd6c`. Deployment is local;
  intended Final Push target is `origin/main`.

## 2026-07-11 — Discovery

- Approved provider-neutral workflow commands and provider-affine delegation.
- Kept OpenCode Bedrock Claude and raw LM Studio.
- Approved complete removal of Claude Code, Meridian, Headroom, OMO, and their
  historical project documentation and machine state.
- Approved OpenCode-only skill curation and removal of Claude-specific or
  Anthropic-dependent Caveman skills.
- Required Graphify preservation with a freshness/relevance fallback and no
  duplicate project plugin.
- Set Discovery2 confidence to 99%.

## 2026-07-11 — Implementation

- Made workflow commands inherit the selected primary and aligned Plan/Build
  permissions with the approved autonomy boundary.
- Denied direct Anthropic provider use while preserving Bedrock Claude and raw
  LM Studio.
- Removed Claude Code, Meridian, Headroom, OMO, incompatible skills, packages,
  services, authentication, state, wrappers, providers, and historical docs.
- Made the skills CLI the sole owner of its mutable lock and constrained installs
  to the curated OpenCode set.
- Refreshed Graphify's global skill to 0.8.46, retained both Git hooks and query
  behavior, and removed the duplicate project integration.
- Added seven focused control-plane contract tests; all passed.
- Live Plan and Build-GPT probes passed. Build-Claude resolved to Bedrock Opus
  but its live request was blocked by an expired AWS SSO token; model listing and
  resolved provider-affinity assertions passed as next-best evidence.
