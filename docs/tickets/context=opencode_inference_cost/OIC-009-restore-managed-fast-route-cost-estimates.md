---
schema_version: 1
id: "OIC-009"
slug: "restore-managed-fast-route-cost-estimates"
context: "opencode_inference_cost"
title: "Restore managed Fast route cost estimates"
kind: "task"
state: "review"
priority: "high"
points: null
depends_on: []
relations:
  - "OCP-37"
owns:
  - "Managed OpenAI Fast rate-card entries, focused regression evidence, and inference-cost lifecycle artifacts"
reads:
  - "OCP-37 exact managed model identities and published priority-processing rate decision"
parallel_safe: false
validation:
  - "uv run --group test pytest -q tests/test_inference_cost_report.py"
  - "git diff --check"
created: "2026-08-23"
updated: "2026-08-23"
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Restore list-price estimates for the three exact managed OpenAI Fast identities.

## Context

OCP-37 routes managed OpenAI work through Sol Fast, Terra Fast, and Luna Fast.
The inference-cost card contains only their standard identities, so Fast usage is
correctly retained but currently unestimated.

## Scope

Add exact effective-dated Fast entries at published priority-processing rates.
Do not alias Fast IDs to standard IDs, infer historical prices, or deploy the
managed card.

## Acceptance Criteria

- Sol Fast, Terra Fast, and Luna Fast have exact card entries at twice their corresponding standard token-class rates.
- Fast entries start at `2026-08-23T00:00:00Z`; earlier usage remains unestimated.
- Standard entries and conservative long-context behavior remain unchanged.
- Focused inference-cost tests and Git whitespace validation pass.

## Risks

Decision-facing estimates are wrong if an exact identity, token-class rate, or
effective boundary drifts. Exact card assertions and the existing interval
resolution regression constrain those failures.

## Evidence

- The focused test first failed with `KeyError: ('openai', 'gpt-5.6-sol-fast')`, proving the missing exact entry.
- `uv run --group test pytest -q tests/test_inference_cost_report.py`: 6 passed.
- `git diff --check`: passed.
- Standard rates were reverified unchanged on 2026-08-23 before the card-level retrieval date advanced.

## Review

Independent review identified mixed-date provenance and ambiguous resolver
boundary evidence. The spec now records standard-rate reverification, and the
end-to-end test distinguishes exact-boundary and pre-boundary records. Final
review found no material issue; mutable external pricing pages remain a residual
provenance risk mitigated by the checked-in values and report card digest.
