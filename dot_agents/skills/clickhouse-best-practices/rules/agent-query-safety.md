---
title: Bound Authorized Agent Queries
impact: CRITICAL
impactDescription: Bound scan, memory, runtime and output without changing the question
tags: [agent, safety, limits, timeout]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

## Bound Authorized Agent Queries

Apply [task boundaries](../SKILL.md#task-boundaries). These controls are for live
operations already covered by the request; static audits do not execute SQL.

Set appropriate supported runtime, scanned-row/byte, memory and result limits
using the selected role/tool/client policy. `LIMIT` bounds output, not aggregate,
sort, join or scanned work. Do not copy billion-row/100GB examples as safe
universal defaults. Choose limits from the actual source size and authorized
budget; preserve stricter existing settings.

Useful settings to verify against the selected server version include
`max_execution_time`, `max_rows_to_read`, `max_bytes_to_read`, `max_memory_usage`,
`max_result_rows`, `max_result_bytes` and relevant overflow modes. Enforcement can
occur at block boundaries and distributed semantics differ; don't promise exact
wall-clock cancellation or byte ceilings. Review actual effective profiles and
tool behavior rather than assuming Cloud/self-hosted defaults.

Prefer scoped metadata and non-executing plans before data scans. Narrow queries
where that preserves meaning; do not invent sort/partition filters solely to
satisfy a blanket rule. `count()` is not inherently cheap. If the required answer
exceeds budget, propose a plan, authorized larger scan or explicitly approximate
result rather than silently truncating correctness.

Partial results from overflow modes such as `break` must be labelled incomplete,
not a complete count, top-N or aggregate. Include the selected bounds and actual
execution/coverage in the report.

On timeouts or memory errors, inspect the plan and reduce real work within scope.
Do not repeatedly retry, raise shared limits, change profiles or disable controls.
For insert failures, distinguish confirmed rejection from unknown commit status;
retries need an idempotency/deduplication contract. Waiting for merges is not proof
that a write can safely be replayed.

Role-level limits/read-only access and quotas can provide stronger sustained
controls than per-query settings. Recommend them when useful, but creating or
changing roles, quotas or settings profiles is separate operational work.

References: [Query complexity](https://clickhouse.com/docs/operations/settings/query-complexity),
[settings profiles](https://clickhouse.com/docs/operations/settings/settings-profiles),
[quotas](https://clickhouse.com/docs/operations/quotas).
