# Runtime, GIL and ABI background

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

Free-threaded CPython is a separate interpreter build that can execute Python
threads in parallel. It first shipped experimentally in 3.13; PEP 779 promoted
support in 3.14. Select the project's actual versions and build type; the 3.14t
example is not a minimum, a deployment recommendation or a supported-version list.

## Detection and declarations are separate

Build-time `sysconfig.get_config_var("Py_GIL_DISABLED")` identifies a free-threaded
build. Runtime `sys._is_gil_enabled()` identifies whether its GIL is currently on,
where the selected interpreter exposes that API. A native extension without a
support declaration can cause a fresh free-threaded process to enable the GIL
on import. A forced `PYTHON_GIL=0` / `-X gil=0` setting masks that declaration check;
use a separate controlled forced-off process for race stress.

A failed import is a failed check, even if no GIL warning appeared. Import every
affected module/dependency needed by the support claim and inspect actual GIL
state afterward. Neither importing nor declaring support proves safe concurrent
execution. Pure-Python code has no native slot to add just to advertise support.

## Shared state and CPython internals

The GIL never made arbitrary check-then-act or read-modify-write sequences atomic.
Without it, previously hidden interleavings may become observable. Built-in
containers use internal synchronization in supported builds; this protects their
own operations, not an application's compound invariant or another C library's
state. Do not equate normal concurrent dict/list use with undefined behavior.

Version-specific internals include biased/deferred reference counting,
immortalization, object locks, memory-allocation rules and garbage collection.
Use these to explain a concrete hazard, not as a stable extension interface.
Borrowed references can become invalid when another thread mutates the owning
container. Direct struct access and unsafe macros bypass supported synchronization.
Check the selected CPython C API and preserve runtime attachment even without a GIL.

## Workload and compatibility decisions

Parallelism is a possibility, not an automatic speedup. Measure the actual workload
including native dependencies, synchronization, allocation, memory and conversion
costs. Do not copy fixed overhead percentages or an old ecosystem-adoption count
into project acceptance criteria. A read-only assessment can identify missing
support without installing an interpreter or starting a benchmark.

Native version-specific wheels use free-threaded ABI tags such as `cp314t`; verify
the actual interpreter/backend's tags and supported platforms. Existing abi3 wheels
for GIL-enabled builds do not automatically establish free-threaded support.

Python 3.15 introduced the `abi3t` stable ABI family under
[PEP 803](https://peps.python.org/pep-0803/), with additional API restrictions and
[PEP 793](https://peps.python.org/pep-0793/) module initialization. A compatible
`abi3.abi3t` wheel can cover GIL and free-threaded CPython from its selected floor,
but that requires a qualified native port and tool support. It is not an automatic
matrix collapse or reason to drop older supported versions. Thread safety and ABI
stability remain orthogonal.

Optional [pinned limited-API workflow](https://github.com/tiran/agent-skills/blob/0c51c24122b33afed31fd8d50534e089534f77a7/skills/port-to-python-limited-api/SKILL.md)
is external reference material, not a required installed sibling.

Primary sources: [free-threading HOWTO](https://docs.python.org/3/howto/free-threading-python.html),
[C extension HOWTO](https://docs.python.org/3/howto/free-threading-extensions.html),
[PEP 703](https://peps.python.org/pep-0703/),
[PEP 779](https://peps.python.org/pep-0779/),
[ABI migration](https://docs.python.org/3.15/howto/abi3t-migration.html).
