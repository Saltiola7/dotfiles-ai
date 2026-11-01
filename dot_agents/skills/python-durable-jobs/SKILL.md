---
name: python-durable-jobs
description: Design and review Python durable queue and worker boundaries for enqueue, claims, redelivery, idempotency and crash recovery when persistent background execution is selected.
---

# Python Durable Jobs

Use for actual durable queue/worker behavior or its repository audit. Preserve the
selected queue, broker, database, worker framework and delivery contract. Ordinary
async tasks or request-local background callbacks are not durable execution.
Databricks platform task graphs remain the platform specialist's responsibility.

## Trace one job across failure boundaries

Identify producer commit, durable enqueue acknowledgement, reservation/claim,
execution, effect commit, completion record and message acknowledgement. Record
which component owns each transition, what survives a crash and what can repeat.
Read actual broker/framework configuration and versions; a task decorator does
not establish delivery guarantees. Keep payload schemas versioned and compatible
with old queued messages and workers during rollout.

## Enqueue and claim atomically where required

When a domain update must imply a job, use a transactionally coupled job record,
outbox or an equivalent proven facility. Writing domain state and then calling
enqueue has a crash gap. An after-commit callback fixes early-consumption races
but alone does not guarantee durable publication. Outbox dispatch can duplicate;
confirm publication before marking dispatch complete and retain recovery ownership.

For store-backed workers, acquire a claim atomically through the selected store's
conditional write/locking primitive. A read followed by an unconditional update
does not exclude another worker. Define lease renewal, expiry, reclaim and stale
owner behavior if leases are used. Fencing or conditional completion must reject
stale owners at the protected boundary; a timestamp or heartbeat alone cannot stop
an expired worker from writing. Broker reservations need their own documented
acknowledgement and redelivery semantics instead of an invented database lease.

## Make replay and acknowledgement explicit

- Use a stable business-operation identity for idempotency. Reject incompatible
  payloads under the same key and define replay across payload-version changes;
  adding a schema version to the key can allow the same effect twice. Enforce
  uniqueness/conditional state transitions atomically; a check-before-write cache
  is insufficient under concurrent delivery. Keep deduplication state long enough
  for the permitted redelivery/replay horizon.
- Couple a local effect and its completion/deduplication record in the same
  transaction when possible. Remote effects require a provider idempotency or
  reconciliation contract. A timeout can mean the effect happened; retrying or
  marking success without resolving that ambiguity can corrupt results.
- Acknowledge according to the selected durability contract, after the required
  durable state transition. Early and late acknowledgements have different crash
  behavior. Neither a result backend nor an idempotency key alone proves exactly
  once execution or effects.
- Define cancelled, retryable, terminal and ambiguous outcomes separately. Returning
  normally after a failed effect can acknowledge it as success. A poison-job or
  dead-letter handoff must be durable before discarding the original delivery.

## Bound recovery and verify it

Assign one retry owner across job framework, SDK and application. Bound attempts,
elapsed deadline, per-call timeouts, queue age, concurrency and prefetch. Define
graceful shutdown and recovery for abandoned work; cancellation or forced worker
death does not roll back external effects. Keep ordering and per-key concurrency
requirements explicit when redelivery or retries can reorder work.

Read [failure boundaries](references/failure-boundaries.md) for crash tests,
Celery-specific traps or outbox/broker evidence. Use isolated fixtures and the
existing selected harness. Eager/in-memory tests can check handler logic but do
not establish broker persistence, redelivery or recovery behavior.

Return concrete findings, durability assumptions, affected artifacts and actual
validation limits to the existing lifecycle/QA. Loading this skill does not start
workers, install a broker, publish messages or change live queue configuration.
