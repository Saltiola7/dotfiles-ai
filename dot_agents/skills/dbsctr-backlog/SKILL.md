---
name: dbsctr-backlog
description: Show durable P2/P3 autonomous-improvement claims waiting for operator review without changing worker, claim, or delivery state.
---

# DBSCTR Backlog

Read `dbsctr_improvement_status` without a worker filter. Validate that every
returned worker has a safe worker ID, state, and optional P0-P3 priority.

Report only workers whose state is `claimed` and priority is P2 or P3, ordered by
priority then creation time. For each, show worker ID, priority, sanitized summary,
age, and whether its original session remains available. Never expose private
history, source paths, claim hashes, or presentation identifiers.

This skill is report-only. Do not reprioritize, advance, recover, abandon, launch,
merge, release, deploy, or mutate review markers. Tell the operator to open the
worker's existing Herdr tab to continue or explicitly abandon it through the
normal recovery command. If none wait, report `No P2/P3 claims waiting.`
