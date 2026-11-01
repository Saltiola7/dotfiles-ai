# Shared state and synchronization

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

Inventory state reachable from multiple threads and identify at least one writer
before calling it a race. Read-only-after-initialization state can be safe. The GIL
never made arbitrary compound Python operations atomic; internal container locks
also do not establish an application-level multi-step invariant.

## Find the actual ownership boundary

Inspect mutable module/class/function state, lazy caches, registries, free lists,
reused buffers, callback slots, native globals and linked-library state. Trace
callers, publication, mutation, teardown and concurrent callbacks. Use witnesses
and the supported public contract; a source keyword search is only a candidate list.

Local reference-lifetime or synchronization repairs can fit a bounded task.
Global ownership changes, multi-lock protocols, non-reentrant libraries and
lock-free structures need a design decision and matching validation. Report
location, shared state, interleaving and candidate fixes for unresolved findings;
continue independent work already authorized. Do not disguise a missing design
as a completed port or automatically rewrite every global.

## Python-level state

- Use `Lock`/`RLock` around the complete invariant, including failure/cleanup paths.
  Determine reentrancy and callback behavior before choosing the lock.
- `functools.cache`/`lru_cache` keep their cache structures coherent across threads,
  but may compute the same key more than once. That is distinct from corrupted
  cache state; synchronize only when the computation's side effects or contract
  require it. `cached_property` has different version-dependent behavior.
- `ContextVar` models logical-context state; `threading.local` models OS-thread
  state. Neither makes a shared mutable default value safe. Context inheritance
  and executor propagation depend on the selected runtime and framework.
- Publishing an immutable replacement and reading one local snapshot can simplify
  ownership. Establish a supported publication/synchronization rule; copying a
  reference alone does not make an arbitrary object graph or update sequence safe.
- Moving a global cache to thread-local state changes sharing, lifetime and memory
  use. Treat that as a contract decision, not an automatic race fix.

## Borrowed references and containers in native extensions

A borrowed item can be freed by another thread mutating its owner. Increasing its
reference afterward does not close the gap. Use supported strong-reference getters
when the owner may change, and release the resulting reference on every path.
Check the selected Python floor; pythoncapi-compat is an optional reviewed backport.

| Borrowed API | Strong-reference alternative / qualification |
| --- | --- |
| `PyList_GetItem` / `PyList_GET_ITEM` | `PyList_GetItemRef` returns a new reference or NULL |
| `PyDict_GetItem` / `PyDict_GetItemWithError` | `PyDict_GetItemRef` returns status 1/0/-1 and writes through an out-parameter |
| `PyDict_GetItemString` | `PyDict_GetItemStringRef`, where available |
| `PyWeakref_GetObject` | `PyWeakref_GetRef` returns status and an owned out-reference |
| `PyImport_AddModule` | `PyImport_AddModuleRef` |
| `PyDict_Next` | No direct strong-reference replacement; protect concurrent iteration |

Do not blanket-convert safe private/immutable borrows or function arguments whose
owners remain alive. Direct struct access and macros that omit locking need their
own justification. `PyList_SET_ITEM`/`PyTuple_SET_ITEM` are appropriate only for a
new, unshared object with the documented reference-ownership rules.

For a dictionary that another thread may mutate, `PyDict_Next` requires a critical
section around iteration. Borrowed key/value references are protected only while
that section remains active; take strong references before retaining them beyond
it, and account for suspension across calls. A linter annotation is not protection.

```c
Py_BEGIN_CRITICAL_SECTION(dict);
Py_ssize_t pos = 0;
PyObject *key, *value;
while (PyDict_Next(dict, &pos, &key, &value)) {
    /* Consume protected borrowed references here; do not retain them unowned. */
}
Py_END_CRITICAL_SECTION();
```

## Locks and critical sections

`PyMutex` is a small non-reentrant native lock on supported versions. It can be
zero-initialized; confirm API availability and Limited API restrictions. A legacy
`PyThread_type_lock` fallback requires allocation, failure handling and lifetime
cleanup; an uninitialized static pointer is not a working fallback.

Critical-section macros open/close a lexical block. They can suspend locks while
blocking or detaching and reacquire them afterward; invariants spanning such a call
must be rechecked. Do not nest sections to hold two object locks: use the supported
two-object form when applicable. They become no-ops in GIL-enabled builds, so they
do not synchronize arbitrary native code running detached from that GIL.

Do not use `Py_REFCNT(obj) == 1` as a free-threaded uniqueness proof. Consult the
selected public/unstable API and its precise scope before taking a fast path.

## Atomics and memory ordering

A language atomic makes an individual operation atomic, not a check-then-act
sequence, pointer lifetime or a larger data structure. Use actual correctly aligned
atomic storage consistently. **Do not cast an ordinary field to `_Atomic` to retrofit
safety**, mix atomic and non-atomic accesses or depend on CPython's private atomics.

A standalone statistic may allow relaxed ordering. Publishing initialized data
requires a correct synchronization relationship, commonly release-store and
acquire-load, plus an ownership/reclamation protocol. Sequential consistency does
not repair an incorrect lifetime or multi-operation algorithm. Prefer a simple lock
when that is easier to establish; do not optimize memory ordering speculatively.

CAS loops, hazard pointers, RCU and custom lock-free containers require specialist
design/review and measured need. Report them rather than improvising an algorithm
inside a port. Weakly ordered architectures can expose defects hidden on x86;
select meaningful platform coverage and report what could not be exercised.

## Native libraries and binding frameworks

A non-reentrant dependency can require per-handle or global serialization,
caller-owned state, or an explicit refusal of concurrent use. Documenting a restricted
subsystem can be valid when it matches the public admitted-use contract. It does
not justify a general safety claim for concurrency that remains allowed and unsafe.

Cython's free-threading declaration does not protect handwritten `cdef` globals,
mutable extension attributes or shared Python-object variables in parallel loops.
`nogil` and free-threaded safety are separate. Use the selected version's critical
sections/mutexes and confirm Windows build defines; do not edit generated C blindly.

PyO3's attachment token is not a mutex for arbitrary state. Use its selected-version
runtime-aware synchronization when blocking might otherwise deadlock GC or Python
callbacks. Preserve owned references across calls and review concurrent mutable
borrows, panic/exception behavior and interpreter lifetime. Detach pure native work
only when no Python access remains.

nanobind/pybind11 support does not synchronize the user's C++ objects. Binding-level
argument locks protect only calls through that binding; direct C++ callers need the
same ownership contract. Keep attachment/detachment APIs even on no-GIL builds.

Primary authorities: [CPython extension guide](https://docs.python.org/3/howto/free-threading-extensions.html),
[critical sections](https://docs.python.org/3/c-api/init.html#python-critical-section-api),
[functools](https://docs.python.org/3/library/functools.html),
[PyO3 free-threading](https://pyo3.rs/latest/free-threading.html),
[Cython](https://docs.cython.org/en/latest/src/userguide/freethreading.html),
[nanobind](https://nanobind.readthedocs.io/en/latest/free_threaded.html).
