# python-resource-management — detailed worked examples

Apply the entrypoint's ownership and failure rules. The examples borrow their
inputs unless explicitly stated; the owner closes the underlying response/stream.
Prefer native driver contexts. Test failed acquisition, cancellation, early close
and secondary cleanup errors. See [contextlib](https://docs.python.org/3/library/contextlib.html)
for ExitStack, generator closure and exception propagation semantics.

## Advanced Patterns

### Pattern 5: Selective Exception Suppression

Suppress only a documented domain outcome; returning True affects the body
exception, while close itself may raise a different failure. A client disconnect
is not universally a successful operation. Close only an owned stream and preserve
other errors. This example applies only when that ownership/contract is explicit.

```python
class StreamWriter:
    """Own the supplied stream under an explicit broken-pipe contract."""

    def __init__(self, stream) -> None:
        self._stream = stream

    def __enter__(self) -> "StreamWriter":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Clean up, suppressing BrokenPipeError on shutdown."""
        self._stream.close()

        # Suppress BrokenPipeError (client disconnected)
        # This is expected behavior, not an error
        if exc_type is BrokenPipeError:
            return True  # Exception suppressed

        return False  # Propagate all other exceptions
```

### Pattern 6: Streaming with Accumulated State

Retain a full result only when required, with a caller-selected budget. This
illustration handles decoded text, not arbitrary wire bytes. Returning every full
prefix performs repeated joins and can cost quadratic copying; prefer yielding
only new chunks when consumers do not require snapshots. Early generator close
is incomplete output; only exhaustion returns the final result.

```python
from collections.abc import Generator, Iterable
from dataclasses import dataclass, field

@dataclass
class StreamingResult:
    """Accumulated streaming result."""

    max_chars: int
    chunks: list[str] = field(default_factory=list)
    _size: int = 0
    _finalized: bool = False

    def __post_init__(self) -> None:
        if self.max_chars < 0:
            raise ValueError("Retention budget must be nonnegative")

    @property
    def content(self) -> str:
        """Get accumulated content."""
        return "".join(self.chunks)

    def add_chunk(self, chunk: str) -> None:
        """Add chunk to accumulator."""
        if self._finalized:
            raise RuntimeError("Cannot add to finalized result")
        if self._size + len(chunk) > self.max_chars:
            raise ValueError("Stream retention budget exceeded")
        self.chunks.append(chunk)
        self._size += len(chunk)

    def finalize(self) -> str:
        """Mark stream complete and return content."""
        self._finalized = True
        return self.content

def stream_with_accumulation(
    response: Iterable[str], *, max_chars: int,
) -> Generator[tuple[str, str], None, str]:
    """Stream response while accumulating content.

    Yields:
        Tuple of (accumulated_content, new_chunk) for each chunk.

    Returns:
        Final accumulated content.
    """
    result = StreamingResult(max_chars=max_chars)

    for chunk in response:
        result.add_chunk(chunk)
        yield result.content, chunk

    return result.finalize()
```

### Pattern 7: Efficient String Accumulation

When a full bounded result is required, collect chunks then join once. Repeated
full-prefix construction can cost quadratic copying; implementation-dependent
concatenation optimizations are not a performance guarantee. Use profiling for
performance claims and account for retained memory as well as runtime.

```python
def accumulate_stream(stream, *, max_chars: int) -> str:
    """Efficiently accumulate stream content."""
    # BAD: O(n²) due to string immutability
    # content = ""
    # for chunk in stream:
    #     content += chunk  # Creates new string each time

    # GOOD: O(n) with list and join
    chunks: list[str] = []
    size = 0
    for chunk in stream:
        size += len(chunk)
        if size > max_chars:
            raise ValueError("Stream retention budget exceeded")
        chunks.append(chunk)
    return "".join(chunks)  # Single allocation
```

### Pattern 8: Tracking Stream Metrics

Measure time to first decoded chunk and time to normal exhaustion separately.
These timings exclude work before iteration starts and do not prove wire-level
time-to-first-byte. Empty streams have no first-chunk latency; early termination
must not publish a successful final metric.

```python
import time
from collections.abc import Generator, Iterable

def stream_with_metrics(
    response: Iterable[str],
) -> Generator[str, None, dict[str, float | int | None]]:
    """Stream response while collecting metrics.

    Yields:
        Content chunks.

    Returns:
        Metrics dictionary.
    """
    start = time.perf_counter()
    first_chunk_time: float | None = None
    chunk_count = 0
    total_bytes = 0

    for chunk in response:
        if first_chunk_time is None:
            first_chunk_time = time.perf_counter() - start

        chunk_count += 1
        total_bytes += len(chunk.encode())
        yield chunk

    total_time = time.perf_counter() - start

    return {
        "first_chunk_latency_ms": None if first_chunk_time is None else round(first_chunk_time * 1000, 2),
        "total_time_ms": round(total_time * 1000, 2),
        "chunk_count": chunk_count,
        "total_bytes": total_bytes,
    }
```

### Pattern 9: Managing Multiple Resources with ExitStack

ExitStack unwinds already acquired resources when later acquisition fails.
Keep the input population bounded; a single stack that opens every file/connection
at once can exhaust descriptors or pools. Batch work or cap active resources when
the project workload requires it. AsyncExitStack still follows the selected
resources' cancellation and close semantics.

```python
from contextlib import ExitStack, AsyncExitStack
from pathlib import Path

def process_files(paths: list[Path]) -> list[str]:
    """Process multiple files with automatic cleanup."""
    results = []

    with ExitStack() as stack:
        # Open all files - they'll all be closed when block exits
        files = [stack.enter_context(open(p)) for p in paths]

        for f in files:
            results.append(f.read())

    return results

async def process_connections(hosts: list[str]) -> list[dict]:
    """Process multiple async connections."""
    results = []

    async with AsyncExitStack() as stack:
        connections = [
            await stack.enter_async_context(connect_to_host(host))
            for host in hosts
        ]

        for conn in connections:
            results.append(await conn.fetch_data())

    return results
```
