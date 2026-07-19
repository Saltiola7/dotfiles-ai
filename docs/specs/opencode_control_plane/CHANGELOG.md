# OpenCode Control Plane Changelog

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
