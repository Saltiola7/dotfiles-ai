---
name: python-observability
license: MIT
description: Design and review Python logs, metrics and traces, including correlation context, bounded labels and sensitive-data handling when instrumentation changes.
---

# Python Observability

## Project and workflow boundaries

Apply this guidance within the current task and project Engineering Profile.
Project-selected runtimes, dependencies, tools, error contracts and acceptance
criteria control examples. Loading this skill does not install tools or authorize
external operations. Existing authorization persists; ask only about unresolved
material decisions. DBSCTR retains phase and gate ownership; QA retains configured
validation and evidence ownership. Return scoped findings, affected artifacts,
supporting evidence and limitations. See [UPSTREAM.md](UPSTREAM.md) for provenance.

Design telemetry around the operational question and selected project stack.
Keep an existing logging/tracing provider; adding structlog, Prometheus or an
exporter is a project decision, not a prerequisite of loading this skill. Do not
install dependencies, attach to production or send telemetry externally without
the task's existing authority.

Use allowlisted fields. Exception messages, repr/serialization, URLs, SQL and
parameters, headers, tokens and user identifiers can contain sensitive data.
Record safe classifications/counts; inspect sinks and apply project redaction and
retention. Compose `secret-serialization` when credential holders or whole-object
logging change. A redacted display does not prove other exporters are safe.

Bound metric cardinality at every label: use registered route templates, normalized
methods, finite error groups and approved buckets. Keep request IDs in permitted
logs/traces rather than metric labels. Distinguish handler return, full stream
completion, cancellation and errors. A source-level instrumentation pattern does
not prove delivery, dashboard correctness or incident detection.

Bind correlation context for its actual request/job lifetime and restore it in
finally, including errors and cancellation. Validate incoming IDs according to
trust policy; do not blindly echo arbitrary headers. Verify propagation across
async/sync/thread and queued-job boundaries with the selected framework.
Inspect the actual logs/spans/metrics using isolated tests before making claims.

## When to Use This Skill

- Adding structured logging to applications
- Implementing metrics collection with Prometheus
- Setting up distributed tracing across services
- Propagating correlation IDs through request chains
- Debugging production issues
- Building observability dashboards

## Core Concepts

### 1. Structured Logging

Emit logs as JSON with consistent fields for production environments. Machine-readable logs enable powerful queries and alerts. For local development, consider human-readable formats.

### 2. The Four Golden Signals

Select latency, traffic, errors and saturation signals for the boundaries that matter under the project observability policy.

### 3. Correlation IDs

Thread a unique ID through all logs and spans for a single request, enabling end-to-end tracing.

### 4. Bounded Cardinality

Keep metric label values bounded. Unbounded labels (like user IDs) explode storage costs.

## Quick Start

```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()
logger.info("Request processed", operation="status_read", duration_ms=45)
```

## Fundamental Patterns

### Pattern 1: Structured Logging with Structlog

Configure structlog for JSON output with consistent fields.

```python
import logging
import structlog

def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Initialize at application startup
configure_logging("INFO")
logger = structlog.get_logger()
```

### Pattern 2: Consistent Log Fields

Every log entry should include standard fields for filtering and correlation.

```python
import time
import structlog
from contextvars import ContextVar

# Store correlation ID in context
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

logger = structlog.get_logger()

def process_request(request: Request) -> Response:
    """Process request with structured logging."""
    start = time.perf_counter()
    logger.info(
        "Request received",
        correlation_id=correlation_id.get(),
        method=request.method,
        path=request.path,
    )

    try:
        result = handle_request(request)
        logger.info(
            "Request completed",
            correlation_id=correlation_id.get(),
            status_code=result.status_code,
            duration_ms=(time.perf_counter() - start) * 1000,
        )
        return result
    except Exception as e:
        logger.error(
            "Request failed",
            correlation_id=correlation_id.get(),
            error_type=type(e).__name__,
        )
        raise
```

### Pattern 3: Semantic Log Levels

Use log levels consistently across the application.

| Level | Purpose | Examples |
|-------|---------|----------|
| `DEBUG` | Development diagnostics | Variable values, internal state |
| `INFO` | Request lifecycle, operations | Request start/end, job completion |
| `WARNING` | Recoverable anomalies | Retry attempts, fallback used |
| `ERROR` | Failures needing attention | Exceptions, service unavailable |

```python
# DEBUG: Detailed internal information
logger.debug("Cache lookup", hit=cache_hit)

# INFO: Normal operational events
logger.info("Order created", operation="create_order")

# WARNING: Abnormal but handled situations
logger.warning(
    "Rate limit approaching",
    current_rate=950,
    limit=1000,
    reset_seconds=30,
)

# ERROR: Failures requiring investigation
logger.error(
    "Payment processing failed",
    error_type=type(e).__name__,
    payment_provider="stripe",
)
```

Choose levels through project operational/security policy. Expected user mistakes
need not page an operator; security-relevant authentication failures may still
require a dedicated event. Avoid claiming one universal severity for them.

### Pattern 4: Correlation ID Propagation

Generate or validate an ID at ingress and propagate it only across intended
boundaries. This handler-scoped example restores both context stores on exit;
stream/background work may outlive the handler and needs its own scope. See
[structlog context variables](https://www.structlog.org/en/stable/contextvars.html)
for token restoration and hybrid sync/async isolation limitations.

```python
from contextlib import contextmanager
from contextvars import ContextVar
import uuid
import structlog
from fastapi import Request

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

@contextmanager
def request_context(cid: str):
    token = correlation_id.set(cid)
    try:
        with structlog.contextvars.bound_contextvars(correlation_id=cid):
            yield
    finally:
        correlation_id.reset(token)

async def correlation_middleware(request: Request, call_next):
    """Illustrate scoped handler context; verify framework/stream lifetimes."""
    # Generate locally. Accept upstream IDs only under an explicit validation policy.
    cid = uuid.uuid4().hex
    with request_context(cid):
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
```

Propagate to outbound requests:

```python
import httpx

async def call_downstream_service(endpoint: str, data: dict) -> dict:
    """Call downstream service with correlation ID."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            json=data,
            headers={"X-Correlation-ID": correlation_id.get()},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
```

## Detailed worked examples and patterns

Detailed sections (starting with `## Advanced Patterns`) live in `references/details.md`. Read that file when the navigation summary above is insufficient.

## Best Practices Summary

1. **Use structured logging** - JSON logs with consistent fields
2. **Propagate correlation IDs** - Thread through all requests and logs
3. **Track the four golden signals** - Latency, traffic, errors, saturation
4. **Bound label cardinality** - Never use unbounded values as metric labels
5. **Log at appropriate levels** - Don't cry wolf with ERROR
6. **Allowlist context** - Include only safe operation fields permitted by sink policy
7. **Use context managers** - Consistent timing and error handling
8. **Separate concerns** - Observability code shouldn't pollute business logic
9. **Test your observability** - Verify logs and metrics in integration tests
10. **Verify the intended use** - Confirm collection and configured alerts where required
