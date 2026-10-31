---
name: mojo-gpu-fundamentals
description: Write or review Mojo GPU kernels, launches, device buffers, layouts, synchronization or accelerator benchmarks. Use for an actual device-code concern, bound to the project-selected SDK, runtime and supported hardware.
---

# Mojo GPU fundamentals

Use [Mojo syntax](../mojo-syntax/SKILL.md) for the affected source. Establish SDK
version/channel, runtime/driver, device architecture, supported target matrix and
project correctness/performance authority. Preserve environment manager and pins.
A host architecture or vendor label alone does not establish accelerator support.

## Apply to the device boundary

Read relevant sections of [GPU patterns](references/gpu-patterns.md) for layouts,
thread indexing, buffers, launches, reductions, synchronization or benchmarking.
These are a pinned snapshot: verify imports, origin types and host-versus-device
capability APIs against the selected SDK. Mojo examples do not use CUDA decorators
or launch syntax; do not invent CUDA-to-Mojo substitutions from memory.

Check the affected invariants before optimizing:

- Shape, dtype, layout, strides, alignment, tails and zero-size inputs.
- Buffer ownership/lifetime, transfer direction, stream/device context and launch
  dimensions against actual device limits.
- Shared-memory visibility, barriers, completion and host/device synchronization.
- Compile-time parameters only where required by the selected API; preserve supported
  dynamic shapes and runtime launch inputs.
- Numerical tolerance and behavior on every required target. Generic primitives
  suggest possible portability; they do not prove support on untested hardware.

Keep justified capability guards. Expand the device matrix only when in scope and
validated; preserve required fallbacks. Hardware tables in the reference illustrate
families and are not substitutes for querying actual limits.

## Evidence and return

Use the project's existing environment and scoped correctness tests before timing.
For performance, compare equivalent data, precision, warmup, synchronization,
transfers and workloads, and identify device/runtime. The optional `max.benchmark`
example applies only when already compatible with selected project dependencies;
it does not authorize unrelated MAX installation or model-lifecycle work.

Report actual target/results and distinguish measured performance from hypotheses.
Missing SDK, supported GPU or required device lane remains a capability gap, not
a passing hardware gate. Loading this skill authorizes no SDK, driver, GPU or tool
installation. Existing primary and QA retain lifecycle and acceptance authority.

Provenance and exact license terms: [UPSTREAM.md](UPSTREAM.md).
