# Artifacts and bounded concurrency evidence

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

Use the project's selected interpreter, backend, versions, support matrix and QA
commands. Loading this reference does not install runtimes, native dependencies,
TSan or a parallel-test tool, or start a build. Report unavailable coverage.

## Check imports and GIL state

Run the following Python in a **fresh selected free-threaded interpreter**, replacing
`your_package` with the actual affected module list. The check requires no forced
GIL setting; run it without `PYTHON_GIL` or `-X gil=...`. It propagates import errors
and verifies actual runtime state afterward, rather than matching one warning string.
This checks a support declaration path; it does not establish thread safety.

```python
import importlib
import os
import sys
import sysconfig

if "PYTHON_GIL" in os.environ or "gil" in sys._xoptions:
    raise SystemExit("Run declaration check without a forced GIL setting")
if sysconfig.get_config_var("Py_GIL_DISABLED") != 1:
    raise SystemExit("Selected interpreter is not a free-threaded build")
is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
if not callable(is_gil_enabled):
    raise SystemExit("Selected interpreter lacks the runtime GIL check")
if is_gil_enabled():
    raise SystemExit("GIL is already enabled before target imports")
for module_name in ("your_package",):
    importlib.import_module(module_name)
if is_gil_enabled():
    raise SystemExit("Target imports enabled the GIL")
```

An unsuccessful import cannot pass this check. Check each native module required
by the support claim, including optional imports exercised by the public operation.
Avoid catching ImportError as a successful optional result for a required module.
A separate controlled `PYTHON_GIL=0` or `-X gil=0` process can expose races without
a missing declaration re-enabling the GIL; it cannot replace the unforced check.

## Wheels and selected build backends

Version-specific native wheels built for a free-threaded interpreter normally use
a `t` ABI tag such as `cp314t`. Verify the resulting artifact, module declaration,
compiler defines and dependencies; the tag alone does not prove safe behavior.
Pure-Python wheels do not gain a native `t` ABI requirement solely for this port.

Preserve the selected meson-python, scikit-build-core, setuptools or maturin setup.
PyO3's declaration syntax differs between releases; follow
[declaration guidance](declaring-support.md) and the selected version's docs rather
than always adding `gil_used = false`. Windows may need a compiler define derived
from the free-threaded interpreter's configuration.

For a selected cibuildwheel version, check whether its supported free-threaded
targets are automatic or opt-in. Some versions use `enable =
["cpython-freethreading"]` / `CIBW_ENABLE`; do not assume that setting, a new matrix
or an interpreter upgrade is needed in every project. Build/test only the admitted
platforms and record skips. Install and test the actual wheel outside the source
checkout with the selected runtime.

Stable ABI/`abi3t` is a separate migration with binding/backend support requirements.
Do not change the Python floor or declare a combined ABI tag from this reference.
See [background](background.md) for the distinction and optional external guidance.

## Exercise the admitted concurrency contract

Use existing project tests and targeted concurrent operations against each changed
shared invariant. Coordinate workers with a barrier when simultaneous access is
the behavior under test; bound worker count, repetitions, time and memory. Check
outcomes, exceptions, cleanup and continuing external effects, not merely absence
of crashes. Include allowed callback/reentrancy and failure paths where affected.

A compatible pytest-run-parallel version can run existing tests concurrently from
threads, but fixture/global-state assumptions can make tests unsafe to share.
Triage a parallel failure: it may be an application race, a test-isolation defect,
an unsupported test contract or another failure. Do not silence a new failure with
a blanket marker; justify quarantine and its missing coverage explicitly.

For native code, ThreadSanitizer can find data races the suite does not assert.
Use a compatible instrumented CPython and relevant native dependencies to avoid
uninstrumented-runtime blind spots or misleading reports. Review every suppression
and distinguish known upstream issues from proved harmless behavior. TSan is not
a proof of race freedom or a detector for all application-level ordering errors.

Weakly ordered architectures such as ARM can expose ordering defects hidden on
x86. Select meaningful coverage from the supported targets and resource authority;
record absent architectures/instrumentation rather than claiming they passed.
No fixed x86-plus-ARM-plus-TSan sequence overrides the project's accepted QA plan.

Return exact runtime/build identifiers, artifact identities, commands actually run,
GIL observations, concurrency cases, findings and gaps to the existing primary/QA.
A static check of this example is not a live free-threaded runtime qualification.

Sources: [CPython free-threading](https://docs.python.org/3/howto/free-threading-python.html),
[C extension guide](https://docs.python.org/3/howto/free-threading-extensions.html),
[cibuildwheel options](https://cibuildwheel.pypa.io/en/stable/options/),
[pytest-run-parallel](https://github.com/Quansight-Labs/pytest-run-parallel).
