---
name: python-resilience
license: MIT
description: Design and review Python retries, deadlines and degraded results when external calls fail, preserving idempotency, cancellation and project error contracts.
---

# Python Resilience Patterns

## Project and workflow boundaries

Apply this guidance within the current task and project Engineering Profile.
Project-selected runtimes, dependencies, tools, error contracts and acceptance
criteria control examples. Loading this skill does not install tools or authorize
external operations. Existing authorization persists; ask only about unresolved
material decisions. DBSCTR retains phase and gate ownership; QA retains configured
validation and evidence ownership. Return scoped findings, affected artifacts,
supporting evidence and limitations. See [UPSTREAM.md](UPSTREAM.md) for provenance.

Design resilience from the operation's contract, not from exception names alone.
Before retrying, establish replay safety: reads may be repeatable; writes require
an idempotency key/deduplication contract or proof that no effect occurred. A
network timeout or lost commit acknowledgement can leave an ambiguous result.
Reconcile that result; do not blindly replay a write, transaction or ingestion job.

Choose one retry owner and count retries already performed by drivers, SDKs,
proxies and job schedulers. Bound total attempts, per-attempt work, waits and the
caller's remaining deadline. `stop_after_delay` limits retry scheduling after an
attempt; it does not interrupt an in-flight call or guarantee a hard deadline.
Use the selected client's timeout/deadline support and propagate cancellation.
Honor service retry hints within the caller's budget. Release a response/stream
before another attempt and preserve the original terminal failure contract.

Tenacity/httpx below are optional examples when selected. Keep existing driver
retry/error handling and project dependency choices. Test retry classification,
ambiguous outcomes, duplicate effects, cancellation and exhausted budgets with
controlled clocks and isolated dependencies. Static inspection alone cannot prove
fault tolerance or recovery time.

## When to Use This Skill

- Adding retry logic to external service calls
- Implementing timeouts for network operations
- Building fault-tolerant microservices
- Handling rate limiting and backpressure
- Creating infrastructure decorators
- Designing circuit breakers

## Core Concepts

### 1. Transient vs Permanent Failures

Retry transient errors (network timeouts, temporary service issues). Don't retry permanent errors (invalid credentials, bad requests).

### 2. Exponential Backoff

Increase wait time between retries to avoid overwhelming recovering services.

### 3. Jitter

Add randomness to backoff to prevent thundering herd when many clients retry simultaneously.

### 4. Bounded Retries

Cap both attempt count and total duration to prevent infinite retry loops.

## Quick Start

This example retries an explicitly repeatable read for selected transport failures;
it borrows a caller-owned client. Its timing values illustrate policy, not a hard
end-to-end deadline. It does not retry HTTP status or decoding failures.

```python
import httpx
from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, stop_after_delay,
    wait_exponential_jitter,
)

@retry(
    retry=retry_if_exception_type((httpx.ConnectTimeout, httpx.ReadTimeout)),
    stop=stop_after_attempt(3) | stop_after_delay(10),
    wait=wait_exponential_jitter(initial=0.1, max=1),
    reraise=True,
)
def read_status(client: httpx.Client, url: str) -> httpx.Response:
    response = client.get(url, timeout=3)
    response.raise_for_status()
    return response
```

## Fundamental Patterns

### Pattern 1: Basic Retry with Tenacity

Use the project's existing retry owner. Tenacity is one optional implementation;
adding it or stacking it over a retrying SDK needs a justified project decision.

```python
from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential_jitter,
    retry_if_exception_type,
)

import httpx

TRANSIENT_ERRORS = (httpx.ConnectTimeout, httpx.ReadTimeout)

@retry(
    retry=retry_if_exception_type(TRANSIENT_ERRORS),
    stop=stop_after_attempt(5) | stop_after_delay(60),
    wait=wait_exponential_jitter(initial=1, max=30),
    reraise=True,
)
def fetch_data(url: str) -> dict:
    """Fetch data with automatic retry on transient failures."""
    response = httpx.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
```

### Pattern 2: Retry Only Appropriate Errors

Classify retryable failures for the actual operation and provider. Do not treat
all `OSError` or all client/server status codes alike. Invalid inputs, parsing bugs
and unauthorized requests usually need correction rather than another attempt.
Statuses such as 408, 409 or 429 require API-specific replay and recovery semantics;
even a transient status does not make an arbitrary write safe to replay.

```python
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter
import httpx

# Define what's retryable
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
)

@retry(
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
)
def resilient_api_call(endpoint: str) -> dict:
    """Make API call with retry on network issues."""
    return httpx.get(endpoint, timeout=10).json()
```

### Pattern 3: HTTP Status Code Retries

For an operation already proven repeatable, retry only the selected statuses.
Result-based exhaustion raises Tenacity's RetryError unless an explicit terminal
callback maps the outcome. Preserve the project's expected error/result shape;
do not report exhausted retries as success.

```python
from tenacity import retry, retry_if_result, stop_after_attempt, wait_exponential_jitter
import httpx

RETRY_STATUS_CODES = {429, 502, 503, 504}

def should_retry_response(response: httpx.Response) -> bool:
    """Check if response indicates a retryable error."""
    return response.status_code in RETRY_STATUS_CODES

@retry(
    retry=retry_if_result(should_retry_response),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
)
def http_request(url: str) -> httpx.Response:
    """Illustrate result-based retry for a repeatable read."""
    return httpx.get(url, timeout=30)
```

### Pattern 4: Combined Exception and Status Retry

Handle both network exceptions and HTTP status codes.

```python
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential_jitter,
)
import logging
import httpx

logger = logging.getLogger(__name__)

TRANSIENT_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
)
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

def is_retryable_response(response: httpx.Response) -> bool:
    return response.status_code in RETRY_STATUS_CODES

def log_retry(state) -> None:
    # Do not serialize request arguments, URLs, headers or raw exception text.
    logger.warning("Retry scheduled", extra={"attempt": state.attempt_number})

@retry(
    retry=(
        retry_if_exception_type(TRANSIENT_EXCEPTIONS) |
        retry_if_result(is_retryable_response)
    ),
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=1, max=30),
    before_sleep=log_retry,
)
def robust_http_call(url: str) -> httpx.Response:
    """Illustrate transport and status retry for a repeatable read."""
    return httpx.get(url, timeout=30)
```

## Detailed worked examples and patterns

Detailed sections (starting with `## Advanced Patterns`) live in `references/details.md`. Read that file when the navigation summary above is insufficient.

## Best Practices Summary

1. **Retry only transient errors** - Don't retry bugs or authentication failures
2. **Use exponential backoff** - Give services time to recover
3. **Add jitter** - Prevent thundering herd from synchronized retries
4. **Bound the full budget** - Attempt limits and retry stops do not interrupt in-flight calls
5. **Expose bounded retry signals** - Use safe fields and project logging/sampling policy
6. **Use decorators** - Keep retry logic separate from business logic
7. **Inject dependencies** - Make infrastructure testable
8. **Set timeouts everywhere** - Every network call needs a timeout
9. **Honor degraded-result contracts** - Use fallback only where explicitly permitted and observable
10. **Monitor retry rates** - High retry rates indicate underlying issues
