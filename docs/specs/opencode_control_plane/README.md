# OpenCode Control Plane

**Status:** OCP-17 advisory runtime health and OCP-19 autonomous worker implemented
**Discovery2 confidence:** 99%

## Engineering Profile

### Defaults

| Field | Value |
|---|---|
| Deliverable | Managed OpenCode providers, agents, commands, permissions, skills, and routing |
| Languages/frameworks | JSON/JSONC configuration, Markdown agent prompts, Python contract tests |
| Modules | ML/AI |
| Runtime/platform support | OpenCode in the managed macOS dotfiles environment; Python `>=3.12` tests |
| Public compatibility | Preserve native Plan-to-Build and provider-affine Build workflows; retire provider entries that current authentication cannot use |
| Trust/data classification | Local configuration and public provider metadata; credentials remain outside the repository |
| Operational owner | Dotfiles owner maintains deployment and OpenCode compatibility |

### OCP-16 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: adds an external documentation boundary and changes typed cycle-begin authorization |
| Delivery intent | Deploy managed OpenCode configuration, Scout permissions, lifecycle routing, and tests locally |
| Scope | Scout-only Context7 with optional environment credential; standing authorization for validated typed begin in Build |
| Overrides | Plan remains read-only; Context7 is non-authoritative and optional; destructive and external writes remain permission-gated |

### OCP-19 Cycle Overrides

| Field | Value |
|---|---|
| Risk | Elevated: grants a native-Build workflow bounded claim and draft-PR delivery interfaces |
| Delivery intent | Deploy the managed worker command, typed coordination adapters, and narrow permissions locally |
| Scope | Global review, holistic research, atomic claim, Discovery pause, explicit proceed, isolated DBSCTR cycle, and draft PR |
| Overrides | Only `chezmoi-dotfiles-ai` is writable; private provenance is withheld; no automatic merge, release, deployment, or Discovery answer |

## Overview

The OpenCode control plane owns global providers, agents, commands, permissions,
skills, and Graphify routing. It keeps OpenAI and Amazon Bedrock workflows
provider-affine while removing unused Claude Code, Meridian, Headroom, and OMO
surfaces.

## Goals

- Keep native Plan and Build, plus provider-affine `build-gpt` and `build-claude`.
- Keep direct Bedrock Claude and raw LM Studio models.
- Make workflow commands inherit the selected primary agent.
- Allow local Build commands by default while gating external or destructive writes.
- Give Builder subagents bounded write access without Git, deployment, or external paths.
- Install only OpenCode-compatible skills, once.
- Preserve Graphify CLI, skill, graph, hooks, and health-gated query-first routing.
- Remove Claude Code, Meridian, Headroom, OMO, and their runtime state completely.

## Non-goals

- No new orchestration framework, review agent, MCP server, or benchmark suite.
- No Graphify package changes.
- No removal of Bedrock Claude or raw LM Studio.
- No changes to V1 `dbsctr` or `discovery`.

## Ubiquitous Language

| Term | Meaning |
|---|---|
| Control Plane | Managed OpenCode config, agents, commands, permissions, skills, and routing. |
| Provider Affinity | Delegation remains inside the active primary's provider family. |
| Local Build Command | In-worktree command without external, destructive, deploy, publish, or Git-write effects. |
| Runtime Residue | Unmanaged config, package, service, authentication, cache, or backup from a removed integration. |
| Graph Health Gate | Freshness and relevance check before trusting a Graphify query. |

## Behavior

### Provider-neutral commands

Given any selected primary, when `/dbsctr`, `/discovery`, or `/qa` runs, then
the command uses that primary and does not force OpenAI.

### Plan and Build permissions

Given a Plan primary, edits are denied and Bash requires approval. Given a Build
primary, local commands run by default while known external, destructive,
deployment, publishing, and Git-write commands require approval.

### Native Plan-to-Build handoff

Given native Plan completes planning, its built-in exit path targets the native
`build` agent. Native Build therefore remains enabled. `build-gpt` and
`build-claude` are lowercase filename-derived custom-primary IDs selected through
the agent control or exact `--agent` value; changing only the model does not
change the active agent.

### Bounded Builder

Given a provider-local Builder subagent, it may edit owned in-worktree files and
run focused checks, but cannot use external directories, delegate, write Git
state, deploy, publish, or perform external writes.

### Provider affinity

Given an OpenAI primary, it delegates only to OpenAI optimized agents. Given
`build-claude`, it delegates only to Bedrock optimized agents. No fallback
crosses providers silently.

### ChatGPT OAuth model exposure

Given OpenAI uses ChatGPT OAuth, only models and reasoning-effort variants
supported by that route are exposed. Native Plan and `build-gpt` use base
GPT-5.6 Sol with medium effort by default, while the user may select another
supported effort variant. No agent or provider override claims unavailable Pro
reasoning mode. The ChatGPT OAuth backend rejects base Sol requests containing
`reasoning.mode: "pro"` with `unsupported_value`. OpenAI Explore, Scout, and
Builder remain on GPT-5.6 Terra.

### Removed integrations

Given deployment completes, Claude Code, Meridian, Headroom, OMO, their wrappers,
providers, services, packages, skills, authentication, state, backups, and
historical project documentation are absent. Bedrock Claude remains available.

### Graphify preservation

Given an existing graph, architecture work checks graph freshness and relevance,
queries it when useful, verifies findings against source, and falls back to
source search when stale or weak. Full Graphify creation, update, query, and Git
hook behavior remains available without a duplicate project plugin.

### Private DBSCTR review

Given `/dbsctr-review` runs under any selected primary, it loads the unversioned
review skill and uses a read-only typed scan. Persisting the sanitized private
report asks through a separate typed completion permission. The completion tool
writes only DBSCTR operational review state and grants no repository mutation.

Given a review spans pages, when the first page captures a snapshot, then typed
continuations and completion preserve that snapshot and reject changed sanitized
candidate metadata. Session prose without structured lifecycle authority reports
`unknown` rather than a guessed terminal state.

Given detailed reports exceed 90 days, completion or explicit maintenance prunes
them while compact private reviewed-ID tombstones preserve review progress.
Candidates expose independent Cycle Record states and page-local urgency without
inventing an aggregate state.

### Autonomous R&D worker

Given a fresh scheduled native-Build session, when its managed worker command
runs, then it processes global sanitized review evidence, compares it with the
private improvement ledger, this repository's specs/source/tests and GitHub
state, and authoritative external documentation through Scout when useful.

Given a defensible distinct opportunity, when the worker claims it atomically,
then it runs Discovery in the same session and stops for every material question.
Answering questions does not itself authorize implementation; the operator must
explicitly instruct the worker to proceed.

Given explicit proceed and completed Discovery, when the worker begins DBSCTR,
then it edits only the helper-owned isolated worktree for this source and may use
the typed claim and draft-PR delivery interfaces. Builder and read-only subagents
remain denied those writes.

Given no distinct finding after every configured lens is exhausted, when the
worker cannot justify a change, then it asks the operator where to research next.
It never manufactures a proposal merely to finish the scheduled run.

Given typed cycle begin runs, stable OpenCode tool context records the initiating
session and worktree in the Cycle Record. Optional Herdr launch metadata remains
advisory, uses no-focus launch, and never changes lifecycle state or cleanup.

Given `/dbsctr-review` is asked to inspect history, a separate read-only typed
tool includes reviewed candidates through bounded composable filters and fixed
cohort replay. A schema-validated history-save tool has standing authority only
for sanitized private reports and cohort manifests; it never changes operational
review markers or repository state and remains denied to Builder subagents.
The save tool optionally forwards the source history page's `limit` and `cursor`
so complete-page cohorts can use source-bound exact-member revalidation; callers
that omit them retain strict whole-snapshot validation.

### Runtime Health And Approved Future Compact Analytics Interfaces

OCP-17 runtime health is current after deployment. Compact analytics contracts
become current only when OCP-18 is completed and deployed; until then, existing
history interfaces remain authoritative.

Given a validated Build primary attaches its current runtime, the typed control
plane persists only the helper-validated runtime identity and returns normalized
Herdr health as advisory operational metadata. Health is one of `healthy`,
`missing`, `ambiguous`, or `unavailable`; malformed Herdr output fails closed and
never changes a Cycle Record, gate result, or improvement state.

Runtime attachment requires structured message identity that resolves through
the authoritative OpenCode database to a parentless primary session and exactly
matches the supplied session ID. The attachment command accepts no database
override. Child Builder sessions fail at the helper boundary even if a shell
wrapper bypasses textual command matching; supplying a primary message can only
idempotently attach that primary.

`dbsctr_runtime_health` invokes only structured `herdr pane current`. Outside a
Herdr runtime or when the command is unavailable it returns `unavailable`; a
valid absent pane returns `missing`; malformed output or mismatched OpenCode
session/worktree identity returns `ambiguous`; and an exact current pane returns
`healthy` with bounded presentation IDs and normalized agent status. It emits no
path, command error, or private content and performs no write. The Herdr probe
has a two-second timeout and 64 KiB output cap, and compares canonical existing
worktree paths so equivalent macOS/symlink spellings do not create false health.
The probe runs in its own process group so timeout terminates descendants that
retain output pipes.

Given a caller requests compact history or benchmark evidence after the matching
helper interface is finalized and deployed, typed adapters
expose bounded capture summary, ordered member drill-down, exact replay, telemetry
availability, and versioned benchmark results from finalized helper JSON
contracts. Schemas reject unknown arguments, invalid cursors, oversized requests,
and malformed helper output. No adapter returns an unbounded member collection.
The read-only tools are `dbsctr_history_capture`, `dbsctr_history_telemetry`, and
`dbsctr_benchmark`. They execute argument vectors without a shell, cap combined
helper output at 256 KiB with a 30-second timeout, reject unsafe path/URL content,
and validate the returned contract before exposure. Legacy history without a
telemetry envelope is normalized only to explicit `unavailable` fields; adapters
never infer a value or classification.

Plan, Reviewer, Explore, Scout, and Builder agents cannot attach runtimes or
write analytics state. Read-only analytics access and permissioned private-state
writes remain separate tools. OpenCode adapters never duplicate helper lifecycle,
capture, attribution, or benchmark state machines.

### Scout-only current documentation

Given a Scout-class subagent needs current dependency documentation, when it
uses Context7, then OpenCode connects to the managed remote MCP endpoint and
exposes only `context7_*` tools to Scout-class agents. Primary, Builder,
Reviewer, and Explore agents cannot use those tools.

Given `CONTEXT7_API_KEY` is non-empty, Context7 requests use it through runtime
environment substitution. Given it is absent, Context7 remains usable through
its anonymous service and no credential is required. The key is never stored in
Git, rendered source, agent prompts, logs, or tool arguments.

Context7 results are research hints. Scout verifies material claims against
project source or authoritative upstream documentation and reports uncertainty.

### Standing typed cycle begin

Given Build invokes `dbsctr_begin` with an applicability plan, when OpenCode
dispatches the typed tool, then it runs without another permission prompt. The
helper still validates the committed profile, upstream, worktree safety, ahead
commits, plan, risk, and arguments before creating local cycle state.

Plan continues to deny `dbsctr_begin` and returns a Build Handoff. Direct
destructive operations, external writes, deployment, DVC push, and non-DBSCTR
Git push retain their existing permission boundaries. Optional Herdr launch
remains explicit through `launch=true` and never becomes lifecycle authority.

Given the primary orchestrator operates on a helper-created isolated worktree,
OpenCode allows external-directory access only beneath
`~/.local/state/dbsctr/worktrees/**` without another prompt. Only native Build,
`build-gpt`, and `build-claude` receive that allow rule. Plan and every subagent deny
external-directory access; Builder agents remain confined to the worktree where
they were launched.

Given a Build primary deploys the standalone AI dotfiles source, it may read and
edit only the machine-local `~/.config/dotfiles-ai/**` config and persistent
state directory outside the worktree. Plan and subagents remain denied, and no
personal chezmoi, credential, or arbitrary external path is exposed.

Given a teammate configures a non-empty machine-local SEO data science repository
path, when chezmoi renders OpenCode configuration, then it exposes that path as
the named `seo-data-science` reference to every agent under OpenCode's reference
boundary. Given the value is empty, the reference is omitted. The absolute path
never enters shared defaults or generated documentation.

## Contracts

- `$schema` remains `https://opencode.ai/config.json` and rendered config passes
  the current schema/runtime parser.
- Direct provider `anthropic` is denied; `amazon-bedrock` is not.
- Raw `lmstudio` remains configured; `headroom` and `headroom-lmstudio` do not.
- Native Plan remains the startup default and native Build stays enabled as the
  built-in Plan exit target.
- `gpt-5.6-sol-pro`, `Plan-GPT-Pro`, `Plan-GPT-Pro-Max`, and `Build-GPT-Pro`
  are absent while ChatGPT OAuth excludes Pro reasoning mode.
- Native Plan and `build-gpt` resolve to `openai/gpt-5.6-sol` with `medium` as
  their default effort; OpenAI optimized subagents remain on Terra.
- Commands contain no fixed `agent` field.
- `/dbsctr-review` contains no fixed agent field and loads its exact skill.
- `dbsctr_review` is read-only and allowed; `dbsctr_review_complete` asks before
  writing private operational state and remains denied to Builder subagents.
- `dbsctr_review_history` is read-only and allowed. `dbsctr_review_history_save`
  is allowed only for validated private history reports and remains denied to
  Builder subagents.
- `dbsctr_begin` is allowed for Build without an internal approval callback;
  Plan denies it, and the helper remains the authoritative safety boundary.
- The helper-owned DBSCTR worktree root is an allowed external directory for the
  Build primary orchestrators only; the global default is deny and the rule does
  not broaden arbitrary home-directory, Plan, or subagent access.
- The standalone `~/.config/dotfiles-ai/**` directory is allowed for Build
  primaries only so managed machine-local deployment values and source-specific
  persistent state can be maintained; the personal chezmoi config and all other
  external paths remain denied.
- `data.dotfiles_ai.opencode.seo_data_science_path` defaults to empty and is
  supplied independently by each machine. A non-empty value renders exactly one
  `seo-data-science` local reference with a stable description; an empty value
  renders no reference or external-directory access.
- Context7 is a managed remote MCP server. Its tools are globally disabled and
  enabled only for Scout-class agents. Its API key is optional and environment-
  backed when available.
- Skill names visible to OpenCode are unique.
- Unversioned lifecycle commands load DBSCTR V3; V1 is removed and V2 source is
  archived outside deployed skill paths.
- Runtime cleanup is irreversible and was explicitly approved.

## Validation Strategy

| Authority | Scope | Command | Availability |
|---|---|---|---|
| OpenCode parser | Resolved config and agents | `opencode debug config` | Required |
| JSON parser | Source/rendered config | `jq empty` | Required |
| Focused tests | Control-plane invariants | `pytest tests/test_opencode_control_plane.py` | Required |
| Chezmoi | Deployment and removals | dry-run, apply, status | Required |
| Graphify | Skill, hooks, query | version, hook status, targeted query | Required |
| Package/service inventory | Removed runtime | npm, pipx, launchctl, path checks | Required |
| MCP runtime | Context7 connection, anonymous fallback, optional authenticated request, and role isolation | `opencode mcp list` plus fresh Scout/non-Scout probes | Required |
| Typed begin | Prompt-free Build dispatch, helper-worktree access, and denied Plan dispatch | Focused tool/config tests plus fresh Build probe | Required |

## Risks

- Bash patterns are guardrails, not an OS sandbox.
- Runtime deletion cannot be rolled back without reinstalling removed tools.
- Removing the duplicate Graphify project integration must not remove its global
  skill, graph, or hooks.
- OpenCode provider behavior may change across upgrades; focused contract tests
  prevent unsupported aliases from silently returning.
- OpenCode cannot retarget native `plan_exit` to a custom primary; `build-gpt`
  and `build-claude` therefore require exact manual agent selection and a new
  message. Changing only the model leaves native Plan active.
- Context7 is externally operated and may be unavailable, rate-limited, stale,
  or incomplete; Scout reports degradation and falls back to authoritative
  sources without blocking unrelated work.
