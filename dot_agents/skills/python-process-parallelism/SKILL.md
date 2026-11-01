---
name: python-process-parallelism
description: Design and review Python process or subinterpreter pools, IPC, shared memory and child-process shutdown when those execution boundaries are selected or changing.
---

# Python Process Parallelism

Use for actual worker pools, process communication, shared-memory ownership or
child-process lifetime changes. Keep the project's supported Python versions,
operating systems, deployment limits and selected executor. A CPU-bound function
alone does not justify introducing parallelism or raising the runtime floor.

## Define the execution boundary

Identify the caller, worker owner, input/result sizes, ordering and partial-success
contract. Establish limits for workers, submitted work, retained results, IPC bytes
and shutdown time. Include native-library threads and container CPU/memory limits
when choosing the worker count; nested pools and BLAS/OpenMP threads can multiply
concurrency. Measure startup and serialization costs before claiming a speedup.

For process workers, use importable targets and an import-safe entrypoint. Lambdas,
REPL-local functions and live sessions/connections are not portable pool payloads.
Initialize worker-owned resources in the worker. Let library callers provide the
multiprocessing context; do not globally change the application's start method.
Keep synchronization primitives compatible with that context.

## Bound work and preserve failure semantics

- Bound submission as well as active workers. Collecting every `submit()` result
  before consumption still retains the entire population. On Python 3.14+,
  `Executor.map(buffersize=...)` provides submission backpressure; account for
  process `chunksize`, result sizes and ordered-result head-of-line blocking.
  On older versions, use a bounded pending set or the selected streaming API.
- Propagate worker exceptions and initialization failures. An abrupt worker exit
  can break the process pool; stop submitting and reconcile completed versus
  unknown work before rebuilding it. Retrying a side effect needs replay safety.
- Do not call executor/future methods from a task submitted to the same process
  pool. Avoid worker dependency cycles and waiting on work whose owner is blocked.
- Treat pickled IPC as a trusted-code boundary, not a format for untrusted input.
  Prefer explicit, versioned payloads; validate size and meaning at the boundary.

## Cancellation is not termination

`Future.cancel()` and `shutdown(cancel_futures=True)` affect work that has not
started; they do not stop running callables. A wait timeout does not stop a worker.
`shutdown(wait=False)` returns before completion but does not guarantee prompt
program exit. Exiting an executor context waits for its work.

Define cooperative stop signals, per-operation timeouts, grace period and an
explicit escalation owner. Python 3.14+ process-pool `terminate_workers()` and
`kill_workers()` affect the whole pool and preclude reuse. Forced termination can
leave partial external effects or damaged IPC/locks; it is not successful cleanup
or an individual-future cancellation mechanism. Earlier runtimes require a
supported owner-controlled strategy, not private executor internals.

## Specialized lifetimes and evidence

Read [runtime boundaries](references/runtime-boundaries.md) for selected start
methods, subinterpreters, shared-memory ownership or subprocess pipes. Do not apply
process-killing techniques to interpreter threads. Async callers retain their
event-loop contract; cancellation of an await does not stop the underlying worker.

Test the selected start method from an importable module, worker/initializer
failure, bounded input consumption, timeout, interruption and shutdown. Check
child reaping and resource cleanup, including failure during acquisition. Use
isolated fixtures and bounded workloads; static review does not prove throughput,
platform portability or absence of leaked children.

Return concrete findings, execution assumptions, affected interfaces and actual
validation limits. The existing lifecycle and QA retain gate ownership; loading
this skill does not launch workers, install tools or change application policy.
