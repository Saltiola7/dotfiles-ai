---
name: mojo-python-interop
description: >
  Change or review a Mojo/Python boundary: Python calls from Mojo, value conversions, Python extension modules, exported Mojo types, or importing Mojo from Python. Use for ABI, ownership, lifetime and exception concerns with the project-selected SDK and Python runtime.
---

# Mojo and Python interop

Use [Mojo syntax](../mojo-syntax/SKILL.md) for affected Mojo source. Identify the
interop direction, selected Mojo SDK/channel, Python version/ABI, OS/architecture,
environment manager and dependency constraints before choosing an API. Preserve
existing pins and boundaries; a pinned upstream example is not compatibility proof.

## Choose only needed detail

Read relevant sections of [interop patterns](references/interop-patterns.md):

- Python calls, PythonObject conversions and collections for Python from Mojo.
- Module initialization, exported functions/types, ownership and build rules for
  Python extension modules.
- `mojo.importer` only when the selected SDK and requested workflow use it. Importing
  can compile code and write `__mojocache__`; it is not read-only inspection.

Treat Python imports and `Python.evaluate` as code execution. Resolve modules and
search paths from trusted project context. Keep evaluated code static and trusted;
never concatenate or interpolate untrusted values into source. Pass values as
arguments or use callable factories such as `operator.itemgetter(field)`.

Check conversion failures, exception propagation, ownership transfer, borrowed
references and lifetime/cleanup in the affected boundary. Confirm extension names,
export/initialization symbols and library/ABI rules for the actual SDK and target.
Do not infer a supported ABI from an example's filename or successful local import.

## Evidence and return

Use existing compatible project tooling for scoped build/import and behavior tests
when available and authorized. Cover affected round trips, invalid inputs and
exception conversion, plus ownership/lifetime scenarios appropriate to the change.
Report target identity, actual commands/results and untested runtime/ABI combinations.
Missing compiler, Python library or target support remains a capability gap.

Loading this skill authorizes no SDK/Python/package installation, runtime upgrade
or unrelated MAX dependency. The existing primary, project profile and QA retain
lifecycle and acceptance authority. Use [new project setup](../new-modular-project/SKILL.md)
only when setup or an environment change is explicitly in scope.

Provenance and exact license terms: [UPSTREAM.md](UPSTREAM.md).
