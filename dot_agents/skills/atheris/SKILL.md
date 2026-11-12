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

## Runtime and instrumentation

Resolve the project's selected interpreter, Atheris release/source revision and
platform before applying a recipe. Check that release's supported versions;
current-source and historical PyPI compatibility differ. Keep native compiler,
libFuzzer and sanitizer versions aligned when a native target is involved.

- Import Atheris before the target. Import the target inside
  `atheris.instrument_imports()` so its Python code receives coverage; code already
  imported will not be instrumented by re-importing it in the context.
- Use `@atheris.instrument_func` for the selected callback/function when needed.
  Instrument the actual target, not only the harness. Broad `instrument_all()` is
  experimental; it is not the default fix for every coverage problem.
- A native extension also needs its own verified coverage/sanitizer build and
  matching loaded runtime. Python bytecode instrumentation is insufficient;
  read the native sections in [references/details.md](references/details.md)
  before changing a native build or preload configuration.

## Harness and failure contract

`TestOneInput` accepts one `bytes` value. Keep inputs deterministic and use the
selected target's documented contract. Pass the callback and arguments to
`atheris.Setup()` before `atheris.Fuzz()`; keep executable script startup under
its intended entrypoint so importing a harness does not start a campaign.

Catch only documented input-rejection exceptions. Preserve unexpected Python
exceptions, assertions and sanitizer reports; verify the exception identities
for the selected target version. A deliberately memory-only campaign that filters
Python failures has a narrower scope and cannot claim Python behavior coverage.

A finite local command, using the selected environment and adapted budgets:

```bash
python fuzz.py -max_total_time=60 -max_len=4096 -rss_limit_mb=2048 -timeout=5
```

Record interpreter/Atheris/target/build versions, exact command, corpus/artifact
paths and crash input. Reproduce a finding and retain its minimized input with
its original failure; distinguish a target failure from a harness or environment
error. Missing coverage or instrumentation remains an explicit limitation.

## Load supporting guidance when needed

- [examples.md](examples.md): concrete pure-Python JSON and HTTP-header harnesses.
- [structured-input.md](structured-input.md): multiple typed arguments,
  `FuzzedDataProvider`, stable draw order and exhausted buffers.
- [references/details.md](references/details.md): environment/container recipes,
  native compiler and sanitizer integration, corpus/minimization, campaign
  options, coverage troubleshooting and optional pinned upstream references.

The complete recipe content remains available on demand. Loading this skill does
not require installing sibling skills, tools or plugin hooks.
