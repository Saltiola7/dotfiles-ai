# python-resilience — detailed worked examples

Follow the entrypoint's replay-safety, cancellation, deadline and ownership
contract before using any example. Tool choices and timing values are illustrative.
Consult the selected [Tenacity version's documentation](https://tenacity.readthedocs.io/en/latest/)
for retry/terminal-result behavior and the actual client's timeout and exception
semantics. Never infer successful rollback or no remote effect from a timeout.

## Advanced Patterns

### Pattern 5: Logging Retry Attempts

Track retry behavior for debugging and alerting.

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger()

def log_retry_attempt(retry_state):
    """Log detailed retry information."""
    outcome = retry_state.outcome
    exception = outcome.exception() if outcome is not None and outcome.failed else None
    logger.warning(
        "Retrying operation",
        attempt=retry_state.attempt_number,
        exception_type=type(exception).__name__ if exception is not None else "result",
        next_wait_seconds=retry_state.next_action.sleep if retry_state.next_action else None,
    )

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    before_sleep=log_retry_attempt,
)
def call_with_logging() -> dict:
    """External call with retry logging."""
    ...
```

### Pattern 6: Timeout Decorator

Use the selected framework/client's timeout support where possible. The
illustrative async decorator cancels and waits for the inner coroutine; cleanup
can make elapsed time exceed `seconds`. It cannot stop arbitrary synchronous work
or undo a remote effect. Preserve cancellation and verify actual client semantics.

```python
import asyncio
from functools import wraps
from typing import TypeVar, ParamSpec
from collections.abc import Awaitable, Callable

T = TypeVar("T")
P = ParamSpec("P")

def with_timeout(seconds: float):
    """Decorator to add timeout to async functions."""
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=seconds,
            )
        return wrapper
    return decorator

@with_timeout(30)
async def fetch_with_timeout(url: str) -> dict:
    """Fetch URL with 30 second timeout."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### Pattern 7: Cross-Cutting Concerns via Decorators

Stack decorators to separate infrastructure from business logic.

```python
from functools import wraps
from typing import TypeVar, ParamSpec
from collections.abc import Awaitable, Callable
import structlog

logger = structlog.get_logger()
T = TypeVar("T")
P = ParamSpec("P")

def traced(name: str | None = None):
    """Add tracing to function calls."""
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        span_name = name or func.__name__

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            logger.info("Operation started", operation=span_name)
            try:
                result = await func(*args, **kwargs)
                logger.info("Operation completed", operation=span_name)
                return result
            except Exception as e:
                logger.error("Operation failed", operation=span_name, error_type=type(e).__name__)
                raise
        return wrapper
    return decorator

# Illustrative stack: UpstreamUnavailable is a project-classified repeatable-read failure.
# Decorator order determines whether timeout covers one attempt or the whole retry.
# Stack multiple concerns
@traced("fetch_user_data")
@with_timeout(30)
@retry(
    retry=retry_if_exception_type(UpstreamUnavailable),
    stop=stop_after_attempt(3), wait=wait_exponential_jitter(), reraise=True,
)
async def fetch_user_data(user_id: str) -> dict:
    """Fetch an explicitly repeatable read with one outer timeout budget."""
    ...
```

### Pattern 8: Dependency Injection for Testability

Pass infrastructure components through constructors for easy testing.

```python
from dataclasses import dataclass
from typing import Protocol

class Logger(Protocol):
    def info(self, msg: str, **kwargs) -> None: ...
    def error(self, msg: str, **kwargs) -> None: ...

class MetricsClient(Protocol):
    def increment(self, metric: str, tags: dict | None = None) -> None: ...
    def timing(self, metric: str, value: float) -> None: ...

@dataclass
class UserService:
    """Service with injected infrastructure."""

    repository: UserRepository
    logger: Logger
    metrics: MetricsClient

    async def get_user(self, user_id: str) -> User:
        self.logger.info("Fetching user")
        start = time.perf_counter()

        try:
            user = await self.repository.get(user_id)
            self.metrics.increment("user.fetch.success")
            return user
        except Exception as e:
            self.metrics.increment("user.fetch.error")
            self.logger.error("Failed to fetch user", error_type=type(e).__name__)
            raise
        finally:
            elapsed = time.perf_counter() - start
            self.metrics.timing("user.fetch.duration", elapsed)

# Easy to test with fakes
service = UserService(
    repository=FakeRepository(),
    logger=FakeLogger(),
    metrics=FakeMetrics(),
)
```

### Pattern 9: Contract-Defined Degraded Results

A fallback is a behavior change, not a generic error handler. Use it only when
project contracts allow degraded output, classify expected recoverable failures,
mark the fallback in the result/telemetry, and preserve other exceptions and
cancellation. Create fresh mutable defaults for every call.

```python
from functools import wraps
from typing import ParamSpec, TypeVar
from collections.abc import Awaitable, Callable

P = ParamSpec("P")
T = TypeVar("T")

def fail_safe(
    default_factory: Callable[[], T],
    recoverable: tuple[type[Exception], ...],
):
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except recoverable as error:
                logger.warning("Using permitted fallback", error_type=type(error).__name__)
                return default_factory()
        return wrapper
    return decorator

# Apply only to a project-defined error and a contract that permits empty results.
class RecommendationsUnavailable(Exception):
    pass

@fail_safe(default_factory=list, recoverable=(RecommendationsUnavailable,))
async def get_recommendations(user_id: str) -> list[str]:
    ...
```
