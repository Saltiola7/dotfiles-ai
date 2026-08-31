---
name: dbsctr-performance-audit
description: Audit DBSCTR cycle performance, session telemetry, orchestration, validation, and tool failures without weakening quality. Use when asked to speed up cycles, find lifecycle bloat, review autonomous runtime, or repeat the cycle-performance audit.
trigger: /dbsctr-performance-audit
---

# DBSCTR Performance Audit

## Outcome

Produce one reproducible, report-only map of DBSCTR optimization surfaces and a
ranked delivery portfolio. Ground measured findings in private sanitized local
evidence, retain obvious source-backed opportunities when timing is unavailable,
and preserve every required quality and safety outcome.

Read `docs/initiatives/dbsctr-cycle-speed/` and the matching context specifications
before analysis. Change nothing during the audit.

## Boundaries

- Keep raw session content, candidate identifiers, paths, provenance, prompts,
  responses, tool payloads, commands, URLs, credentials, environment values, and
  account identity local and out of the report and subagent prompts.
- Never call `dbsctr_review_complete` or `dbsctr_review_history_save`.
- Never call `dbsctr_incident_register`, `dbsctr_incident_update`, or `dbsctr_incident_forget`.
- Never call `dbsctr_improvement_claim` or `dbsctr_improvement_update`.
- Never call `dbsctr_begin`, `dbsctr_initiative_launch`, delivery, or activation tools.
- Never query the OpenCode database, PostgreSQL, or private ledgers directly.
- Never infer unavailable values as zero or causal effects from associations.

## Evidence Pass

1. Resolve a fixed Git commit and read the Initiative, context specifications,
   configured QA, model routes, CI, and lifecycle source. Use
   `dbsctr_inspect` when worktree overlays would make source ambiguous.
2. Call `dbsctr_runtime_health`. Run `dbsctrctl cycle-performance --json` and,
   when known, repeat with `--context CONTEXT`. Record autonomous and calendar
   aggregates, coverage, unavailable samples, gate failures, reopenings, and
   remediation together.
3. Call `dbsctr_incident_scan` with global scope by itself. Do not place this
   required call in a parallel batch with DKS, skill loading, or external work.
4. Call `dbsctr_review_history` with the narrowest relevant filters and a maximum
   first page of 100. Preserve the returned snapshot, session ceiling, part
   ceiling, database digest, exclusion digest, limit, and cursor for every
   continuation. Aggregate only allowlisted sanitized metadata locally.
5. Call `dbsctr_history_telemetry` once with the same bounded filters. On timeout
   or unavailability, retain the successful history evidence and mark structured
   telemetry unavailable. Do not retry a broader query.
6. Call `dks_context` for the highest-value architecture question with one
   attempt. On lock contention, timeout, or unavailability, record the failure
   class and use fixed-commit source. Never bypass the quality lock.
7. Check whether `graphify-out/graph.json` exists before loading Graphify. If no
   graph exists, skip it. If one exists, verify its commit and use one targeted
   query before source verification.
8. Use Explore only for unresolved fixed-commit local architecture. Use Scout
   only for current authoritative public guidance that can change a decision.
   Run at most three independent subagent lanes. Never send private telemetry or
   governed result bodies to a hosted subagent.

Each optional evidence source gets one attempt. A failed optional source must not
cancel a required local source or trigger repeated fallback work.

## Reduction

Compute bounded counts and integer mean, p50, and p90 where the source supports
them. At minimum cover:

- cycle autonomous/calendar time, coverage, state, risk, delivery, and Method Revision
- gate failures, reopenings, remediation, unavailable required evidence, and CI
- session elapsed time, tokens, tools, errors, children, delegation, agents, and models
- Discovery and approval, context retrieval, begin/worktrees, phase locks,
  implementation, QA, gate evidence, deployment, delivery, operations, review,
  maintenance, retries, timeouts, and context growth

Label every finding exactly one of `measured`, `source_backed_unmeasured`,
`external_guidance`, or `assumption`. State cohort composition and attribution
caveats. Provider cost is unavailable unless authoritative billing evidence exists.

## RCA

Perform root-cause analysis for every reproduced timeout, abort, lock failure,
retry loop, or repeated gate remediation. Trace the adapter, subprocess boundary,
query, lock order, timeout/cancellation, and tests. Distinguish a specific aborted
parallel batch from an independently slow underlying command.

Do not recommend retrying an expensive failing tool as its own optimization.
Prefer bounded failure, fast authoritative fallback, stage attribution, and a
separately measurable repair.

## Prioritization

Rank by impact, observed frequency, confidence, effort, and quality risk:

- P0: critical safety/reliability failure or a workflow that cannot complete.
- P1: reproduced high-impact latency, repeated remediation, duplicate exact work,
  or a strong high-volume bottleneck.
- P2: useful measured improvement with bounded risk or benchmark-gated concurrency.
- P3: source-backed but currently low-impact or speculative work needing telemetry.

`reviewer-openai` is only for explicit or critical review or a named specialist
lens. Primary integration review and affected QA remain required. Treat reviewer,
model, token, and elapsed associations as confounded until comparable cohorts pass
the same quality gates.

Reject proposals that remove gates, validation, privacy, security, data-loss
handling, accessibility, compatibility, recovery, or required evidence. Reusing
validation is valid only when commit, normalized paths, command, authority,
toolchain, and environment identities match; gate decisions remain separate.

## Report

Return these sections in order:

1. Executive findings
2. Evidence availability and cohort caveats
3. Cycle and session scorecards
4. Reproduced failure RCA
5. Complete optimization-surface map
6. Ranked opportunity portfolio
7. Model, reviewer, Scout, Explore, and orchestration recommendations
8. Quality guardrails and rejected shortcuts
9. Delivery slices with context ownership, dependencies, validation, baseline,
   metric, procedure, success threshold, and residual risk

Separate measured conclusions from source_backed_unmeasured opportunities. Bring
obvious bloat forward even without timing, but do not assign causal benefit.
Conclude with the smallest independently deliverable P0/P1 slice. Implementation
requires separate Discovery readiness and exact approval.
