# Streaming

Check installed FastAPI/Starlette support before using these APIs. JSON Lines
iterator inference and native `fastapi.sse` are version-dependent; preserve an
existing compatible explicit `StreamingResponse` or selected SSE library. These
fragments depend on application imports/values and are not a running service.

## Stream JSON Lines

To stream JSON Lines, declare the return type and use `yield` to return the data.

```python
@app.get("/items/stream")
async def stream_items() -> AsyncIterable[Item]:
    for item in items:
        yield item
```

## Server-Sent Events (SSE)

To stream Server-Sent Events, use `response_class=EventSourceResponse` and `yield` items from the endpoint.

Plain objects are automatically JSON-serialized as `data:` fields, declare the return type so the serialization is done by Pydantic:

```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


@app.get("/items/stream", response_class=EventSourceResponse)
async def stream_items() -> AsyncIterable[Item]:
    yield Item(name="Plumbus", price=32.99)
    yield Item(name="Portal Gun", price=999.99)
```

For full control over SSE fields (`event`, `id`, `retry`, `comment`), yield `ServerSentEvent` instances:

```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent

app = FastAPI()


@app.get("/events", response_class=EventSourceResponse)
async def stream_events() -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(data={"status": "started"}, event="status", id="1")
    yield ServerSentEvent(data={"progress": 50}, event="progress", id="2")
```

Use `raw_data` instead of `data` to send pre-formatted strings without JSON encoding:

```python
yield ServerSentEvent(raw_data="plain text line", event="log")
```

## Stream bytes

To stream bytes, declare a `response_class=` of `StreamingResponse` or a sub-class, and use `yield` to return the data.

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from app.utils import read_image

app = FastAPI()


class PNGStreamingResponse(StreamingResponse):
    media_type = "image/png"


@app.get("/image", response_class=PNGStreamingResponse)
def stream_image_no_async_no_annotation():
    with read_image() as image_file:
        yield from image_file
```

An explicit response can also be appropriate. This incomplete counterexample
leaves `read_image()` ownership ambiguous; it is not a ban on explicit responses:

```python
# Incomplete lifetime example; define ownership before copying

import anyio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from app.utils import read_image

app = FastAPI()


class PNGStreamingResponse(StreamingResponse):
    media_type = "image/png"


@app.get("/")
async def main():
    return PNGStreamingResponse(read_image())
```

## Producer lifetime and failures

Close resources inside the iterator's lifetime or an appropriate request/lifespan
owner; do not return an iterator over a resource already closed by a handler or
function-scoped dependency. Propagate cancellation/disconnect and perform cleanup
in `finally`/context managers. Bound buffers, producer concurrency and slow-client
work according to the application's requirements. Define event framing, heartbeat
and replay/last-event behavior explicitly if clients rely on them.

Headers/status normally commit before iteration finishes: late producer errors
cannot reliably turn into a new JSON error/status. Test cancellation, early error,
normal completion and relevant cleanup. In-process clients can buffer responses;
they do not prove proxy buffering, disconnect timing, network backpressure or SSE
reconnection behavior. Report the actual execution environment and those limits.
