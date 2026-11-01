# Atheris Examples

Two harness examples for a compatible installed Atheris environment. They run
only when executed as scripts. Import instrumentation cannot reach code loaded
before its context; verify the actual target receives coverage. Use finite
campaign budgets such as `-max_total_time=60 -max_len=4096 -rss_limit_mb=2048
-timeout=5`, with selected corpus/artifact paths. No campaign was run to install
this guidance.

## Example: Pure Python Parser

```python
import sys
import atheris

with atheris.instrument_imports():
    import json

@atheris.instrument_func
def TestOneInput(data: bytes):
    try:
        # Fuzz Python's JSON parser
        json.loads(data.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
```

## Example: HTTP Header Parsing

```python
import sys
import atheris

with atheris.instrument_imports():
    import http.client
    from io import BytesIO

@atheris.instrument_func
def TestOneInput(data: bytes):
    try:
        # Parse header lines from an in-memory byte stream; no network access.
        with BytesIO(data) as source:
            http.client.parse_headers(source)
    except http.client.HTTPException:
        # Documented rejection of too many or overlong header lines.
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
```

Both catch only documented malformed-input failures. Unexpected exceptions,
assertions and native sanitizer reports remain observable. Confirm exception
contracts against the project's selected Python version. A memory-only campaign
that deliberately suppresses Python failures is a different, explicitly limited
scope and cannot claim Python behavior coverage.
