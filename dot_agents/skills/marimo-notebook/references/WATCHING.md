# External Editing and Watch Mode

For an active session, `marimo-pair` remains the mutation owner. The watch workflow
below applies only when the task deliberately selects external editing with the
selected runtime. Do not enable watchers, autorun or another server to bypass a
live kernel's authority.

## The Problem

marimo loads the notebook file into memory at startup. After that, it works from its in-memory state and does **not** watch the file for external changes. If you edit the `.py` file externally (vim, VSCode, another agent), marimo won't see it. When any cell is saved in the marimo UI, it writes its in-memory version back to disk, **overwriting your external edits**.

## Solution: --watch

```bash
marimo edit --watch notebook.py
```

This monitors the file for changes and streams them to the browser editor. By default, synced code appears as "stale" — the user manually runs cells via the "Run" button or the `runStale` hotkey.

For apps:

```bash
marimo run --watch notebook.py
```

This auto-refreshes when file changes are detected.

## Auto-Execute After External Edits

If automatic execution on external edits is explicitly intended and supported
by the selected runtime, the project can select this setting. It executes affected
cells and their effects; do not add it as a default validation convenience:

```toml
[tool.marimo.runtime]
watcher_on_save = "autorun"
```

## Watcher dependencies

The selected version may use `watchdog` or a polling fallback. Inspect its
requirements and existing project dependencies. An optional performance dependency
is not permission to install it or alter the environment.

## Module Autoreloading

Watch imported `.py` modules for changes (not just the notebook file):

1. Enable in notebook settings → Runtime → Module Autoreloading
2. Two modes:
   - **Autorun**: automatically executes cells affected by module changes
   - **Lazy**: marks affected cells as stale for manual execution

The reloader tracks changes recursively through the import chain.

Use case: develop logic in Python modules, use the notebook as an orchestrating DAG.

## Responding to other files

marimo has `mo.watch.file` and `mo.watch.directory` utilities that can cause cells to update when a file/folder updates.
