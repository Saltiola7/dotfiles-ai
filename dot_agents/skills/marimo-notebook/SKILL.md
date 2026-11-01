---
name: marimo-notebook
description: Author or review marimo notebook structure, reactivity, UI, tests and exports. Use for actual notebook artifact work; live sessions retain marimo-pair mutation ownership.
---

# Marimo notebooks

Resolve the selected notebook, marimo/Python versions, dependency owner, intended
execution modes and project runner from existing files and task context. Preserve
those choices; snapshot examples do not select versions, packages or tools.

An active kernel owns its notebook state. Use the existing `marimo-pair` capability
for durable changes in a live session; do not edit its backing `.py` file, switch
watch modes or start another server to bypass that authority. If pair is unavailable,
report that capability gap before a live mutation. Saved-file authoring applies
when no live session owns the artifact.

## Apply the relevant method

Read the affected sections of [notebook conventions](references/details.md) for
saved-file structure, output rendering and ordinary checks. Load further detail
only when the task needs it:

- [Reactivity](references/REACTIVITY.md), [state](references/STATE.md) and
  [expensive work](references/EXPENSIVE.md): definitions, mutations, gates and caching.
- [UI](references/UI.md), [anywidget](references/ANYWIDGET.md) and
  [columns](references/COLUMNS.md): actual interface changes.
- [Pytest](references/PYTEST.md), [SQL](references/SQL.md) and
  [reusable definitions](references/TOP-LEVEL-IMPORTS.md): those boundaries.
- [Configuration](references/CONFIGURATION.md), [external editing](references/WATCHING.md),
  [exports](references/EXPORTS.md) and [deployment](references/DEPLOYMENT.md): selected
  configuration or output work.

## Evidence and return

Use the project's selected command environment. Inspect version-sensitive options
in its help or matching primary documentation; do not fetch or install a newer
runtime to make a snippet work. Keep dependency additions within the requested task.

Static `marimo check` evidence is distinct from notebook execution, pytest cells,
exports that execute code and browser validation. Those operations can read data,
call services or change state; inspect the selected notebook and bound validation
to its intended effects. A passing native run does not establish browser/WASM
compatibility or authorize publication.

Return the change or findings, actual checks and unresolved runtime or environment
gaps. Existing project policy, primary agent and QA retain acceptance and delivery
ownership. Provenance: [UPSTREAM.md](UPSTREAM.md).
