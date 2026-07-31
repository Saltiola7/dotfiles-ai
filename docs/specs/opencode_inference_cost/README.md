---
title: "OpenCode Inference Cost Reporting (Spec v0.1)"
owner: AI Tooling
goal: "Report token usage and actual or estimated inference cost by DBSCTR bounded context without retaining prompt or response content."
status: "draft"
created: 2026-07-30
last_updated: 2026-07-30
version: "0.1"
pipeline_type: "analysis"
tags: ["opencode", "dbsctr", "telemetry", "cost", "roi"]
---

# OpenCode Inference Cost Reporting

## Overview

This bounded context turns local OpenCode usage metadata and DBSCTR lifecycle
metadata into auditable cost summaries by bounded context. The MVP reports the
cost side of AI ROI and the distribution needed for budgeting; it does not
claim ROI until a separately governed outcome or benefit numerator exists.

### Context Boundaries

| Context | Ownership |
|---|---|
| `opencode_inference_cost` | Derived cost resolution, descriptive statistics, reconciliation, and report schema. |
| `dbsctr_v3_lifecycle` | Cycle/context semantics, history capture, sanitization, attribution availability, and source lifecycle. |
| `opencode_control_plane` | Typed OpenCode adapters, permissions, provider/model activation identity, and local runtime routing. |
| `dotfiles_ai_distribution` | Federated capture transport, scheduled execution, private persistence, and deployment. |

This context consumes the other contracts and does not duplicate their scanners,
captures, permissions, retention state machines, or deployment paths.

## Engineering Profile

| Concern | Bounded-context default |
|---|---|
| Accountable owner | AI Tooling |
| Deliverable | Internal local CLI report with JSON and Markdown output |
| Applicable modules | Python, data, analytics, ML, security |
| Runtime | Existing Python `>=3.12` dotfiles/DBSCTR toolchain; no new service or scheduler |
| Sources | Read-only OpenCode database plus sanitized DBSCTR cycle/history metadata |
| Data classification | Internal developer telemetry; prompt, response, title, tool argument, credential, and repository-path content is prohibited |
| Canonical interfaces | Versioned report schema and `inference-cost-report` CLI contract |
| Compatibility | Unknown source schemas fail with a capability report; existing databases are never migrated |
| Reliability | Source totals reconcile to attributed, multi-context, and unknown totals; missing cost remains null |
| Recovery | Read-only rerun; outputs are replaced atomically after validation |
| Quality authorities | Repository-configured tests, lint, type checks, and sanitized fixture databases |
| Release | Git-versioned internal tool; no package publication in the MVP |
| Deploy/operate | Manual local execution only |
| Maintenance/retirement | AI Tooling owns source-schema adapters, rate-card dates, deprecation, and deletion guidance |

### Current Cycle Overrides

| Concern | Value |
|---|---|
| Affected scope | Specification and portable implementation backlog only; no live database mutation, scheduler, dashboard, or ROI benefit model |
| Risk | `elevated`: private developer telemetry and decision-facing financial estimates |
| Delivery intent | Transfer this specification to the dotfiles/DBSCTR repository, then implement through a feature branch and draft pull request |

## Goals

- Produce one table of token counts, actual cost, estimated cost, model mix, and
  descriptive statistics per bounded context.
- Quantify attribution and monetary coverage so missing metadata cannot look
  like zero usage or zero cost.
- Preserve source provenance and rate-card effective dates.
- Make repeated runs deterministic over the same source snapshot.

## Non-goals

- Reading or classifying prompts, responses, titles, or tool arguments.
- Allocating ambiguous usage proportionally across contexts.
- Treating public list-price estimates as invoices.
- Calculating ROI without an independently governed benefit numerator.
- Forecasting, anomaly alerts, dashboards, scheduling, or remote publication.
- Changing the OpenCode or DBSCTR source databases.

## Ubiquitous Language

| Term | Meaning |
|---|---|
| Usage Record | Provider/model token and cost metadata attributable to one OpenCode response or the smallest available source grain. |
| Bounded Context | Stable DBSCTR context name recorded by a cycle or explicit local mapping. A project digest is not a bounded context. |
| Actual Cost | Monetary cost recorded by the source. Zero is actual only when the source explicitly distinguishes it from unavailable. |
| Estimated Cost | USD list-price estimate computed from a versioned rate card and supported token classes. |
| Monetary Coverage | Share of usage tokens for which actual or estimated cost can be computed. |
| Attribution Status | `ATTRIBUTED`, `MULTI_CONTEXT`, or `UNKNOWN`. |
| Attribution Confidence | `HIGH`, `MEDIUM`, or `UNAVAILABLE`, retained separately from status. |
| Source Snapshot | Immutable read boundary identified by database digest and session/part ceilings where available. |
| Cost Basis | `RECORDED`, `LIST_PRICE`, or `UNAVAILABLE`; recorded and estimated values are never coalesced. |

## Domain Model

| Entity/value | Identity | Invariants |
|---|---|---|
| `UsageRecord` | source usage ID or deterministic source coordinates | Contains metadata only; token counts are non-negative; unavailable values are null. |
| `ContextAttribution` | usage record ID | Exactly one status; ambiguous records are never divided among contexts. |
| `RateCardEntry` | provider + model + effective interval | Currency is USD; intervals do not overlap for the same model; source and retrieval date are retained. |
| `ContextCostSummary` | source snapshot + bounded context + optional provider/model | Reconciles to the included usage population and exposes coverage. |
| `ReportManifest` | report schema version + source snapshot | Records generation time, filters, source capabilities, rate-card identity, and checksums. |

## Behavior Scenarios

### Context attribution

**Scenario: A DBSCTR cycle supplies one bounded context**

- Given a usage record belongs to a session with one unambiguous DBSCTR context
- When the report is built
- Then the usage is assigned to that bounded context with high confidence
- And the attribution source is retained.

**Scenario: One session spans contexts without part-level correlation**

- Given a session is associated with more than one bounded context
- And the source cannot correlate each usage record to one context
- When the report is built
- Then all affected usage is reported as `MULTI_CONTEXT`
- And no proportional allocation is fabricated.

**Scenario: No context evidence exists**

- Given usage has no cycle context or explicit mapping
- When the report is built
- Then it is retained as `UNKNOWN`
- And it remains included in grand totals and attribution coverage.

### Cost resolution

**Scenario: Recorded and estimated cost are both available**

- Given a usage record has authoritative recorded cost and a matching rate card
- When cost is resolved
- Then actual and estimated cost are reported in separate columns
- And variance can be calculated without replacing either value.

**Scenario: Model identity is unavailable**

- Given token usage exists but provider or model identity is unavailable
- When cost is resolved
- Then estimated cost is null with basis `UNAVAILABLE`
- And the tokens remain in totals and reduce monetary coverage.

**Scenario: Recorded zero is ambiguous**

- Given a source emits zero cost without a field proving that zero is authoritative
- When cost is resolved
- Then actual cost is null rather than zero
- And source availability is visible in the report manifest.

### Privacy and source safety

**Scenario: A source schema contains content fields**

- Given the OpenCode database contains prompt, response, title, or tool-argument columns
- When source capabilities are discovered
- Then those columns are excluded from every query projection
- And tests prove they cannot enter persisted output.

**Scenario: The source schema is unsupported**

- Given required usage/session relationships cannot be discovered
- When the report is requested
- Then execution fails before writing output
- And a metadata-only capability report identifies missing fields.

### Reporting

**Scenario: A context has one session**

- Given one attributed session
- When descriptive statistics are computed
- Then count, minimum, quartiles, mean, median, p95, maximum, and standard deviation are deterministic
- And standard deviation is zero rather than unavailable.

**Scenario: Output validation fails**

- Given source-to-summary reconciliation or schema validation fails
- When output is finalized
- Then no partial report replaces the prior valid report.

## Architecture And Data Flow

```mermaid
flowchart LR
    accTitle: OpenCode inference cost reporting flow
    accDescr: OpenCode usage metadata passes through a read-only capability probe and metadata-only extract. Sanitized DBSCTR lifecycle metadata supplies bounded-context attribution. A dated rate card supplies separate estimates. Reconciled summaries atomically produce JSON and Markdown, while failed validation preserves the prior report.
    O[(OpenCode DB<br/>usage metadata)] --> P[Read-only capability probe]
    D[DBSCTR sanitized<br/>cycle/history metadata] --> A[Context attribution]
    P --> E[Metadata-only usage extract]
    E --> A
    R[Versioned rate card] --> C[Actual and estimated cost resolution]
    A --> C
    C --> S[Context and context-model summaries]
    S --> V{Reconciliation and privacy validation}
    V -->|pass| J[JSON report + manifest]
    V -->|pass| M[Markdown table]
    V -->|fail| F[No output replacement]
```

**Text equivalent:** A read-only probe discovers supported metadata in the
OpenCode database. The extractor sends only usage metadata to context
attribution, which is enriched by sanitized DBSCTR metadata. A dated rate card
adds a separate list-price estimate. Aggregated context summaries pass privacy
and reconciliation checks before JSON and Markdown outputs atomically replace
prior reports. Failed checks write no final output.

## Source Contracts

### OpenCode database

The adapter must discover, not assume, table and column names. It may select only
stable identifiers, parent/session relations, timestamps, project/workspace
identity, provider/model identity, token counters, recorded cost, and source
schema metadata. It must open the database read-only and must not run migrations,
DDL, pragmas that mutate state, or content queries.

Required capability for a token report is a stable usage-to-session relation and
at least one token counter. Actual cost requires a source cost field with
availability semantics. Estimated cost requires provider and model identity plus
a matching effective rate-card entry.

### DBSCTR telemetry

DBSCTR supplies context and provenance, not replacement model detail. The
sanitized history interface currently exposes fields such as `session_id`,
`context`, `cycles`, `project_digest`, `method_revision`, `token_total`,
`cost_total`, `model_families`, `attribution_status`, per-field availability,
and immutable snapshot ceilings/digests. Every field must be interpreted using
its availability marker; `unavailable` is not zero or an empty set.

An observed archived sample had 128,469,753 tokens, zero reported cost,
`context=unavailable`, ambiguous correlation, model family `gpt`, and unavailable
provider/model IDs. This proves DBSCTR aggregates alone cannot satisfy the MVP's
model-level cost requirement.

### Explicit mapping

An optional local mapping may associate a session ID with exactly one context.
It is input-only, excluded from persisted reports, and never overrides a
contradictory DBSCTR cycle. Contradictions become `MULTI_CONTEXT`.

## Report Contract

### CLI

```text
dbsctrctl inference-cost-report \
  --opencode-db PATH \
  --output-dir PATH \
  [--mapping PATH] \
  [--after UNIX_MS] [--before UNIX_MS]
```

The command writes `inference-cost-report.json`,
`inference-cost-report.md`, and `manifest.json`. A `--dry-run` mode emits only
the capability report and planned row counts. Secrets and content never appear
in arguments, logs, errors, or output.

### Context summary

| Field | Type | Contract |
|---|---|---|
| `bounded_context` | string | Context name, `MULTI_CONTEXT`, or `UNKNOWN`. |
| `session_count` | integer | Distinct sessions contributing usage. |
| `usage_count` | integer | Distinct usage records. |
| `input_tokens` | integer | Sum of available uncached input tokens. |
| `output_tokens` | integer | Sum of available output tokens. |
| `cache_read_tokens` | integer/null | Null when source capability is absent. |
| `cache_write_tokens` | integer/null | Null when source capability is absent. |
| `reasoning_tokens` | integer/null | Null when source capability is absent. |
| `actual_cost_usd` | decimal/null | Sum only when recorded-cost coverage is explicit. |
| `estimated_cost_usd` | decimal/null | Versioned list-price estimate; never substituted for actual. |
| `actual_cost_coverage` | number | Fraction of included tokens with authoritative recorded cost. |
| `estimated_cost_coverage` | number | Fraction of included tokens with supported model/rate data. |
| `models` | array | Provider/model usage and cost breakdown; unavailable identity stays explicit. |
| `tokens_per_session_stats` | object | min, p25, mean, median, p75, p95, max, population standard deviation. |
| `actual_cost_per_session_stats` | object/null | Same statistics over sessions with authoritative actual cost. |
| `estimated_cost_per_session_stats` | object/null | Same statistics over sessions with complete estimates. |
| `p95_to_median_tokens` | number/null | Predictability ratio; null when median is zero. |
| `token_coefficient_of_variation` | number/null | Population standard deviation divided by mean; null when mean is zero. |

Quantiles use one documented deterministic method for all outputs. Monetary
values retain calculation precision internally and round only for display.

### Reconciliation invariants

- Every included usage record appears in exactly one context bucket.
- Context totals plus `MULTI_CONTEXT` and `UNKNOWN` equal grand totals for each
  available token class.
- Context-model totals equal context totals where model identity coverage is
  complete; gaps are reported rather than assigned to an invented model.
- Actual and estimated cost are never added together.
- A rate-card miss produces null estimated cost and lowers coverage.
- Persisted outputs contain no session IDs, message IDs, paths, or content.

## Failure Semantics

| Failure | Behavior |
|---|---|
| Database unavailable or locked | Fail clearly; do not copy or mutate the live database automatically. |
| Unsupported schema | Emit metadata-only capability diagnostics; write no report. |
| DBSCTR telemetry unavailable | Continue with explicit mapping or `UNKNOWN`; mark attribution source unavailable. |
| Unknown model/rate | Preserve tokens, null the estimate, lower coverage. |
| Invalid rate-card overlap | Fail before aggregation. |
| Reconciliation/privacy failure | Fail loud and leave prior valid outputs unchanged. |
| Markdown rendering failure | Fail the run; JSON and Markdown are one atomic report set. |

## Validation Strategy

- Use synthetic SQLite fixtures for each supported source shape; never copy a
  live OpenCode database into tests.
- Seed prohibited content fields with sentinel strings and assert they never
  appear in executed projections, logs, exceptions, or outputs.
- Cover attributed, explicitly mapped, conflicting, multi-context, unknown, and
  unavailable-DBSCTR cases.
- Cover recorded cost, ambiguous zero, estimate fallback, unknown model,
  effective-date boundaries, and overlapping rate-card rejection.
- Verify statistics for empty, singleton, repeated, and highly skewed samples.
- Verify source/context/model reconciliation and atomic output replacement.
- Run `uv run --group test pytest tests/test_dbsctr_lifecycle.py tests/test_opencode_control_plane.py -q` plus focused report tests.
- Run repository-configured lint and type checks over touched source, then
  `git diff --check` over all affected artifacts.

## Visual Evidence Plan

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | required: inference cost reporting flowchart | Which context owns extraction, attribution, costing, federation, and output? | Context Boundaries and Architecture | AI Tooling; ownership changes |
| Interaction | required: inference cost reporting flowchart | How does source metadata become a validated report? | Behavior and Architecture | AI Tooling; workflow changes |
| State | not_applicable: the MVP is a stateless manual transform with atomic replacement | - | Failure Semantics | AI Tooling; scheduling or persistent workflow state added |
| Data/trust | required: inference cost reporting flowchart | Where is private content excluded and sanitized lifecycle metadata introduced? | Source Contracts and Architecture | AI Tooling; source or privacy boundary changes |
| Schema | not_applicable: report-contract tables are the canonical accessible schema representation | - | Report Contract | AI Tooling; report schema changes |
| Dependency/deployment | not_applicable: no service, scheduler, or environment deployment exists in the MVP | - | Engineering Profile | AI Tooling; deployment introduced |
| Quantitative | not_applicable: no validated report dataset exists and no comparative decision is yet being made | - | Report Contract | AI Tooling; validated trend data controls a decision |

The flowchart's canonical sources are the Context Boundaries, Source Contracts,
and Architecture sections. AI Tooling updates the diagram and text equivalent in
the same change whenever ownership, source flow, trust boundaries, or output
flow changes.

## Risks And Decisions

| Type | Statement |
|---|---|
| Fact | Sanitized DBSCTR history has token totals and context/correlation metadata but can omit provider/model IDs. |
| Fact | Cost availability does not prove a reported zero is an authoritative zero. |
| Decision | The MVP reports actual and estimated cost separately. |
| Decision | Ambiguous usage is never proportionally allocated. |
| Decision | Prompt and response content are outside the source contract. |
| Risk | OpenCode schema drift can break extraction; capability detection and fixture adapters mitigate it. |
| Risk | Public list prices can differ from negotiated or cached billing; basis, effective date, and coverage remain visible. |
| Risk | Context attribution can be incomplete; `UNKNOWN` and `MULTI_CONTEXT` prevent false precision. |

## Gate Ledger

| Gate | Applicability | Result | Evidence or reason |
|---|---|---|---|
| Domain | required | passed | Ubiquitous language, domain model, source ownership, and trust boundaries defined. |
| Behavior | required | passed | Happy, edge, failure, privacy, and recovery scenarios defined. |
| Spec | required | passed | CLI, report schema, source contracts, and visual evidence plan defined. |
| Contract | required | passed | Preconditions, invariants, failure semantics, compatibility, and privacy constraints defined. |
| Test-driven implementation | required | pending | Target-repository implementation has not started. |
| Refactor | required | pending | Applies after affected behavior passes. |
| Review/Integrate | required | pending | Target-repository review and downstream trace required. |
| Release | not_applicable | not_run | MVP is an internal Git-versioned tool with no package publication. |
| Deploy | not_applicable | not_run | Manual local command; no environment change. |
| Operate | not_applicable | not_run | No service, schedule, or alerting in MVP. |
| Maintain/Retire | required | pending | Adapter/rate-card ownership and retirement guidance must be finalized with implementation. |
