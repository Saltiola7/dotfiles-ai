# Backlog - OpenCode Inference Cost Reporting

**Last updated:** 2026-07-30
**Critical path:** OIC-008 replaces lossy session-grain attribution; OIC-006 and OIC-007 remain separate cycles

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| OIC-008 | Attribute canonical step-finish costs through timestamped DBSCTR context intervals | P1 | implementing | OIC-005 | inference adapter, report schema, focused tests, inference lifecycle artifacts | sanitized lifecycle intervals and OpenCode metadata schema | false | Extraction, reconciliation, attribution, and schema-v2 output share one financial/privacy contract. | L | Focused red/green tests, affected QA, live read-only smoke, and independent review. |
| OIC-006 | Evaluate scheduled snapshots and trend reporting | P2 | pending | OIC-005 | Future cycle; ownership not assigned | validated MVP reports | false | Scheduling is useful only after manual reports prove stable. | M | Separate DBSCTR cycle and operational profile. |
| OIC-007 | Join governed outcome values for ROI reporting | P2 | pending | OIC-005 | Future cycle; ownership not assigned | separately governed benefit source | false | Cost alone is not ROI and benefit semantics require another bounded context. | L | Separate discovery and authority contract. |

## Execution Guide

- OIC-001 through OIC-005 are sequential because each fixes contracts consumed
  by the next task.
- Read-only source-schema research may run independently, but implementation
  ownership must not overlap the telemetry adapter or report module.
- OIC-006 and OIC-007 are explicitly outside the MVP.

## Completed

| id | outcome | completed | commit |
|---|---|---|---|
| OIC-001 | Reconciled the portable specification with the owning repository and live metadata schema. | 2026-07-30 | 1a5b8a9 |
| OIC-002 | Added strict read-only capability detection and synthetic privacy fixtures. | 2026-07-30 | 67056a2 |
| OIC-003 | Added sanitized history/mapping attribution with explicit status, confidence, source, and coverage. | 2026-07-30 | ab46a73 |
| OIC-004 | Added separate recorded/list-price costs, effective-dated rates, provenance, coverage, and statistics. | 2026-07-30 | 85ab5b8 |
| OIC-005 | Added coherent JSON/Markdown/manifest CLI output and end-to-end recovery tests. | 2026-07-30 | 67056a2 |
