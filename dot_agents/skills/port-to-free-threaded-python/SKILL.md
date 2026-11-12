---
name: port-to-free-threaded-python
license: Apache-2.0
description: Assess or implement support for a selected free-threaded CPython target, including shared-state safety, native extension declarations, wheel compatibility and concurrency evidence. Use for actual no-GIL compatibility work, not routine async edits.
---
# Port to free-threaded Python

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

**Status: Experimental porting workflow.** CPython's runtime support status and this
bundle's maturity are separate. Verify target-version APIs and binding/build-tool
support from primary documentation before applying a recipe.

Read [project boundaries](GUARDRAILS.md). Establish the project's supported
Python versions, selected GIL/free-threaded builds, native dependencies, platforms,
public concurrency contract and validation authority. Preserve those choices;
3.14t in examples is illustrative, not a new minimum or deployment selection.
The current primary/QA owns evidence and completion; this technique adds no
runtime installer, automatic build matrix or independent gate.

## Scope and baseline

Check upstream issues/ports before duplicating work. Classify pure-Python code and
every compiled module/dependency separately. Pure Python needs shared-state review
and meaningful concurrency tests; it does not need a native GIL-support slot or
version-specific native wheel solely for this port.

Use the selected existing free-threaded interpreter. Confirm both the build
(`sysconfig.get_config_var("Py_GIL_DISABLED")`) and actual runtime GIL state
(`sys._is_gil_enabled()` where supported). Import the package and affected native
dependencies, propagate failed imports, then check GIL state again. An undeclared
extension can re-enable the GIL, hiding races and removing expected parallelism.
A successful import alone establishes neither thread safety nor performance.

## Shared-state and extension review

Inventory state reachable by multiple threads and establish who can write it:
mutable globals/class fields, lazy caches, native globals, reusable buffers,
callback slots and linked libraries. The GIL never made arbitrary compound
operations atomic. Built-in container safety also does not protect a multi-step
application invariant. Distinguish coherent caches from exactly-once side effects.

Choose synchronization from the actual ownership and reentrancy contract. Review
logical-context versus OS-thread state, lock/callback ordering, runtime attachment,
borrowed-reference lifetimes and native allocation domains. Read
[thread safety](reference/thread-safety.md) for concrete C/Cython/PyO3/nanobind
hazards and [declarations](reference/declaring-support.md) for version-specific
module support flags. A declaration is a promise; it does not fix races.

Apply local fixes only when their invariant, failure paths and lifetime are clear.
Structural ownership changes, lock-free algorithms, non-reentrant libraries and
multi-lock protocols need an explicit design decision within the task's scope.
Report location, shared state, race witness, candidate remedy and validation for
unresolved findings; continue independent authorized work. Do not claim completed
support while a required safety contract remains unresolved.

## Artifact and concurrency evidence

Read [build and test](reference/build-and-test.md) for version-specific native
wheels, cibuildwheel options, a failed-import-aware GIL check and bounded stress
techniques. Keep the selected backend and support matrix. For applicable native
modules, verify free-threading declarations and correct wheel tags in the built
artifact; test the installed wheel outside the source tree.

Use targeted concurrent operations and the existing suite under the selected
runtime. A parallel-test tool can expose races or unsupported test sharing;
triage failures rather than labeling every flake an application race. Native
race analysis may require ThreadSanitizer with an instrumented interpreter and
relevant native dependencies. Record architecture/tool availability and gaps;
absence of TSan or ARM evidence is not proof of safety, nor an implied install.

Use fresh interpreter processes for two distinct checks: without a forced GIL
setting, verify imports do not re-enable it; with a deliberately forced-off GIL,
stress only the reviewed/test target under controlled conditions. A forced-off
setting cannot prove a support declaration is present. Keep both checks bounded.

`abi3t` and stable-ABI migration are a separate compatibility decision. Optional
pinned [limited-API guidance](https://github.com/tiran/agent-skills/blob/0c51c24122b33afed31fd8d50534e089534f77a7/skills/port-to-python-limited-api/SKILL.md)
is external reference material, not an installed sibling dependency or an
instruction to change the Python floor.

## Return evidence

Report selected runtime/build/dependency versions, shared-state findings and
resolution, import failures, observed GIL state after imports, artifact identities,
actual concurrency/stress/sanitizer coverage and remaining limits. Add a Free
Threading classifier only if appropriate to the project's metadata policy and
verified support level; it is advisory, not the runtime mechanism. Use measured
end-to-end workload results for speedup claims.

Primary authorities: [CPython free-threading HOWTO](https://docs.python.org/3/howto/free-threading-python.html),
[C extension guide](https://docs.python.org/3/howto/free-threading-extensions.html),
[PEP 703](https://peps.python.org/pep-0703/),
[PEP 779](https://peps.python.org/pep-0779/) and
[PEP 803](https://peps.python.org/pep-0803/). Read
[background](reference/background.md) for the runtime/ABI distinction.
