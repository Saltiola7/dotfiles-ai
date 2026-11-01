# python-observability — detailed worked examples

Follow the entrypoint's project stack, privacy, lifetime and evidence boundaries.
Telemetry examples are optional implementations, not permission to create an
external exporter, dashboard or alert. Avoid logging raw error text or arbitrary
caller fields. Instrumentation failures must not silently replace the operation's
primary failure; apply the project's telemetry failure policy.

## Advanced Patterns

### Pattern 5: The Four Golden Signals with Prometheus

Select relevant signals for the approved operational boundaries. Metric names and buckets below are illustrative:

```python
from prometheus_client import Counter, Histogram, Gauge

# Latency: How long requests take
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint", "status"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)

# Traffic: Request rate
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

# Errors: Error rate
ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "error_group"],
)

# Saturation: Resource utilization
DB_POOL_USAGE = Gauge(
    "db_connection_pool_used",
    "Number of database connections in use",
)
```

This example measures a handler boundary, not response-body delivery or a complete
stream lifetime. Select the framework's actual lifecycle hook for those signals.
The decorator declares a finite method/status/error vocabulary and records
cancellation separately; test the selected cancellation and error paths.

```python
import asyncio
import time
from functools import wraps

def track_request(func):
    """Decorator to track request metrics."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        method = request.method if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} else "OTHER"
        # Use the route template ("/users/{user_id}"), not the raw path,
        # so IDs in URLs do not create a new label value per request.
        # Inside a mounted sub-app this is the sub-app's own template, so
        # add a fixed per-app label if two mounts share route paths.
        route = request.scope.get("route")
        endpoint = route.path if route else "unmatched"
        start = time.perf_counter()
        status = "uncompleted"

        try:
            response = await func(request, *args, **kwargs)
            status = str(response.status_code)
            return response
        except asyncio.CancelledError:
            status = "cancelled"
            raise
        except Exception:
            status = "500"
            ERROR_COUNT.labels(
                method=method,
                endpoint=endpoint,
                error_group="unexpected",
            ).inc()
            raise
        finally:
            duration = time.perf_counter() - start
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint, status=status).observe(duration)

    return wrapper
```

### Pattern 6: Bounded Cardinality

Avoid labels with unbounded values to prevent metric explosion.

```python
# BAD: User ID has potentially millions of values
REQUEST_COUNT.labels(method="GET", user_id=user.id)  # Don't do this!

# GOOD: Bounded values only
REQUEST_COUNT.labels(method="GET", endpoint="/users", status="200")

# If you need per-user metrics, use a different approach:
# - Log the user_id and query logs
# - Use a separate analytics system
# - Bucket users by type/tier, in a metric that declares that label
REQUESTS_BY_TIER = Counter(
    "http_requests_by_tier_total",
    "HTTP requests by user tier",
    ["method", "endpoint", "user_tier"],
)
REQUESTS_BY_TIER.labels(
    method="GET",
    endpoint="/users",
    user_tier="premium",  # Bounded set of values
)
```

### Pattern 7: Timed Operations with Context Manager

Create a timing context for operations using a bounded operation name and
explicitly allowlisted extra fields. Arbitrary kwargs are not automatically safe.
The synchronous manager measures the body it surrounds; cancellation is not a
successful completion and may need a separate framework signal.

```python
from contextlib import contextmanager
import time
import structlog

logger = structlog.get_logger()

@contextmanager
def timed_operation(name: str, **extra_fields):
    """Context manager for timing and logging operations."""
    start = time.perf_counter()
    logger.debug("Operation started", operation=name, **extra_fields)

    try:
        yield
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "Operation failed",
            operation=name,
            duration_ms=round(elapsed_ms, 2),
            error_type=type(e).__name__,
            **extra_fields,
        )
        raise
    else:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Operation completed",
            operation=name,
            duration_ms=round(elapsed_ms, 2),
            **extra_fields,
        )

# Usage
with timed_operation("fetch_user_orders"):
    orders = await order_repository.get_by_user(user.id)
```

### Pattern 8: OpenTelemetry Tracing

Use the existing tracer/provider when present. Initialize a new provider only at
an application startup boundary when the project selects OpenTelemetry and the
export destination; do not replace process-global providers from reusable library
code. Flush/shutdown belongs to the application lifecycle. Sampling and sink
policy apply to span attributes and automatic instrumentation too.

**Note:** OpenTelemetry is actively evolving. Check the [official Python documentation](https://opentelemetry.io/docs/languages/python/) for the latest API patterns and best practices.

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def configure_tracing(service_name: str, otlp_endpoint: str) -> None:
    """Configure OpenTelemetry tracing."""
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

async def process_order(order_id: str) -> Order:
    """Process order with tracing."""
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("operation", "process_order")

        with tracer.start_as_current_span("validate_order"):
            validate_order(order_id)

        with tracer.start_as_current_span("charge_payment"):
            charge_payment(order_id)

        with tracer.start_as_current_span("send_confirmation"):
            send_confirmation(order_id)

        return order
```
