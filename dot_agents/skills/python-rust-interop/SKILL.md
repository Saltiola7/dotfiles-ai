---
name: python-rust-interop
description: Design and review Python/Rust extensions or embedding boundaries, including PyO3 ownership, interpreter attachment, async lifetimes and wheel compatibility. Use for actual interoperability changes.
---

# Python/Rust Interoperability

Start with the affected boundary and its existing Python and Rust consumers.
Preserve project interfaces, tooling and validation ownership. Using Rust-based
Python tools such as Ruff or uv does not itself require an interoperability review.

## Establish the selected environment

Inspect relevant Cargo manifests and lockfile, Rust toolchain/MSRV, Python build
backend and the selected Python, PyO3, maturin, NumPy-binding and async-bridge
versions. Distinguish an extension imported by Python from a Rust executable
embedding Python, and GIL-enabled from free-threaded interpreter builds.

Use official documentation matching those versions. Resolve a missing support
assumption before adopting an API; do not make an unrelated toolchain upgrade or
build-backend migration part of the repair.

## Trace ownership and execution

Identify callers, input/output shapes, conversions, retained handles, callbacks,
resource lifetimes and expected exceptions. For acceleration work, measure the
Python caller including conversions and crossings; choose batching when it
preserves behavior and improves that workload.

`Bound<'py, T>` owns a Python reference tied to interpreter attachment;
`&Bound` and `Borrowed` express borrowing. `Py<T>` can retain an object across
calls for later binding, but does not keep the interpreter alive or establish
permission to use that object in another interpreter.

A `Python<'py>` token establishes attachment, not a mutex for arbitrary shared
state on free-threaded Python. Keep Python access attached, detach Rust-only work
where appropriate, and inspect lock, callback and join ordering. Match module
thread-safety declarations and unsafe assumptions to the selected versions.

Map expected Rust failures into the existing Python exception contract using
`PyResult`/`PyErr`; preserve useful Python exception information. Determine the
panic/unwind/abort policy separately instead of treating panics as ordinary
recoverable input failures or successful results.

## Load affected detail only

- Futures, cancellation, callbacks or runtime shutdown:
  [Async ownership](references/async-ownership.md).
- NumPy views, aliasing, borrowed buffers or zero-copy:
  [Array ownership](references/array-ownership.md).
- Build layout, linking, stable ABI or wheel distribution:
  [Build compatibility](references/build-compatibility.md).

## Verify the changed contract

Use the project's selected Rust and Python checks. Exercise the affected public
operation and failure paths; include cancellation, concurrency or teardown when
those boundaries changed. Test the actual built artifact in clean supported
targets for distribution changes: a development import does not establish wheel
compatibility. Use optimized builds for performance claims.

Return boundary decisions, version/build assumptions, observed checks and gaps
to the existing primary workflow and QA owner. Read the relevant reference's
official sources for version-specific recipes; the references are not a required
sequence or a replacement for project policy.
