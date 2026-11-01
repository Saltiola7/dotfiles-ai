---
name: atheris
description: Design or review explicitly selected Atheris coverage-guided Python or native-extension fuzz targets, instrumentation and sanitizer setup. Preserve meaningful failures, project runtime compatibility and bounded campaign scope.
license: CC-BY-SA-4.0
metadata:
  author: Trail of Bits
  category: fuzzer
---

# Atheris

Atheris is a coverage-guided Python fuzzer built on libFuzzer. It enables fuzzing of both pure Python code and Python C extensions with integrated AddressSanitizer support for detecting memory corruption issues.

Use this skill for an explicitly selected fuzz target or fuzzing review, not for
ordinary Python changes merely because tests are present. Keep the project's
interpreter, dependency manager and test ownership. These recipes do not authorize
package/toolchain installation, container builds, native rebuilds or campaigns.

For authorized execution, establish the target, permitted fixture inputs, corpus
and artifact paths, time/run budget, maximum input size, RSS limit and worker
count before running. Avoid targets that contact live services or mutate live
data. The commands below illustrate finite local runs; adapt budgets to the
project, and report missing instrumentation or unavailable tools as coverage gaps.
Keep crash inputs and the exact versioned reproduction command; confirm the
failure without swallowing it before calling it a target bug. Fuzzing without
findings does not prove correctness.

## When to Use

| Fuzzer | Best For | Complexity |
|--------|----------|------------|
| Atheris | Python code and C extensions | Low-Medium |
| Hypothesis | Property-based testing | Low |
| python-afl | AFL-style fuzzing | Medium |

**Choose Atheris when:**
- Fuzzing pure Python code with coverage guidance
- Testing Python C extensions for memory corruption
- Integration with libFuzzer ecosystem is desired
- AddressSanitizer support is needed

## Quick Start

```python
import sys
import atheris

@atheris.instrument_func
def TestOneInput(data: bytes):
    if len(data) == 4:
        if data[0] == 0x46:  # "F"
            if data[1] == 0x55:  # "U"
                if data[2] == 0x5A:  # "Z"
                    if data[3] == 0x5A:  # "Z"
                        raise RuntimeError("You caught me")

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
```

Run:
```bash
python fuzz.py -max_total_time=60 -max_len=4096 -rss_limit_mb=2048 -timeout=5
```

## Installation

Atheris supports 32-bit and 64-bit Linux, and macOS. We recommend fuzzing on Linux because it's simpler to manage and often faster.

### Prerequisites

- Resolve the project's selected Python and Atheris release/source versions.
  The [pinned official README](https://github.com/google/atheris/blob/e36da74cf42b5834c4e31d7cabb58d796695d29f/README.md#installation-instructions)
  lists Python 3.11–3.14 for that source revision and notes that older releases
  remain on PyPI. This is not a universal floor for every release. Verify the
  selected release's compatibility rather than upgrading the project implicitly.
- For native targets, a compatible Clang/libFuzzer/sanitizer toolchain; match
  Atheris and extension build versions. Apple Clang may lack libFuzzer.
- A project-selected container runtime only if container execution is requested.

### Linux/macOS

```bash
# Only when a dependency change is part of the task, using a uv-managed project:
uv add atheris
```

### Optional Linux Container Example

This is an illustrative build recipe, not a verified image or an instruction to
replace the project's environment. Select compatible pinned Python/LLVM/Atheris
versions and the image/package provenance required by the project before building.
Do not infer macOS preload support from this Linux recipe.

```dockerfile
# https://hub.docker.com/_/python
ARG PYTHON_VERSION=3.11

FROM python:$PYTHON_VERSION-slim-bookworm

RUN python --version

RUN apt update && apt install -y \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# LLVM builds version 15-19 for Debian 12 (Bookworm)
# https://apt.llvm.org/bookworm/dists/
ARG LLVM_VERSION=19

RUN echo "deb http://apt.llvm.org/bookworm/ llvm-toolchain-bookworm-$LLVM_VERSION main" > /etc/apt/sources.list.d/llvm.list
RUN echo "deb-src http://apt.llvm.org/bookworm/ llvm-toolchain-bookworm-$LLVM_VERSION main" >> /etc/apt/sources.list.d/llvm.list
RUN wget -qO- https://apt.llvm.org/llvm-snapshot.gpg.key > /etc/apt/trusted.gpg.d/apt.llvm.org.asc

RUN apt update && apt install -y \
    build-essential \
    clang-$LLVM_VERSION \
    && rm -rf /var/lib/apt/lists/*

ENV APP_DIR="/app"
RUN mkdir $APP_DIR
WORKDIR $APP_DIR

ENV VIRTUAL_ENV="/opt/venv"
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Native target build flags; align these with the selected release and toolchain.
ENV CC="clang-$LLVM_VERSION"
ENV CFLAGS="-fsanitize=address,fuzzer-no-link"
ENV CXX="clang++-$LLVM_VERSION"
ENV CXXFLAGS="-fsanitize=address,fuzzer-no-link"
ENV LDSHARED="clang-$LLVM_VERSION -shared"
ENV ASAN_SYMBOLIZER_PATH="/usr/bin/llvm-symbolizer-$LLVM_VERSION"

# Allow Atheris to find fuzzer sanitizer shared libs
# https://github.com/google/atheris#building-from-source
ARG ATHERIS_VERSION
RUN test -n "$ATHERIS_VERSION" && \
    LIBFUZZER_LIB=$($CC -print-file-name=libclang_rt.fuzzer_no_main-$(uname -m).a) \
    python -m pip install --no-binary atheris "atheris==$ATHERIS_VERSION"

# Resolve the selected interpreter's actual Atheris directory at run time; do not
# hardcode a python3.11 site-packages path. See Linux preload guidance below.
# Keep allocation failures and leaks observable unless the target's explicit
# campaign policy documents a justified suppression.

CMD ["/bin/bash"]
```

Build and run:
```bash
docker build --build-arg ATHERIS_VERSION="$atheris_version" -t atheris .
docker run -it atheris
```

Set `atheris_version` to the deliberately selected compatible release before
using the recipe. Building the image does not build or instrument the target
extension; that remains a separate verified build step.

### Verification

```bash
python -c "from importlib.metadata import version; print(version('atheris'))"
```

## Writing a Harness

### Harness Structure for Pure Python

```python
import sys
import atheris

@atheris.instrument_func
def TestOneInput(data: bytes):
    """
    Fuzzing entry point. Called with random byte sequences.

    Args:
        data: Random bytes generated by the fuzzer
    """
    # Add input validation if needed
    if len(data) < 1:
        return

    # Call your target function
    try:
        your_target_function(data)
    except ValueError:
        # Catch this only if ValueError is the target's documented input rejection.
        pass
    # Let unexpected exceptions crash (that's what we're looking for!)

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
```

### Structured Input with FuzzedDataProvider

A target taking several typed arguments wastes most of the fuzzer's inputs if the harness
slices `data` by hand, because every mutation shifts the byte offsets of everything after it.
`atheris.FuzzedDataProvider` splits one `bytes` input into typed values instead:

```python
fdp = atheris.FuzzedDataProvider(data)
name = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
strict = fdp.ConsumeBool()
```

See [structured-input.md](structured-input.md) for the full method reference, the fixed-draw-
order rule, and what each method returns once the buffer runs dry.

### Harness Rules

| Do | Don't |
|----|-------|
| Use `@atheris.instrument_func` for coverage | Forget to instrument target code |
| Catch expected exceptions | Catch all exceptions indiscriminately |
| Use `atheris.instrument_imports()` for libraries | Import modules after `atheris.Setup()` |
| Keep harness deterministic | Use randomness or time-based behavior |

> **See Also:** For detailed harness writing techniques, patterns for handling complex inputs,
> and advanced strategies, see the optional [upstream harness-writing reference](https://github.com/trailofbits/skills/blob/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a/plugins/testing-handbook-skills/skills/harness-writing/SKILL.md).

## Fuzzing Pure Python Code

For fuzzing broader parts of an application or library, use instrumentation functions:

```python
import atheris
with atheris.instrument_imports():
    import your_module
    from another_module import target_function

def TestOneInput(data: bytes):
    target_function(data)

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
```

**Instrumentation Options:**
- `atheris.instrument_func` - Decorator for single function instrumentation
- `atheris.instrument_imports()` - Context manager for instrumenting all imported modules
- `atheris.instrument_all()` - Instrument loaded Python functions in the current interpreter; experimental and broader/slower than targeted imports

## Fuzzing Python C Extensions

Python C extensions require compilation with specific flags for instrumentation and sanitizer support.

### Environment Configuration

Use these only for the selected native target's authorized build. Scope environment
changes to that build; do not change the global toolchain or replace project flags
without checking required linker/runtime settings. The Linux container example
sets analogous flags, but has not established coverage of any extension.

```bash
export CC="clang"
export CFLAGS="-fsanitize=address,fuzzer-no-link"
export CXX="clang++"
export CXXFLAGS="-fsanitize=address,fuzzer-no-link"
export LDSHARED="clang -shared"
```

### Example: Fuzzing cbor2

Install the extension from source:
```bash
CBOR2_BUILD_C_EXTENSION=1 uv add --no-binary-package cbor2 'cbor2==5.6.4'
```

The `--no-binary-package` flag ensures the C extension is compiled locally with
instrumentation rather than pulled as a prebuilt wheel. Persist that choice with
`no-binary-package = ["cbor2"]` under `[tool.uv]` in `pyproject.toml`, or a later
`uv sync` can silently swap in an uninstrumented wheel.
The version above is an upstream example, not a project dependency recommendation.
Use the selected release and verify its native module, documented exception types
and compiled sanitizer/coverage symbols before trusting a campaign. Python import
instrumentation alone does not instrument a native extension.

Create `cbor2-fuzz.py`:
```python
import sys
import atheris

# _cbor2 ensures the C library is imported
from _cbor2 import CBORDecodeError, loads

@atheris.instrument_func
def TestOneInput(data: bytes):
    try:
        loads(data)
    except CBORDecodeError:
        # Documented malformed-CBOR rejection; unexpected Python errors propagate.
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
```

Run:
```bash
python cbor2-fuzz.py -max_total_time=60 -max_len=4096 -rss_limit_mb=2048 -timeout=5
```

For Linux, use the matching sanitizer/libFuzzer preload when the selected build
requires it; see the pinned native guide below. Its preload option is not supported
on macOS. Do not copy the guide's historical CPython 3.8.6 build recipe into a
current runtime; verify a supported strategy for the selected platform/version.

## Corpus Management

### Creating Initial Corpus

```bash
mkdir corpus
# Add seed inputs
echo "test data" > corpus/seed1
echo '{"key": "value"}' > corpus/seed2
```

Run with corpus:
```bash
python fuzz.py corpus/ -max_total_time=60 -max_len=4096 -rss_limit_mb=2048 -timeout=5
```

### Corpus Minimization

Atheris inherits corpus minimization from libFuzzer:
```bash
python fuzz.py -merge=1 -max_total_time=60 -rss_limit_mb=2048 new_corpus/ old_corpus/
```

> **See Also:** For corpus creation strategies, dictionaries, and seed selection,
> use the project's corpus policy. Optional upstream guidance on [dictionaries](https://github.com/trailofbits/skills/blob/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a/plugins/testing-handbook-skills/skills/fuzzing-dictionary/SKILL.md)
> can help with token-based formats; no separate corpus skill is required here.

## Running Campaigns

### Basic Run

```bash
python fuzz.py -max_total_time=60 -max_len=4096 -rss_limit_mb=2048 -timeout=5
```

### With Corpus Directory

```bash
python fuzz.py corpus/ -max_total_time=60 -max_len=4096 -rss_limit_mb=2048 -timeout=5
```

### Common Options

```bash
# Run for 10 minutes
python fuzz.py -max_total_time=600 -max_len=4096 -rss_limit_mb=2048 -timeout=5

# Limit input size within the same finite campaign budget
python fuzz.py -max_len=1024 -max_total_time=600 -rss_limit_mb=2048 -timeout=5

# Run with multiple workers
python fuzz.py -workers=4 -jobs=4 -max_total_time=600 -max_len=4096 -rss_limit_mb=2048 -timeout=5
```

### Interpreting Output

| Output | Meaning |
|--------|---------|
| `NEW    cov: X` | Found new coverage, corpus expanded |
| `pulse  cov: X` | Periodic status update |
| `exec/s: X` | Executions per second (throughput) |
| `corp: X/Yb` | Corpus size: X inputs, Y bytes total |
| `ERROR: libFuzzer` | Crash detected |

## Sanitizer Integration

### AddressSanitizer (ASan)

AddressSanitizer requires compatible native build flags and the correct loaded
sanitizer/libFuzzer runtime, as illustrated by the optional Linux configuration.
Compilation flags alone do not prove sanitizer loading or target instrumentation;
check the actual native artifact and matching runtime before claiming coverage.

For local setup:
```bash
export CFLAGS="-fsanitize=address,fuzzer-no-link"
export CXXFLAGS="-fsanitize=address,fuzzer-no-link"
```

Allocation failures, leaks and crashes are potentially meaningful findings.
Keep them visible by default. If interpreter initialization creates known leak
noise, document the specific campaign limitation before disabling leak detection.
Likewise, `allocator_may_return_null=1` changes OOM behavior and must not silently
reclassify resource-exhaustion failures as unimportant.

### LD_PRELOAD Configuration

For a compatible Linux build with the generated sanitizer library present:
```bash
atheris_runtime_dir="$(python -c 'import atheris; print(atheris.path())')"
test -f "$atheris_runtime_dir/asan_with_fuzzer.so" &&
    LD_PRELOAD="$atheris_runtime_dir/asan_with_fuzzer.so" python cbor2-fuzz.py -max_total_time=60 -max_len=4096 -rss_limit_mb=2048 -timeout=5
```

> **See Also:** For detailed sanitizer configuration, common issues, and advanced flags,
> see the optional [upstream AddressSanitizer skill](https://github.com/trailofbits/skills/blob/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a/plugins/testing-handbook-skills/skills/address-sanitizer/SKILL.md)
> and the [pinned native guide](https://github.com/google/atheris/blob/e36da74cf42b5834c4e31d7cabb58d796695d29f/native_extension_fuzzing.md).

### Common Sanitizer Issues

| Issue | Solution |
|-------|----------|
| `LD_PRELOAD` not set | Export `LD_PRELOAD` to point to `asan_with_fuzzer.so` |
| Memory allocation failures | Preserve the artifact; inspect target/campaign limits before choosing a documented allocator policy |
| Leak detection noise | Distinguish target leaks from interpreter startup noise; document any suppression and resulting coverage limit |
| Missing symbolizer | Set `ASAN_SYMBOLIZER_PATH` to `llvm-symbolizer` |

## Advanced Usage

### Tips and Tricks

| Tip | Why It Helps |
|-----|--------------|
| Use `atheris.instrument_imports()` early | Ensures all imports are instrumented for coverage |
| Start with small `max_len` | Faster initial fuzzing, gradually increase |
| Use dictionaries for structured formats | Helps fuzzer understand format tokens |
| Run multiple parallel instances | Better coverage exploration |

### Custom Instrumentation

Fine-tune what gets instrumented:
```python
import atheris

# Instrument only specific modules
with atheris.instrument_imports():
    import target_module
# Don't instrument test harness code

def TestOneInput(data: bytes):
    target_module.parse(data)
```

### Performance Tuning

| Setting | Impact |
|---------|--------|
| `-max_len=N` | Smaller values = faster execution |
| `-workers=N -jobs=N` | Parallel fuzzing for faster coverage |
| `ASAN_OPTIONS=fast_unwind_on_malloc=0` | Better stack traces, slower execution |

### UndefinedBehaviorSanitizer (UBSan)

Add UBSan to catch additional bugs:
```bash
export CFLAGS="-fsanitize=address,undefined,fuzzer-no-link"
export CXXFLAGS="-fsanitize=address,undefined,fuzzer-no-link"
```

Note: Modify flags in Dockerfile if using containerized setup.

## Real-World Examples

Two complete harnesses — a pure-Python parser and an HTTP response parser — are in
[examples.md](examples.md).

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| No coverage increase | Poor seed corpus or target not instrumented | Add better seeds, verify `instrument_imports()` |
| Slow execution | ASan overhead or large inputs | Reduce `max_len`, use `ASAN_OPTIONS=fast_unwind_on_malloc=1` |
| Import errors | Modules imported before instrumentation | Move imports inside `instrument_imports()` context |
| Segfault without ASan output | Missing `LD_PRELOAD` | Set `LD_PRELOAD` to `asan_with_fuzzer.so` path |
| Build failures | Wrong compiler or missing flags | Verify `CC`, `CFLAGS`, and clang version |

## Related Skills

### Technique Skills

These are optional upstream references, not installed dependencies. Read only
the guidance required by the selected target; this bundle includes its own
harness and structured-input resources.

| Skill | Use Case |
|-------|----------|
| [Harness writing](https://github.com/trailofbits/skills/blob/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a/plugins/testing-handbook-skills/skills/harness-writing/SKILL.md) | Effective deterministic harnesses |
| [AddressSanitizer](https://github.com/trailofbits/skills/blob/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a/plugins/testing-handbook-skills/skills/address-sanitizer/SKILL.md) | Native memory error detection |
| [Coverage analysis](https://github.com/trailofbits/skills/blob/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a/plugins/testing-handbook-skills/skills/coverage-analysis/SKILL.md) | Measuring target coverage |
| [Fuzzing dictionaries](https://github.com/trailofbits/skills/blob/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a/plugins/testing-handbook-skills/skills/fuzzing-dictionary/SKILL.md) | Seeds and format tokens |

### Related Fuzzers

| Skill | When to Consider |
|-------|------------------|
| **Hypothesis** | Property-based testing with type-aware generation; preserve the project's existing property-testing owner |
| **python-afl** | AFL-style fuzzing for Python when Atheris isn't available |

## Resources

### Key External Resources

**[Atheris GitHub Repository](https://github.com/google/atheris/tree/e36da74cf42b5834c4e31d7cabb58d796695d29f)**
Official repository with installation instructions, examples, and documentation for fuzzing both pure Python and native extensions.

**[Native Extension Fuzzing Guide](https://github.com/google/atheris/blob/e36da74cf42b5834c4e31d7cabb58d796695d29f/native_extension_fuzzing.md)**
Comprehensive guide covering compilation flags, LD_PRELOAD setup, sanitizer configuration, and troubleshooting for Python C extensions.

**[Continuously Fuzzing Python C Extensions](https://blog.trailofbits.com/2024/02/23/continuously-fuzzing-python-c-extensions/)**
Trail of Bits blog post covering CI/CD integration, ClusterFuzzLite setup, and real-world examples of fuzzing Python C extensions in continuous integration pipelines.

**[ClusterFuzzLite Python Integration](https://google.github.io/clusterfuzzlite/build-integration/python-lang/)**
Guide for integrating Atheris fuzzing into CI/CD pipelines using ClusterFuzzLite for automated continuous fuzzing.

### Video Resources

Videos and tutorials are available in the main Atheris documentation and libFuzzer resources.
