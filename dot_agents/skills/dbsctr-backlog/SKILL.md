---
name: dbsctr-backlog
description: Show durable P2/P3 autonomous-improvement claims waiting for operator review without changing worker, claim, or delivery state.
---

# DBSCTR Backlog

Read `dbsctr_improvement_status` without a worker filter. Validate that every
returned worker has a safe worker ID, state, and optional P0-P3 priority.

Report only workers whose state is `claimed` and priority is P2 or P3, ordered by
priority then creation time. For each, show worker ID, priority, sanitized summary,
and age. Never expose private history, source paths, claim hashes, session
availability, or presentation identifiers.

This skill is report-only. Do not reprioritize, advance, recover, abandon, launch,
merge, release, deploy, or mutate review markers. A separate promotion contract
is required before a waiting claim can enter Discovery; the only current operator
mutation is explicit abandonment through the normal recovery command. If none
wait, report `No P2/P3 claims waiting.`
