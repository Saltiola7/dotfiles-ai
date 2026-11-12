# CLI contracts and unattended callers

Treat command names, option spelling/aliases, positional order, defaults, environment
fallbacks, exit status and output as a public interface. Inspect shell scripts and
other consumers before changing any of them. Preserve selected help/color policy
and installed entrypoints; a new `Typer()` object alone does not test packaging.

## Output and failures

For an established machine-readable mode, emit the promised payload to stdout and
put diagnostics/progress on stderr. Keep a documented output schema and deterministic
ordering when callers rely on them. Respect piping, non-TTY use and explicit color
controls; do not add prompts, Rich markup or progress bars to machine output.
Ordinary human-readable commands need not acquire a JSON mode without a requirement.

Use the installed Typer exception/exit APIs for their documented purpose. For
example, `typer.BadParameter` is a parameter error, `typer.Exit(code=...)` selects
an exit status, and `typer.Abort` represents abort behavior. Do not invent
`typer.ClickException` or treat every failure as success. Keep meaningful exceptions
inside the owning application boundary; catch only expected failures and preserve
unexpected exceptions for the existing error/reporting policy. Do not leak secret
values through exception text, argv dumps or rich-rendered input.

For automation, missing input should fail with a clear status unless an explicit
interactive mode is selected. Destructive operations retain their existing scope,
dry-run and authorization rules. Adding guidance never authorizes executing those
operations. A help command can still execute callbacks/imports; inspect ownership
before running a real project CLI, including `--help`.

## Focused offline example

This synthetic command has no application, filesystem or network effects. It
illustrates stdout/stderr and failure assertions using an existing compatible
Typer installation; it does not prescribe a new JSON mode for another command.

```python
import json

import typer
from typer.testing import CliRunner

app = typer.Typer()


@app.command()
def double(value: int):
    if value < 0:
        typer.echo("value must be nonnegative", err=True)
        raise typer.Exit(code=2)
    typer.echo(json.dumps({"doubled": value * 2}))


runner = CliRunner()
result = runner.invoke(app, ["4"])
assert result.exit_code == 0
assert json.loads(result.stdout) == {"doubled": 8}
assert result.stderr == ""

result = runner.invoke(app, ["--", "-1"])
assert result.exit_code == 2
assert result.stdout == ""
assert "value must be nonnegative" in result.stderr
```

`--` disambiguates a negative positional value from an option. Test the project's
actual option forms, invalid types, missing values, command dispatch, callbacks,
help, and prompt behavior when relevant. Separate stdout/stderr support differs
across runner versions; use the selected version's supported capture APIs.
In-process tests complement installed-entrypoint smoke evidence. They do not prove
real side effects, terminal rendering, signal handling or subprocess cleanup.
