# Async ownership across Python and Rust

Use this reference when futures, spawned tasks, callbacks or runtime shutdown
cross the boundary. A synchronous binding does not need a second async runtime.

## Identify the owners

Trace the calling asyncio loop, Rust executor, thread attachment and the owner of
each task and retained Python handle. Check the selected PyO3 bridge crate and
feature compatibility before reusing examples. Preserve an existing runtime;
neither a new runtime per call nor an intentionally leaked runtime is a default
solution. Establish initialization and shutdown ordering from actual ownership.

Create Python awaitables in the appropriate running-loop context. Check the
bridge's task-local/context propagation when calls leave that context or call
back into synchronous Python. Do not start a nested `asyncio.run()` in a thread
whose asyncio loop is already running, or hold attachment/locks across a wait
whose completion needs another Python callback.

Carry owned Rust values or appropriate retained handles into futures. A Python
object accessed by a worker still needs attachment to its owning interpreter;
`Send` bounds alone do not establish interpreter identity or lifetime. Avoid
retaining an attached Python token or borrowed object across an async suspension.

## Follow cancellation through the complete task graph

Distinguish the future converted by the bridge from children it spawns. The
documented `future_into_py` conversion propagates cancellation of its returned
Python future to the converted Rust future; that does not prove cleanup of an
independently spawned child or an external side effect.

Dropping a Tokio `JoinHandle` detaches its task, so background work can continue.
Where cancellation should stop children, retain task ownership, request the
appropriate cancellation and observe termination. Aborting an already running
`spawn_blocking` task does not stop it; use a workload-appropriate cooperative
stop or let its explicit owner await completion. Do not report a timeout or
cancellation request as completed cleanup.

Preserve the application's cancellation/error semantics. Closing a loop,
dropping the Rust runtime and finalizing an embedded interpreter are distinct
events. Stop or finish work that could call Python before its interpreter is
destroyed, and ensure any remaining handles/resources have a valid cleanup path.

## Focused verification

Exercise the affected direction of conversion, callback exceptions and relevant
completion/cancellation races. Observe owned task termination and resource
cleanup, not only the Python awaiter's return. Include repeated calls and
import/process exit or explicit runtime teardown when lifetime behavior changed.
Use bounded observations so a deadlock test can fail meaningfully.

## Official sources

Resolve these to the project's installed crate versions before applying recipes.
The versioned pages below were reviewed against the available 0.30 series; they
do not prescribe a dependency upgrade.

- [PyO3 async bridge conversion and cancellation](https://docs.rs/pyo3-async-runtimes/0.30.0/pyo3_async_runtimes/tokio/fn.future_into_py.html)
- [Bridge runtime initialization implementation](https://github.com/PyO3/pyo3-async-runtimes/blob/main/src/tokio.rs)
- [Tokio JoinHandle ownership and cancellation](https://docs.rs/tokio/1.54.1/tokio/task/struct.JoinHandle.html)
- [PyO3 parallelism and attachment](https://github.com/PyO3/pyo3/blob/v0.30.1/guide/src/parallelism.md)
