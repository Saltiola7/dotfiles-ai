# Exact-source child filter harness

This is a source-only experimental harness for OpenShell v0.1.7 commit
`5d25211b25a8fc887e8d5c606d57d6ab22f1d76c` with the existing reviewed
`child-unix-sockets.patch`. Its identity is
`dotfiles-ai-openshell-child-seccomp-proof-0.1.7+dotfiles-ai.child-unix-deny.1`.
It is not a full OpenShell runtime qualification. Offline tests verify fixture
identity and assembly, not compilation, Linux seccomp behavior or compatibility.
For this offline artifact, Cargo --locked validation remains pending.

## Preparation interface

`manifest.json` is schema version 1. Paths are relative to this fixture directory.
`fixture_files` declares the exact bytes of `Cargo.toml`, `Cargo.lock` and
`src/lib.rs`. `generated_source` binds the existing patch provenance record,
original source, patch, resulting SHA256 and destination. Preparation must:

1. Verify the fixture bytes and the referenced existing patch metadata, preimage
   and patch hashes. Use a fresh private assembly directory.
2. Apply the patch once to its declared upstream path, using `git apply --check
   --whitespace=error-all` followed by `git apply --whitespace=error-all`.
3. Verify the patched SHA256, then place those exact bytes at
   `src/linux/child_seccomp.rs` beside the three declared fixture files. Preserve
   the upstream SPDX attribution and accompanying Apache-2.0 license from
   `../patches/upstream/LICENSE`. Do not rewrite, extract or copy selected functions.

No second full module is checked in. The namespace `linux::child_seccomp` is
required because existing and added tests launch exact named tests in child
processes. A non-Linux compilation fails explicitly rather than passing zero tests.

`upstream_lock.records` contains the eight original external package records from
the immutable upstream lock. The harness retains every package version and
checksum. Its derived lock removes version qualifiers on unambiguous dependency
names and removes bitflags' optional `serde_core` edge, which this harness does
not enable. The Windows and errno records remain for cross-platform resolution;
only libc, rustix, socket2, bitflags and linux-raw-sys compile on the selected
Linux raw backend. Direct features are rustix `net` with default `std`, and
socket2 `all`, which exposes `Socket::pair`. No solver, crypto library or C build
dependency is introduced by this harness.

## Selected toolchain and execution

`toolchain` records official Rust 1.95.0 **aarch64-musl host** components, not a
GNU host with an added musl target. The channel manifest was read in memory and
its SHA256 checked against the official checksum. Archive hashes come from that
manifest; compressed byte sizes were checked with HTTP HEAD. Archive payloads,
expanded sizes, installers and native execution remain unverified here.

The three selected archives total 142,021,008 compressed bytes. Native preparation
must verify those hashes and sizes, bound archive extraction, and verify the
bundled linker and static executable behavior before running the tests. This
fixture neither downloads artifacts nor installs a compiler. The official musl-host
compiler is dynamically linked and requires the separately admitted minimal
Fedora musl runtime. The guest runner pins and verifies that runtime's package
versions, hashes and signatures before executing the compiler; this does not add
GCC or authorize a different toolchain.

The compiler also requires a musl-compatible `libgcc_s.so.1`. The guest runner
selects Alpine 3.22 aarch64 `libgcc` 14.2.0-r6, authenticates its package using
`apk-tools-static` 2.14.12-r0, and checks exact package identity and library ELF
metadata. The existing guest OpenSSL first verifies the static verifier's detached
RSA/SHA256 signature against a digest-pinned public key. Both complete packages
are then verified offline before extracting the library. No Alpine package is
installed into the guest OS. The fixed `toolchain-unwind-1` prefix and all
bootstrap files remain inside the same capped filesystem; the earlier failed
prefix remains preserved. Only Rust process environments receive the private
library path. See `../guest_unwind.py` for immutable provenance and bounds.

`build.rustflags` is an argument array; replace only `{toolchain_prefix}` with the
verified private toolchain prefix. Use the selected musl-host Cargo without
`--target` or a configured `build.target`, so linker flags apply to both Rust build
scripts and the test binary. The selected flags use bundled `rust-lld`, GNU LLD
flavor and self-contained linking. Do not fall back to GCC, another host
toolchain, a wrapper, or a modified source if this candidate fails.

`build.cargo_test_args` selects locked, offline release library tests, one test
thread and uncaptured output. Before native execution, clear inherited probe
marker variables; they are controlled only by the isolated child tests. Require
successful test completion, the exact `required_test`, and
`required_stdout_sentinel`. The trusted parent must retain Unix sockets; filtered
children and descendants must reject Unix socket/socketpair creation while
preserving the declared INET and pipe controls.

Native preparation and execution belong to the separately admitted guest runner:
the root-owned 8 GiB filesystem, resource limits, isolated writable paths, network
separation and shutdown deadline remain mandatory. These files authorize no VM
operation. Any kernel success still leaves full OpenShell launch/exec/PTY paths,
broker interaction, inherited descriptors, agent compatibility and activation
unqualified. Full runtime compilation needs its separately accounted C toolchain.

## Primary provenance

- [OpenShell lock](https://github.com/NVIDIA/OpenShell/blob/5d25211b25a8fc887e8d5c606d57d6ab22f1d76c/Cargo.lock)
- [Existing patch provenance](../patches/README.md)
- [Rust 1.95.0 channel manifest](https://static.rust-lang.org/dist/channel-rust-1.95.0.toml)
- [Rust aarch64-musl target](https://github.com/rust-lang/rust/blob/59807616e1fa2540724bfbac14d7976d7e4a3860/compiler/rustc_target/src/spec/targets/aarch64_unknown_linux_musl.rs)
- [Rust bundled linker distribution](https://github.com/rust-lang/rust/blob/59807616e1fa2540724bfbac14d7976d7e4a3860/src/bootstrap/src/core/build_steps/dist.rs)
- [Cargo host/target flag rules](https://github.com/rust-lang/cargo/blob/rust-1.95.0/src/doc/src/reference/config.md#L577)
- [rustix dependency/features](https://github.com/bytecodealliance/rustix/blob/v1.1.4/Cargo.toml)
- [socket2 pair feature](https://github.com/rust-lang/socket2/blob/v0.6.3/src/socket.rs)
- [bitflags optional serde feature](https://github.com/bitflags/bitflags/blob/2.13.2/Cargo.toml)
