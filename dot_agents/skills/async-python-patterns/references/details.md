# Async Python: owned concurrency patterns

Use relevant sections only. Preserve the selected framework, runtime floor,
clients, dependency authority and validation commands. TaskGroup and
`asyncio.timeout()` examples require Python 3.11+; `to_thread()` requires 3.9+.
Newer APIs in the latest documentation may require later runtimes.

## Event-loop and task ownership

Calling an async function creates a coroutine; awaiting it or scheduling an owned
task performs the work. `asyncio.run()` is a top-level synchronous entrypoint,
not a way to nest another loop inside an async framework.

For related required work on Python 3.11+, scope children with a task group:

```python
import asyncio

async def required_pair(fetch_left, fetch_right):
    async with asyncio.TaskGroup() as group:
        left = group.create_task(fetch_left())
        right = group.create_task(fetch_right())
    return left.result(), right.result()
```

The owner waits for completion. A non-cancellation child failure cancels related
siblings and is propagated after cleanup; exception groups may need specific
domain handling at the boundary. Do not catch and discard the entire group merely
to make a result look successful.

On older supported runtimes, retain references, explicitly cancel remaining
owned children on failure/interruption, and await them before their scope exits.
Define how multiple failures are retained under that project's compatibility
contract. Do not silently raise the runtime floor to use a preferred recipe.

`gather()` suits finite known populations or deliberately collecting outcomes.
By default its first raised exception does not cancel all other awaitables;
the caller still needs their ownership/cleanup contract. With
`return_exceptions=True`, inspect every result and return/report failures as part
of an explicitly accepted partial-result contract. Dropping them and returning
only successes is not proof that the requested operation completed.

## Cancellation, deadlines and cleanup

Use `try/finally` for resources and normally propagate `CancelledError`. The
existing catch-and-reraise pattern remains appropriate when a boundary needs to
observe cancellation. This example exposes completion of its cleanup boundary:

```python
import asyncio

async def cancelable_task(stopped: asyncio.Event):
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        raise
    finally:
        stopped.set()

async def cancellation_probe():
    stopped = asyncio.Event()
    task = asyncio.create_task(cancelable_task(stopped))
    await asyncio.sleep(0)  # Allow this finite probe's child to enter its body.
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("cancellation was not propagated")
    assert stopped.is_set()
```

Cleanup failures can matter too; preserve them and the original failure according
to the boundary's error contract. Avoid blanket shielding, swallowed cancellation
or untracked cleanup tasks. Timeouts request cancellation, not instantaneous
termination of remote requests, subprocesses or running threads.

For a selected Python 3.11+ operation, an outer `asyncio.timeout(seconds)` can
bound the operation's awaited scope. `wait_for()` is also useful under its
supported-runtime contract; cancellation cleanup may extend observed elapsed
time. Distinguish the operation deadline, each request timeout and shutdown budget.
Retries still need safe/idempotent operations and a total attempt/time budget.

## Bounded producers and consumers

A semaphore around I/O does not bound millions of already-created tasks. Use a
fixed worker population and bounded queue, or stream results when the full
population should not be retained. This Python 3.11+ pattern bounds queued work
and task count and propagates producer/worker failures:

```python
import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar

Item = TypeVar("Item")
Result = TypeVar("Result")

async def bounded_map(
    items: Iterable[Item],
    worker: Callable[[Item], Awaitable[Result]],
    *,
    workers: int,
    queue_capacity: int,
) -> list[Result]:
    if workers < 1 or queue_capacity < 1:
        raise ValueError("workers and queue_capacity must be positive")
    queue: asyncio.Queue[tuple[int, Item] | None] = asyncio.Queue(queue_capacity)
    results: dict[int, Result] = {}

    async def produce() -> None:
        for index, item in enumerate(items):
            await queue.put((index, item))
        for _ in range(workers):
            await queue.put(None)

    async def consume() -> None:
        while True:
            entry = await queue.get()
            try:
                if entry is None:
                    return
                index, item = entry
                results[index] = await worker(item)
            finally:
                queue.task_done()

    async with asyncio.TaskGroup() as group:
        group.create_task(produce())
        for _ in range(workers):
            group.create_task(consume())
    return [results[index] for index in sorted(results)]
```

The result list still uses memory proportional to successful input size. Use a
bounded downstream sink or streaming interface when that is inappropriate.
Iteration itself must not block the loop; adapt blocking producers separately.
The worker's actual I/O, resource and cancellation contract remains significant.
Do not report an item as successfully processed merely because queue accounting
was completed in `finally`; a failed task group raises instead of returning data.

Select worker count, queue size, connection limits and total budgets from the
workload. A concurrency semaphore is not a time-based rate limiter; provider
quotas may also require pacing, token buckets or server-directed retry behavior.

## Async iterators, contexts and locks

Use `async with` for owned async resources and `async for` for asynchronous
streams. A consumer that stops early must close an owned generator/resource;
use the selected interface or a supported `contextlib.aclosing()` scope rather
than relying on garbage collection. Keep pagination and buffers bounded.

Async context managers acquire on entry and release on every exit path, including
errors and cancellation. Do not keep a connection/response beyond that lifetime.
When adapting a client, inspect its real close/transaction APIs rather than
copying the shape of a simulated client as if it were universal.

An `asyncio.Lock` serializes cooperating tasks on its owning event loop; it is
not an OS-thread or cross-process lock. Keep the critical section as small as the
consistency contract allows:

```python
import asyncio

class AsyncCounter:
    def __init__(self) -> None:
        self.value = 0
        self.lock = asyncio.Lock()

    async def increment(self) -> None:
        async with self.lock:
            self.value += 1

    async def get_value(self) -> int:
        async with self.lock:
            return self.value
```

If work arrives from another OS thread, use the loop's documented thread-safe
submission interfaces. Do not call loop APIs or mutate task-owned state directly
from an arbitrary thread.

## HTTP sessions and connection pools

Use the project's existing async HTTP client where possible. The following is an
aiohttp example only when that dependency is selected. Consume response data
before its response and session contexts close:

```python
import asyncio
import aiohttp

async def fetch_json(session: aiohttp.ClientSession, url: str):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json()

async def fetch_many(urls: list[str], *, deadline: float):
    async with asyncio.timeout(deadline):
        timeout = aiohttp.ClientTimeout(total=10)
        connector = aiohttp.TCPConnector(limit=5, limit_per_host=3)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            return await bounded_map(
                urls,
                lambda url: fetch_json(session, url),
                workers=5,
                queue_capacity=10,
            )
```

The numeric limits are illustrative, not acceptance thresholds. Define redirects,
payload size, trusted destinations, retries and error translation at the actual
boundary. Avoid logging bearer tokens, credential-bearing URLs, full sensitive
payloads or unredacted exception strings. A non-success HTTP status is not always
a transient failure; preserve the client's/domain's classification.

## Database pools and parameter binding

Use the selected driver's binding syntax for values. The following illustrates
asyncpg-style placeholders and pool acquisition; it does not select that driver:

```python
import asyncio

async def fetch_user(pool, user_id: int):
    async with pool.acquire() as connection:
        return await connection.fetchrow(
            "SELECT id, name FROM users WHERE id = $1", user_id
        )

async def fetch_orders(pool, user_id: int):
    async with pool.acquire() as connection:
        return await connection.fetch(
            "SELECT id, total FROM orders WHERE user_id = $1", user_id
        )

async def independent_user_data(pool, user_id: int):
    async with asyncio.TaskGroup() as group:
        user = group.create_task(fetch_user(pool, user_id))
        orders = group.create_task(fetch_orders(pool, user_id))
    return {"user": user.result(), "orders": orders.result()}
```

Each concurrent query owns a connection because many drivers cannot run concurrent
commands on one connection. If a consistent transaction snapshot is required,
use its transaction/connection contract, often with sequential queries. Parameter
binding handles values, not arbitrary SQL identifiers; type annotations do not
perform input validation or authorize query execution.

## WebSocket and background-service ownership

Register/unregister clients with `try/finally`; own each reader/writer task and
close connections at service shutdown. Snapshot a shared client set before
awaiting iteration over it, or use another explicit ownership strategy. Bound
per-client queues/messages and define backpressure or disconnect behavior for
slow peers. An unbounded broadcast gather or detached writer can exhaust memory
or outlive its connection.

Background tasks need references, observed exceptions and an owning startup/
shutdown scope. A framework's task manager/lifespan may be the right authority;
do not introduce a competing loop or lifecycle. A keepalive or reconnect policy
must preserve the application's deadline, idempotency and cancellation semantics.

## Blocking I/O and CPU work

For selected Python 3.9+, `asyncio.to_thread()` bridges blocking I/O:

```python
import asyncio
from pathlib import Path

async def read_file_async(path: str) -> str:
    return await asyncio.to_thread(Path(path).read_text, encoding="utf-8")
```

Under GIL-enabled CPython, this is not a universal CPU-parallelism recipe.
GIL-releasing extensions or other runtime configurations can change the choice;
verify the actual workload. Cancelling its awaiting task does not forcibly stop
a function already running in the thread. Continuing writes or requests still
need bounded ownership and recovery.

For actual CPU parallelism, a selected process pool may fit. Keep its lifetime
outside blocking event-loop shutdown paths and its callables/data compatible
with the platform's process-start method:

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

def cpu_work(value: int) -> int:
    return value * value

async def compute(pool: ProcessPoolExecutor) -> list[int]:
    loop = asyncio.get_running_loop()
    futures = [loop.run_in_executor(pool, cpu_work, value) for value in range(5)]
    return list(await asyncio.gather(*futures))

if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=2) as pool:
        print(asyncio.run(compute(pool)))
```

This is a finite illustrative workload; neither five jobs nor two workers is a
universal budget. Process cancellation/shutdown also has platform-specific limits.
Reuse a suitably owned executor instead of creating a thread pool per request.

## Validation and measurement

Use the existing async test harness, or run a stdlib async scenario from a normal
synchronous test when no loop is running. A selected pytest-asyncio plugin is one
option; loading this skill does not add it. Exercise successful results, child
failure, cancellation propagation/draining, finalization, deadline expiry, bounded
active work and large/streamed inputs. The `cancellation_probe()` above is a small
offline example, not proof of the consuming service's cleanup contract.

Use deterministic events/fakes for ordering and failure tests where possible;
arbitrary sleeps and external network services make timing evidence unreliable.
Measure performance under equivalent runtime, workload, concurrency, cache and
resource conditions with a baseline and variability. An async implementation,
connection pool or semaphore alone does not establish a speedup.

Primary authority: [Python asyncio tasks, cancellation and threads](https://docs.python.org/3/library/asyncio-task.html).
Read the documentation for the selected runtime; a newest-version example does
not establish compatibility with an older supported interpreter.
