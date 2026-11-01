# FastAPI

Adapted upstream FastAPI examples, loaded only for an actual selected FastAPI
boundary. Preserve the project's installed versions and choices. Examples involving
new frontend, telemetry, scope or streaming APIs require checking availability in
the installed release. These fragments are not a deployable application or
authorization to run servers, alter authentication or operate a database.

## Quick Reference

* Serve frontend apps: use `app.frontend()` or `router.frontend()` for built frontend assets; see [Serve Frontend Apps](#serve-frontend-apps).
* Server-Sent Events (SSE): use `response_class=EventSourceResponse` and `yield`; see [Streaming](#streaming-json-lines-sse-bytes) and [the streaming reference](streaming.md).
* JSON Lines and byte streaming: see [the streaming reference](streaming.md).
* OpenTelemetry: use FastAPI's native traces, metrics, and logs. See [OpenTelemetry](#opentelemetry).
* Dependencies: use `Annotated[..., Depends(...)]`; see [Dependency Injection](#dependency-injection) and [the dependency injection reference](dependencies.md) for `yield`, scopes, and class dependencies.
* Response models: prefer return types; use `response_model` when the public response schema differs from the internal return value; see [the response reference](responses.md).
* Pydantic models: prefer clear required fields and choose plain types or `RootModel` for actual contracts; see [the Pydantic reference](pydantic.md).
* Routing: declare router-level prefix, tags, and shared dependencies on the `APIRouter`; see [the path operation reference](path-operations.md).
* Tooling and related libraries: preserve the project's selected tools and dependencies; see [the other tools reference](other-tools.md).

## Existing server entrypoints

If the project uses the FastAPI CLI and local execution is requested, an example
development command is:

```bash
fastapi dev
```

An example production command for projects selecting that CLI is:

```bash
fastapi run
```

Preserve existing entrypoint and server ownership. If a new FastAPI CLI entrypoint
is selected, a supported version can declare it in `pyproject.toml`:

```toml
[tool.fastapi]
entrypoint = "my_app.main:app"
```

Alternatively, when the installed CLI supports it, pass the existing app path:

```bash
fastapi dev my_app/main.py
```

## Use `Annotated`

For compatible new declarations, prefer the `Annotated` style for parameters and dependencies. It keeps function signatures working in other contexts, respects the types, and allows reusability.

Use `Annotated` for parameter declarations, including `Path`, `Query`, `Header`, etc.:

```python
from typing import Annotated

from fastapi import FastAPI, Path, Query

app = FastAPI()


@app.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[int, Path(ge=1, description="The item ID")],
    q: Annotated[str | None, Query(max_length=50)] = None,
):
    return {"message": "Hello World"}
```

Use `Annotated` for compatible dependency declarations. A shared alias can help
when several endpoints need the same dependency. The following current-user stub
only demonstrates injection; it does not authenticate or authorize anyone:

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


def get_current_user():
    return {"username": "johndoe"}


CurrentUserDep = Annotated[dict, Depends(get_current_user)]


@app.get("/items/")
async def read_item(current_user: CurrentUserDep):
    return {"message": "Hello World"}
```

## Required fields

Omitting a default clearly expresses a required field in compatible Pydantic v2
code. Existing ellipsis forms can still be valid; do not rewrite them solely for
style or change required/null semantics.

```python
from typing import Annotated

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(gt=0)


@app.post("/items/")
async def create_item(item: Item, project_id: Annotated[int, Query()]):
    return item
```

See [the Pydantic reference](pydantic.md) for more details.

## Return Type or Response Model

When possible, include a return type. It will be used to validate, filter, document, and serialize the response.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None = None


@app.get("/items/me")
async def get_item() -> Item:
    return Item(name="Plumbus", description="All-purpose home device")
```

Return types or response models can filter and serialize ordinary response data.
Explicit `Response` objects bypass that processing; check actual output and all
custom serialization paths rather than treating a type annotation as a security guarantee.

Use `response_model` when the type you return is not the same as the public schema you want to validate, filter, document, and serialize. See [the response reference](responses.md).

## Performance

Prefer the established response contract; a return type or response model often
provides the needed validation and serialization. Deprecation and performance
guidance for `ORJSONResponse`/`UJSONResponse` depends on the installed FastAPI and
Pydantic release. Do not replace working custom responses without checking their
headers, status, media type and wire behavior.

## Including Routers

When declaring routers, prefer to add router-level parameters like prefix, tags, and shared dependencies to the router itself instead of in `include_router()`.

```python
from fastapi import APIRouter, Depends, FastAPI

app = FastAPI()


def get_current_user():
    return {"username": "johndoe"}


router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def list_items():
    return []


app.include_router(router)
```

See [the path operation reference](path-operations.md) for more routing patterns.

## Serve Frontend Apps

Use `app.frontend()` to serve a built static frontend app, for example a directory generated by Vite, Astro, Angular, Svelte, Vue, or a similar tool.

```python
from fastapi import FastAPI

app = FastAPI()

app.frontend("/", directory="dist")
```

Use `router.frontend()` when the frontend belongs to an `APIRouter`; normal router prefix behavior applies when the router is included.

```python
from fastapi import APIRouter, FastAPI

app = FastAPI()
router = APIRouter(prefix="/admin")

router.frontend("/", directory="admin-dist")
app.include_router(router)
```

`app.frontend()` and `router.frontend()` are low-priority routes: regular API routes are matched first, then frontend files and client-side routing fallbacks. Use these APIs only when available in the installed release and appropriate for
the selected frontend. Preserve working `StaticFiles`, proxy or separate frontend
serving when that remains the project's contract; inspect fallback/routing behavior.

## OpenTelemetry

Use the project's selected telemetry providers and privacy policy. Newer FastAPI
releases expose native OpenTelemetry integration; verify installed support before
using it or proposing changes. Do not create duplicate providers/exporters.

When explicitly selecting supported native telemetry, inspect the project's
dependency ownership rather than adding extras automatically. The upstream
example uses `fastapi[standard]` for SDK/exporters. Automatic exporter setup uses
`FASTAPI_OTEL_AUTO_CONFIGURE=true`; `OTEL_SERVICE_NAME` identifies the app and
`OTEL_EXPORTER_OTLP_ENDPOINT` selects the collector. Existing credential handling
owns `OTEL_EXPORTER_OTLP_HEADERS`; never expose its value. Reuse providers already
configured by the selected telemetry library.

Use `FastAPI(telemetry={...})` for custom configuration, such as choosing signals or supplying providers.

See the [OpenTelemetry tutorial](https://fastapi.tiangolo.com/advanced/opentelemetry/) for configuration details.

## Dependency Injection

Use dependencies when the logic can't be declared in Pydantic validation, depends on external resources, needs cleanup with `yield`, or is shared across endpoints.

Router-level `dependencies=[Depends(...)]` can apply genuinely shared checks.
Preserve endpoint-specific authorization and existing dependency composition.

See [the dependency injection reference](dependencies.md) for detailed patterns including `yield` with `scope`, and class dependencies.

## Async vs Sync *path operations*

Use `async` *path operations* only when fully certain that the logic called inside is compatible with async and await, and that it doesn't block.

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/async-items/")
async def read_async_items():
    data = await some_async_library.fetch_items()
    return data


@app.get("/items/")
def read_items():
    data = some_blocking_library.fetch_items()
    return data
```

Choose each endpoint/dependency from its actual calls: `async def` for awaited
nonblocking I/O, or `def` for synchronous blocking work handled by FastAPI's worker
pool. A synchronous helper called directly inside `async def` is not automatically
offloaded. Threadpool execution also has capacity and resource-affinity limits.

Make sure blocking code is not run inside of `async` functions. The logic will work, but will damage performance heavily.

For mixed boundaries, retain the project's supported offload/cancellation policy;
see [the other tools reference](other-tools.md).

## Streaming (JSON Lines, SSE, bytes)

To stream Server-Sent Events, use `response_class=EventSourceResponse` and `yield` items from the endpoint.

```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent

app = FastAPI()


@app.get("/events", response_class=EventSourceResponse)
async def stream_events() -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(data={"status": "started"}, event="status", id="1")
```

Plain objects are automatically JSON-serialized as `data:` fields. Use `ServerSentEvent` for full control over SSE fields (`event`, `id`, `retry`, `comment`) and `raw_data` for pre-formatted strings.

See [the streaming reference](streaming.md) for JSON Lines, Server-Sent Events (`EventSourceResponse`, `ServerSentEvent`), and byte streaming (`StreamingResponse`) patterns.

## Tooling

See [the other tools reference](other-tools.md) for details on uv, Ruff, ty for package management, linting, type checking, formatting, etc.

## Other Libraries

See [the other tools reference](other-tools.md) for details on other libraries:

* Asyncer, AnyIO or asyncio offloading only when selected and appropriate.
* SQLModel, SQLAlchemy or another existing database boundary without migration.
* HTTPX or the existing HTTP client, with explicit lifetime and sync/async semantics.

## Plain types and RootModel

For a simple compatible list body, regular annotations plus `Annotated` can avoid
a wrapper model. Preserve a selected `RootModel` when named schema, validation or
serialization behavior earns it; do not change public schema identity incidentally.

```python
from typing import Annotated

from fastapi import Body, FastAPI
from pydantic import Field

app = FastAPI()


@app.post("/items/")
async def create_items(items: Annotated[list[int], Field(min_length=1), Body()]):
    return items
```

FastAPI supports these type annotations and will create a Pydantic `TypeAdapter` for them, so types work normally without custom wrapper models. See [the Pydantic reference](pydantic.md).

## Use one HTTP operation per function

Separate handlers when HTTP operations have distinct validation, authorization or
response behavior. Preserve intentional multi-method endpoints when their contract
is shared; one-operation-per-function is a convention, not a correctness gate.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str


@app.get("/items/")
async def list_items():
    return []


@app.post("/items/")
async def create_item(item: Item):
    return item
```

See [the path operation reference](path-operations.md) for more examples.
