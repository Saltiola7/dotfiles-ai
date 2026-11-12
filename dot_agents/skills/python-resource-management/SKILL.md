---
name: python-resource-management
license: MIT
description: Design and review Python resource ownership, acquisition failure, deterministic cleanup and bounded streaming for files, connections and borrowed handles.
---

# Python Resource Management

## Project and workflow boundaries

Apply this guidance within the current task and project Engineering Profile.
Project-selected runtimes, dependencies, tools, error contracts and acceptance
criteria control examples. Loading this skill does not install tools or authorize
external operations. Existing authorization persists; ask only about unresolved
material decisions. DBSCTR retains phase and gate ownership; QA retains configured
validation and evidence ownership. Return scoped findings, affected artifacts,
supporting evidence and limitations. See [UPSTREAM.md](UPSTREAM.md) for provenance.

Make resource ownership explicit: who acquires, borrows, transfers and closes
each handle, client, session, iterator or pool? Close owned resources; do not close
borrowed or shared handles without their owner's contract. Use the selected
driver's native connection/transaction contexts rather than assuming `with`
commits, closes, rolls back or returns a connection identically across libraries.

Review failure before entry completes, failure inside the body, commit/close
failure, early stream termination and cancellation. Register cleanup immediately
after each acquisition; an unsuccessful `__enter__` does not trigger that object's
`__exit__`. Attempt remaining cleanup when one action fails, preserve the primary
failure/secondary context, and report unknown transaction outcomes. Bounded async
cleanup follows the project's cancellation semantics; do not create detached
cleanup tasks or silently swallow cancellation.

Separate incremental transport from retaining a full result. Bound buffers,
open handles, outstanding work and shutdown time using project requirements.
Compose `async-python-patterns` for task ownership and the selected database lens
for driver/engine behavior. Test ownership and cleanup paths; an apparently clean
source pattern alone does not establish successful resource release.

## When to Use This Skill

- Managing database connections and connection pools
- Working with file handles and I/O
- Implementing custom context managers
- Building streaming responses with state
- Handling nested resource cleanup
- Creating async context managers

## Core Concepts

### 1. Context Managers

After successful entry, `with` invokes the exit protocol for normal or exceptional body completion; actual release depends on that implementation.

### 2. Protocol Methods

`__enter__`/`__exit__` for sync, `__aenter__`/`__aexit__` for async resource management.

### 3. Unconditional Cleanup

`__exit__` runs after successful `__enter__`; entry failure and abrupt process termination require separate handling and cannot promise cleanup.

### 4. Exception Handling

Return `True` from `__exit__` to suppress exceptions, `False` to propagate them.

## Quick Start

```python
from contextlib import contextmanager

@contextmanager
def managed_resource():
    resource = acquire_resource()
    try:
        yield resource
    finally:
        resource.cleanup()

with managed_resource() as r:
    r.do_work()
```

## Fundamental Patterns

### Pattern 1: Class-Based Context Manager

Prefer an existing resource's native context manager. This illustrative wrapper
owns only the connection it creates; its close behavior is not a universal
transaction contract. The query method is project-specific. Verify the selected
driver's commit/rollback, pooling and close semantics before adapting it.

```python
class DatabaseConnection:
    """Database connection with automatic cleanup."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: Connection | None = None

    def connect(self) -> None:
        """Establish database connection."""
        self._conn = psycopg.connect(self._dsn)

    def close(self) -> None:
        """Close connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "DatabaseConnection":
        """Enter context: connect and return self."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context: always close connection."""
        self.close()

# Usage with context manager (preferred)
with DatabaseConnection(dsn) as db:
    result = db.execute(query)

# Manual management when needed
db = DatabaseConnection(dsn)
db.connect()
try:
    result = db.execute(query)
finally:
    db.close()
```

### Pattern 2: Async Context Manager

For async resources, implement the async protocol.

```python
class AsyncDatabasePool:
    """Async database connection pool."""

    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool | None = None

    async def __aenter__(self) -> "AsyncDatabasePool":
        """Create connection pool."""
        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close all connections in pool."""
        if self._pool is not None:
            await self._pool.close()

    async def execute(self, query: str, *args) -> list[dict]:
        """Execute query using this owned pool (illustrative driver shape)."""
        if self._pool is None:
            raise RuntimeError("Pool has not been entered")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

# Usage
async with AsyncDatabasePool(dsn) as pool:
    users = await pool.execute("SELECT * FROM users WHERE active = $1", True)
```

### Pattern 3: Using @contextmanager Decorator

Simplify context managers with the decorator for straightforward cases.

```python
from contextlib import contextmanager, asynccontextmanager
import time
import structlog

logger = structlog.get_logger()

@contextmanager
def timed_block(name: str):
    """Time a block of code."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info("Timed block exited", operation=name, duration_seconds=round(elapsed, 3))

# Usage
with timed_block("data_processing"):
    process_large_dataset()

@asynccontextmanager
async def database_transaction(conn: AsyncConnection):
    """Borrow a connection using its selected driver's native transaction API."""
    # Illustrative asyncpg-style API; other drivers differ.
    async with conn.transaction():
        yield conn

# Usage
async with database_transaction(conn) as tx:
    await tx.execute("INSERT INTO users ...")
    await tx.execute("INSERT INTO audit_log ...")
```

### Pattern 4: Release on Every Managed Exit

After successful entry, attempt owned cleanup for both success and failure.
ExitStack supports partial acquisition and reverse-order unwinding. Cleanup
exceptions can still affect the propagated exception; preserve their chain and
apply the project's error policy rather than declaring cleanup successful.

```python
from contextlib import ExitStack
from pathlib import Path
from types import TracebackType
from typing import IO

class FileProcessor:
    """Illustrate ownership of a file acquired during entry."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._file: IO[str] | None = None
        self._stack = ExitStack()

    def __enter__(self) -> "FileProcessor":
        try:
            self._file = self._stack.enter_context(open(self._path, "r"))
            return self
        except BaseException:
            self._stack.close()
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return self._stack.__exit__(exc_type, exc_val, exc_tb)
```

## Detailed worked examples and patterns

Detailed sections (starting with `## Advanced Patterns`) live in `references/details.md`. Read that file when the navigation summary above is insufficient.

## Best Practices Summary

1. **Assign ownership** - Prefer native context managers for owned resources
2. **Cover acquisition and exit** - Failed entry needs its own cleanup path
3. **Don't suppress unexpectedly** - Return `False` unless suppression is intentional
4. **Use @contextmanager** - For simple resource patterns
5. **Expose only needed protocols** - Do not add manual lifecycle APIs without a use case
6. **Use ExitStack** - For dynamic numbers of resources
7. **Bound accumulation** - Incremental transport need not retain a complete response
8. **Describe completion** - Early termination, empty streams and cleanup failures remain distinct
9. **Document behavior** - Especially exception suppression
10. **Test cleanup paths** - Verify resources are released on errors
