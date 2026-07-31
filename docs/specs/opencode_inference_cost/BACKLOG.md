# Backlog - OpenCode Inference Cost Reporting

**Last updated:** 2026-07-30
**Critical path:** OIC-001 -> OIC-002 -> OIC-003 -> OIC-004 -> OIC-005

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| OIC-001 | Transfer and reconcile this specification in the dotfiles/DBSCTR repository | P0 | in_progress | - | `docs/specs/opencode_inference_cost/` | target repository instructions and telemetry source | false | The implementation profile and exact source paths must be verified in the owning repository. | S | Spec triplet present; profile paths and QA commands verified. |
| OIC-002 | Add read-only OpenCode schema capability probe and synthetic fixtures | P0 | in_progress | OIC-001 | target telemetry adapter and tests | OpenCode SQLite metadata only | false | Extraction cannot be correct until supported capabilities are proven without content reads. | M | Unsupported schemas fail; prohibited columns are never selected. |
| OIC-003 | Extract usage metadata and attribute it with DBSCTR context evidence | P0 | in_progress | OIC-002 | target reporting module and tests | OpenCode usage metadata, DBSCTR sanitized history | false | Attribution must preserve unknown and ambiguous usage before costing. | M | Reconciliation and all attribution-status tests pass. |
| OIC-004 | Resolve separate recorded and list-price costs and descriptive statistics | P0 | in_progress | OIC-003 | target reporting module, versioned rate card, tests | provider/model identity and token classes | false | Cost basis, effective date, and coverage must stay auditable. | M | Cost precedence, rate boundaries, nulls, quantiles, and skew tests pass. |
| OIC-005 | Add atomic JSON/Markdown report CLI and end-to-end fixture test | P0 | in_progress | OIC-004 | target CLI, renderer, tests | validated summaries | false | This completes the smallest usable reporting path. | M | Fixture command produces reconciling, content-free outputs. |
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
