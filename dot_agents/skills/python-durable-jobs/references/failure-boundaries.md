# Failure boundaries

Use this matrix to select tests for the repository's actual queue/store contract.
Do not add every mechanism to a project whose required semantics are simpler.

| Interruption point | Evidence needed |
|---|---|
| Domain commit before publication | Coupled durable intent remains recoverable; rolled-back updates do not dispatch |
| Publish succeeded but confirmation was lost | Dispatcher can retry without losing the intent; consumer handles duplicates |
| Two deliveries claim the same operation | Atomic ownership or deduplication permits only the contract's allowed effects |
| Worker pauses past lease/visibility expiry | Reclaim is possible; stale-owner effects/completion are rejected or reconciled |
| Effect succeeds before completion/acknowledgement | Redelivery observes durable completion or reconciles the remote effect |
| Retry budget or deadline expires | Terminal outcome remains visible; original failure is not reported as success |
| Poison-job transfer fails | Original delivery remains recoverable; transfer does not silently discard work |
| Deployment has old queued payloads | Old/new workers decode compatible messages or perform an explicit migration |

Use controlled clocks for handler/state-machine tests and selected backend
integration tests for actual concurrency and crash recovery. Retain failure
evidence; do not claim fault tolerance from static code review. Live fault
injection, redrive, broker changes and message publication need the task's actual
authorization and bounded scope.

## Celery when selected

Inspect the installed Celery version, transport, worker pool, persistence,
acknowledgement settings and failure behavior. The default is acknowledgement
before execution. `acks_late` delays acknowledgement until a task returns, but
child-process termination can still be acknowledged; `task_reject_on_worker_lost`
changes that behavior and can cause repeated poison-job execution. Select settings
from the required recovery contract rather than universally enabling late ack.

Task retries and broker redelivery are different paths. Classify permanent versus
repeatable failures, include framework/transport retries in the budget and preserve
the task's terminal error semantics. Worker time limits can kill processes; use
client I/O timeouts and define reconciliation for partial effects.

`delay_on_commit()` is available in Celery 5.4+ for supported Django task classes;
it addresses the consumer seeing uncommitted state. Inference: because its callback
publishes after the database commit, it cannot by itself make a database update
and broker publication one durable atomic operation. Use a recoverable intent
record when the business contract requires that coupling.

Primary reference: [Celery tasks, acknowledgements, retries and transactions](https://docs.celeryq.dev/en/stable/userguide/tasks.html).

## Outbox and broker qualification

An outbox is appropriate when a single local transaction must persist both the
domain update and publication intent. Keep its retention, dispatch ordering,
replay, duplicate handling and stuck-record recovery explicit. It does not make
downstream external effects atomic with the originating database transaction.

For the selected broker, distinguish publisher confirmation from consumer
acknowledgement. Confirm that queue/message durability, replication and routing
failure handling meet the intended contract. Connection recovery can leave the
publication outcome ambiguous; duplicates remain possible. Evaluate the actual
broker's guarantees rather than treating all transports as interchangeable.

Primary references: [transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
and, when RabbitMQ is selected, [RabbitMQ reliability](https://www.rabbitmq.com/docs/reliability).

Expose queue age, attempt count, execution duration, lease/visibility expiry and
terminal/dead-letter outcomes using bounded labels and the project's telemetry
policy. Payloads and exception strings can contain secrets. Keep enough durable
identity and state for reconciliation without logging complete job arguments.
