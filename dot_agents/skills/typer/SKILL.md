---
name: typer
license: MIT
description: Implement or review actual Typer command interfaces, arguments/options, help and automation contracts. Preserve installed versions and existing CLI conventions; do not select Typer for unrelated Python work.
---

# Typer

Inspect Python/Typer versions, installed entrypoints, command groups/callbacks and
existing callers. Preserve commands, option names, defaults, exit codes and
stdout/stderr. This technique supplements the current primary; loading it does
not select a framework, upgrade dependencies or authorize running user commands.
See [UPSTREAM.md](UPSTREAM.md) for source and adaptations.

Prefer compatible annotated declarations for new code without rewriting valid
older forms. Introduce an explicit app when subcommands/shared configuration earn
it; a simple `typer.run` can remain appropriate. Version-gate Click-extension
changes, especially Typer 0.26+ vendoring, instead of migrating other Click tools.

Read only the reference needed:

- [Command patterns](references/commands.md): annotated arguments/options,
  app choices, optional Rich help and version-dependent Click compatibility.
- [CLI contracts](references/contracts.md): output channels, exit status,
  noninteractive behavior, safe diagnostics and focused in-process tests.

Use the existing runner to verify supported commands, invalid input and automation
contracts. Keep machine output parseable and diagnostics on the selected channel.
Fake/in-process commands do not prove packaging or external effects. Report
unavailable runtime checks without installing or migrating tooling implicitly.
