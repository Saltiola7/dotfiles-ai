---
name: jupyter-to-marimo
description: Convert explicitly selected Jupyter notebooks to marimo while preserving source content, widgets, dependencies and intended behavior. Use for requested notebook migration.
---

# Converting Jupyter notebooks to marimo

Resolve the source, a distinct output path, selected marimo/Python versions,
dependency owner and intended modes. Preserve the original `.ipynb` and existing
project choices; do not overwrite another artifact without task authority.

Use the selected environment's converter first, then review its output:
```bash
marimo convert source.ipynb -o converted.py
marimo check converted.py
```
These are command shapes, not permission to download a tool or execute the notebook.
Inspect selected-version help when options differ. The generated file is a first
draft; read source metadata/content when conversion fails or fidelity needs checking.

If the target is open in an active kernel, `marimo-pair` owns durable mutations.
Do not edit that live backing file or start another runtime to bypass its owner.
Report unavailable pair capability before a live mutation. Perform conversion to
a separate artifact unless the task explicitly selects a different safe handoff.

## Review conversion fidelity

- Account for packages and existing PEP 723 metadata. Use the selected dependency
  owner and sandbox mode when that metadata is the environment contract.
- Remove obsolete installation cells and prose only after their requirements are
  represented. Preserve the source purpose, required data and intended workflow.
- Arrange cells for presentation; the dependency graph determines execution order.
  Fix duplicate definitions, cycles and hidden cross-cell mutations.
- Review every converted or unsupported magic and interactive terminal input.
  Preserve outputs or explain why behavior/content cannot be reproduced.
- Put rendered results in each cell's final expression. Remove redundant Jupyter
  `display()` only when the replacement has the intended output.
- Load [widget migration](references/widgets.md) for ipywidgets, callbacks and
  trait-level behavior; load [LaTeX migration](references/latex.md) for renderer
  differences. Extra UI, live refresh or custom widgets require an actual need.
- Identify expensive work and external side effects before execution. Use suitable
  `mo.stop()` gates and forms where the workflow needs explicit submission.
  Define downstream values after the gate.
- Do not print, log or persist secrets. A masked input is not a secrecy boundary.

## Validate and return

Run the selected static checker after edits. Execute only the intended modes whose
effects are understood and in scope, comparing content, controls, outputs and
workflow with the source. Conversion or clean lint alone does not prove executed
equivalence. Browser/WASM targets require their own compatibility evidence.

Return changes, preserved content, actual checks, unresolved conversion losses and
execution gaps. Inspect changed artifacts for unintended data, caches and secrets.
Existing project policy and QA retain acceptance; this skill neither installs tools
nor authorizes publication. Provenance: [UPSTREAM.md](UPSTREAM.md).
