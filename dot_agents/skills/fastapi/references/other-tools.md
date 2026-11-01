# Other Tools

Preserve project-selected package managers, checkers, event-loop boundaries, ORM
and HTTP clients. Availability of an alternative does not justify adoption or
a migration; the commands and examples below are conditional on explicit scope.

## uv

Use the existing dependency owner. uv is one option when already selected.

## Ruff

Use configured lint/format commands. Ruff FastAPI rules may help when Ruff is
already selected; enabling additional rules is a separate configuration choice.

## ty

Use the configured checker. ty availability does not authorize replacing mypy,
Pyright or another established checker.

## Asyncer

When mixing blocking and asynchronous calls, inspect existing AnyIO/asyncio/
Starlette offloading and cancellation policy first. Asyncer is an optional adapter,
not a required replacement for `run_in_threadpool()` or another working boundary.
Verify concurrency limits and cancellation/resource ownership. If Asyncer is
explicitly selected, dependency-owner syntax might be:

```bash
uv add asyncer
```

Run blocking sync code inside of async with `asyncify()`:

```python
from asyncer import asyncify
from fastapi import FastAPI

app = FastAPI()


def do_blocking_work(name: str) -> str:
    # Some blocking I/O operation
    return f"Hello {name}"


@app.get("/items/")
async def read_items():
    result = await asyncify(do_blocking_work)(name="World")
    return {"message": result}
```

And run async code inside of blocking sync code with `syncify()`:

```python
from asyncer import syncify
from fastapi import FastAPI

app = FastAPI()


async def do_async_work(name: str) -> str:
    return f"Hello {name}"


@app.get("/items/")
def read_items():
    result = syncify(do_async_work)(name="World")
    return {"message": result}
```

## SQLModel for SQL databases

SQLModel is one possible SQL boundary when deliberately selected. Preserve
SQLAlchemy or another established client, schema owner and transaction policy.
Sharing validation and persistence models is optional and can expose unwanted
fields; keep public response contracts deliberate. No database actions are implied.

## HTTPX

HTTPX supports sync and async HTTP. Preserve an existing Requests or other client
when appropriate; do not call a blocking client directly from an async handler.
Reuse app-owned pools when selected, close owned clients, set deadlines and keep
credentials out of diagnostics. Local examples do not authorize remote requests.
