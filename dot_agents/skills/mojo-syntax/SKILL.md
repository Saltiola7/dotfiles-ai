---
name: mojo-syntax
description: Write or review Mojo source, translate code to Mojo, or resolve syntax, ownership and standard-library differences using the project-selected SDK and channel. Use with relevant GPU or Python interop guidance when those boundaries change.
---

# Mojo syntax

Resolve the project-selected Mojo SDK/version, stable or nightly channel, standard
library, environment manager, target architecture and build/test authority before
applying syntax advice. Inspect manifests, lockfiles, tasks and nearby compatible
source first. Preserve existing pins, manager choices and supported versions.

This is a pinned upstream snapshot. Older and newer releases can differ; verify
version-sensitive APIs in the selected SDK's primary documentation or installed
sources. Do not upgrade a runtime to make an example work, or treat this snapshot
as authority over project constraints.

## Apply only relevant guidance

- Read [syntax patterns](references/syntax.md) for the affected feature: declarations,
  functions, compile-time parameters, origins, collections, pointers or exceptions.
- Read affected sections of [idiomatic Mojo](references/idiomatic-mojo.md) for helper
  reuse, API shape, ownership, invariants or review. Its upstream module names and
  style examples are conditional on the actual project and SDK.
- Add [GPU fundamentals](../mojo-gpu-fundamentals/SKILL.md) only for actual device
  code, launches, transfers or synchronization.
- Add [Python interop](../mojo-python-interop/SKILL.md) only when Python calls,
  conversions, extension modules or ABI/lifetime boundaries change.
- Use [new project setup](../new-modular-project/SKILL.md) only for explicitly
  requested setup or an authorized environment change, not routine Mojo edits.

Preserve existing behavior and public compatibility. Check argument conventions,
copy/move ownership, pointer origins and error propagation before adopting a
mechanical syntax replacement. Match compile-time requirements to the selected
API; do not turn runtime inputs into constants just to copy an example.

## Evidence and return

Use the project's existing selected environment and scoped build/tests when
available and authorized. Running an environment manager can resolve or install
dependencies; inspect its command/task behavior before treating it as read-only.
Loading this skill does not authorize SDK/tool installation or host changes.

Return bounded changes or findings, actual SDK/target evidence, commands and
results, and remaining compatibility questions. An absent compiler or unsupported
target remains a capability gap. Static inspection is not compilation evidence.
The existing primary, project policy and QA own acceptance and lifecycle gates.

Provenance and exact license terms: [UPSTREAM.md](UPSTREAM.md).
