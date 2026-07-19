# OpenCode Control Plane Changelog

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
  `seo-data-science` subtree. Empty configurations retain scalar deny behavior.
- Validation: red permission regression, 25 focused tests, targeted dry-run and
  deployment passed. Existing OpenCode processes require restart. Gate
  Exceptions: none. Intended Final Push: `origin/main`.

## 2026-07-19 - Portable Local Repository Reference

- Added an optional machine-local `seo_data_science_path` that renders one named
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
