# Resource ownership and focused verification

Distinguish application lifetime (shared connection pools/clients), request lifetime
(dependency resources), and response-iterator lifetime (stream resources). Preserve
existing ownership and startup/shutdown policy. Use `lifespan` for app-owned
resources when the project selects that pattern; dependency injection can expose
them without creating one new pool per request. Do not start a service or contact
an endpoint as a side effect of reading this guidance.

For example, with an existing HTTPX dependency and compatible FastAPI:

```python
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Request


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=5.0) as client:
        app.state.http_client = client
        try:
            yield
        finally:
            del app.state.http_client


app = FastAPI(lifespan=lifespan)


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


HTTPClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]
```

This illustrates construction/cleanup and does not make any HTTP requests. Timeouts
and pool limits must match actual requirements; one number is not a universal policy.
Do not use a borrowed resource after app shutdown. Dependency caching is normally
request-local; it is not a substitute for an app-owned pool.

## Useful offline checks

With the project's existing in-process test client and synthetic resources:

- Exercise lifespan entry and exit, asserting cleanup on normal and failed requests.
- Check status, headers, media type, valid/invalid input and emitted public fields.
- Verify synchronous blocking handlers/dependencies use the intended boundary;
  an `async def` wrapper does not make a synchronous query nonblocking.
- Assert allowed private-field exclusion for model responses and explicitly test
  custom `Response` paths, which bypass filtering.
- For streaming, test iterator cleanup and application framing. Add appropriate
  transport tests only when proxy/disconnect behavior is part of the change.

Enter the test client's context when lifespan execution matters. A fake client or
resource proves that local path only; it is not evidence of real authentication,
database transactions, production concurrency or deployment health. Preserve the
owning test runner and report missing dependency/runtime coverage without installing
packages automatically.
