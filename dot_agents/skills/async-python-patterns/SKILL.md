---
name: async-python-patterns
description: Design and review Python async task ownership, cancellation, bounded concurrency, resource lifetimes and sync/async boundaries when concurrent behavior changes.
---

# Async Python Patterns

Use for async APIs, concurrent I/O, queues, background work and changed event-loop
boundaries. Keep straightforward synchronous code when concurrency adds no value.
An async keyword or performance question alone does not justify an async rewrite.

## Establish the contract

Read the project runtime range, framework/loop owner, selected clients and test
authority. Identify required outcomes, partial-success policy, deadlines, resource
limits and who owns each task's completion and shutdown. Preserve those choices;
loading guidance neither installs a library nor raises the runtime floor.

| Concern | Decision |
|---|---|
| Concurrent I/O | Prefer an existing async client or a bounded blocking-I/O bridge |
| CPU work | Select processes, qualified GIL-releasing threads or synchronous work from the actual runtime/workload |
| Related required tasks | Structured ownership, failure propagation and awaited completion |
| Large input populations | Bounded workers/queues or streaming; bound allocated tasks as well as active I/O |
| Resources | Open, consume and close within an explicit owned lifetime |
| Framework integration | Use its event loop and startup/shutdown interfaces |

## Correctness before throughput

- Prefer `asyncio.TaskGroup` for related work when Python 3.11+ is supported.
  Its owner awaits all children and propagates failures; qualify newer methods
  against the selected runtime. Earlier runtimes need explicit ownership and
  cleanup, not an implicit upgrade.
- Propagate `CancelledError` after necessary cleanup. Use `try/finally` for owned
  resources; cancellation and timeouts are not successful completion. Cancelled
  children must be awaited/drained, and unexpected failures remain visible.
- `gather()` is useful for finite collections or a deliberate outcome-collection
  contract. Its first-error behavior does not give TaskGroup's sibling-cancellation
  guarantee. Inspect every result when exceptions are returned as values.
- A semaphore limits simultaneous work, not the number of allocated tasks or a
  requests-per-second quota. Use bounded queues/workers or streaming for large
  inputs; select independent rate and memory budgets when they matter.
- `asyncio.to_thread()` primarily bridges blocking I/O. CPU parallelism depends
  on GIL/runtime behavior; cancelling the await does not forcibly stop the thread.
  Keep any continuing external effects and shutdown obligations explicit.

## Boundaries and lifetimes

Do not call `asyncio.run()` from an already-running event loop or replace a
framework-owned loop. Use `await` within async code and an explicit adapter at
the supported synchronous boundary. Cross-thread work needs the documented
thread-safe loop APIs; asyncio locks do not protect arbitrary OS threads.

Keep response bodies, streams, transactions and connections within their owning
contexts. Returning an HTTP response after its session closes is not a usable
resource contract. Use the selected database driver's parameter binding; type
annotations are not runtime validation or permission to interpolate SQL values.

## Detail and validation

Read [worked patterns](references/details.md) when needed for TaskGroup,
cancellation, bounded producer/consumer work, locks, async iteration, HTTP/session
ownership, database pools, WebSocket cleanup, executors and tests. Load only the
relevant sections and qualify APIs against the project's supported versions.

Test required outcomes, child failure, interruption, deadline expiry, cleanup,
backpressure and selected sync/async entrypoints. Preserve the configured harness;
pytest-asyncio is an example choice, not a new dependency requirement. Performance
claims still need equivalent workloads, a baseline and correctness evidence.

Return affected interfaces, concrete findings, actual evidence and unresolved
limitations to the existing primary/QA. This specialist owns no separate gate,
coordinator, deployment or lifecycle workflow.
