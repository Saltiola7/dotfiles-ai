# Native free-threading support declarations

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

A native support marker tells CPython not to enable the GIL for this module.
It is a promise about the admitted concurrent-use contract, not a synchronization
primitive. Complete the relevant shared-state assessment before declaring support.
Pure-Python modules do not need these C extension declarations.

Use the selected CPython and binding versions' primary docs. The following are
version-qualified examples; they do not authorize a toolchain or runtime upgrade.

## Direct C/C++ extensions

For multi-phase initialization on CPython 3.13+, add the slot with a version guard
when older supported versions lack it. A GIL-build compilation can retain the slot;
the marker does not itself establish native race safety.

```c
static PyModuleDef_Slot mymod_slots[] = {
    {Py_mod_exec, mymod_exec},
#if PY_VERSION_HEX >= 0x030D0000
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL},
};
```

This is a fragment requiring the existing module definition and `mymod_exec`.
For legacy single-phase initialization, `PyUnstable_Module_SetGIL` is available
only in the free-threaded build and needs its own guard:

```c
PyMODINIT_FUNC PyInit_mymod(void) {
    PyObject *m = PyModule_Create(&mymoddef);
    if (m == NULL) return NULL;
#ifdef Py_GIL_DISABLED
    PyUnstable_Module_SetGIL(m, Py_MOD_GIL_NOT_USED);
#endif
    return m;
}
```

The unstable API is not a stable-ABI recipe. Keep a selected ABI migration separate;
changing initialization or native ownership can affect subinterpreters and teardown.
On platforms where the free-threaded build flag is not automatically provided to
the compiler, obtain the correct define from the selected interpreter/build system;
check Windows behavior against that toolchain's documentation.

## Binding frameworks

| Selected binding/version | Declaration example and qualification |
| --- | --- |
| Cython 3.1+ | `freethreading_compatible=True` confirms the author's review; it does not protect handwritten shared globals or extension attributes |
| pybind11 2.13+ | `py::mod_gil_not_used()` on the module declaration; review C++ state and callback/runtime attachment |
| nanobind 2.2+ | `FREE_THREADED` in the module build; use its documented free-threading feature macro for binding-specific code |
| PyO3 0.23–0.27 | Explicit `#[pymodule(gil_used = false)]` or its supported equivalent |
| PyO3 0.28+ | Support is the default; `gil_used = true` opts out, subject to the selected version's actual behavior |

A declaration for one module does not cover other modules or linked dependencies.
PyO3 renamed attachment/detachment and synchronization APIs across releases;
preserve the selected API rather than copying a newer spelling into an old project.

A Free Threading Trove classifier is advisory metadata, separate from native module
initialization. Follow project policy and advertise only the verified support level.
Do not claim Stable while an admitted concurrency contract remains unresolved.

Primary authorities: [CPython extension HOWTO](https://docs.python.org/3/howto/free-threading-extensions.html),
[Cython free-threading](https://docs.cython.org/en/latest/src/userguide/freethreading.html),
[pybind11 free-threading](https://pybind11.readthedocs.io/en/stable/advanced/misc.html#free-threading-support),
[nanobind free-threading](https://nanobind.readthedocs.io/en/latest/free_threaded.html),
[PyO3 free-threading](https://pyo3.rs/latest/free-threading.html).
