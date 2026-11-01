# Build and distribution compatibility

Use this reference when changing native packaging, linking, supported targets or
an extension's import layout. Preserve the selected backend and package layout
unless changing them is part of the requested work.

## Resolve the build inputs

Check Cargo workspace/package selection, enabled features, lockfile, MSRV and
toolchain alongside Python build-system requirements. A published source package
needs a toolchain and lockfile format compatible with its stated support floor.
Inspect the configured interpreter; the active development environment is not
necessarily the interpreter selected by the native build.

Distinguish the distribution name, Cargo package/library name and Python module
path. Names can differ intentionally when the backend's layout configuration and
exported module agree. Diagnose an import or symbol failure against the actual
built artifact and package contents before renaming modules or changing linking.

Match build recipes to PyO3 and backend versions. In the reviewed PyO3 0.30.1
guide, maturin and setuptools-rust set `PYO3_BUILD_EXTENSION_MODULE` automatically;
the historical `extension-module` Cargo feature affected other targets too.
Do not add legacy feature flags or manual linker settings indiscriminately when
investigating tests, embedding or extension builds.

## Choose an actual compatibility matrix

Derive supported Python implementations, versions, GIL/free-threaded builds,
OS/architectures and native prerequisites from consumer requirements. Stable ABI
features reduce some Python-version combinations while restricting available
APIs; they do not remove platform, native-library or thread-safety constraints.

Check the actual feature and target semantics before claiming ABI coverage. The
reviewed 0.30.1 guide distinguishes GIL-enabled `abi3` from `abi3t` for Python 3.15
and later; feature combinations and the build interpreter can produce different
wheel types or version-specific fallbacks. Older project versions may lack that
support. Inspect produced tags and test required consumers rather than inferring
coverage from a feature name or copying a future-version recipe.

Thread-safety declarations are a separate decision. PyO3's documented module
default changed in 0.28; versions 0.23 through 0.27 required the opposite opt-in.
Inspect unsafe/shared state and selected-version behavior before changing a
module declaration. A stable-ABI wheel or successful import does not demonstrate
that concurrent operations are safe.

For Linux distribution, check the chosen manylinux/musllinux policy, linked
libraries and architecture against actual consumers. For macOS, include the
selected deployment target, architecture and linked native libraries. A local
host build is not evidence for every supported platform.

## Validate artifacts rather than development state

Use selected build commands to produce the intended release artifact. Inspect
wheel metadata, Python/native package contents and relevant linkage. Install it
in clean target environments and run the affected public operation and failure
case; do not count `maturin develop` or source-tree imports as wheel validation.
When source distribution changed, build from that archive so omitted sources or
incorrect build requirements are observable. Report untested matrix entries.

## Official sources

The tagged PyO3 sources below document the reviewed 0.30.1 behavior. Select the
project's own tag/API documentation for implementation; current maturin help and
documentation should likewise match the installed build tool.

- [PyO3 build configuration, linking and stable ABI](https://github.com/PyO3/pyo3/blob/v0.30.1/guide/src/building-and-distribution.md)
- [PyO3 free-threading defaults and synchronization](https://github.com/PyO3/pyo3/blob/v0.30.1/guide/src/free-threading.md)
- [Maturin project layout](https://www.maturin.rs/project_layout.html)
- [Maturin wheel distribution and platform policy](https://www.maturin.rs/distribution.html)
- [Cargo minimum supported Rust version](https://doc.rust-lang.org/cargo/reference/rust-version.html)
