# Typer

Adapted official Typer examples for an actual selected CLI. Inspect the installed
Typer/Python versions and preserve existing commands, defaults, output and package
entrypoints. These examples do not select a CLI framework or authorize installing
dependencies, running a user command or operating any service.

## Installing typer

Use the project's existing environment and dependency owner. If adding Typer is
explicitly selected, update the owning dependency metadata and lockfile through
that owner; do not run installation merely to consult this skill.

Current upstream marks `typer-slim`/`typer-cli` deprecated in favor of `typer`.
Check the selected release and existing packaging compatibility before a migration.

Current upstream requires Python 3.10+; preserve the project's selected support
floor and verify compatibility rather than raising it to copy an example.

## Use an explicit `Typer` app

An explicit app helps when subcommands, callbacks or shared configuration are
needed. It is not a reason to refactor a working single-command `typer.run`:

```python
import typer

app = typer.Typer()


@app.command()
def hello():
    print(f"Hello World")


if __name__ == "__main__":
    app()
```

Simpler single-command alternative:

```python
# Valid single-command option; migrate only when requirements justify it.
import typer


def main():
    print(f"Hello World")


if __name__ == "__main__":
    typer.run(main)
```

## Execute the app

When local execution is authorized, this example can be invoked as follows.
Preserve existing installed script/module entrypoints rather than adopting
`python main.py` as a new packaging convention:

```bash
python main.py
```

When multiple commands are registered to the Typer app, you have to add the command name:

```bash
python main.py hello
```

To see the automatically generated help documentation, run

```bash
python main.py --help
```

or set `no_args_is_help` to `True` when creating the `Typer()` add to automatically show the help when running a command without any arguments.

## Use `Annotated`

For new compatible declarations, prefer `Annotated` for arguments/options.
Preserve older valid declaration forms unless compatibility or actual behavior
requires a change.

It allows us to pass additional metadata that can be used by Typer.

```python
from typing import Annotated

import typer

app = typer.Typer()


@app.command()
def hello(name: Annotated[str, typer.Argument()] = "World"):
    # Note that name is an optional Argument, as a default is provided
    print(f"Hello {name}")


if __name__ == "__main__":
    app()
```

This program can be run as-is, or can provide a specific name:

```bash
python main.py
python main.py Rick
```

An older way of setting a default value is this:
```python
# Existing valid declaration; Annotated is an option for compatible new code.


@app.command()
def main(name: str = typer.Argument(default="World")):
    # Note that name is an optional Argument, as a default is provided
    print(f"Hello {name}")
```

Similarly, the old style could use ellipsis (...) to explicitly mark an argument as required.

```python
# Existing required-argument form; preserve required/default semantics.


@app.command()
def main(name: str = typer.Argument(default=...)):
    # Note that name is now a required Argument
    print(f"Hello {name}")
```

## CLI Options

CLI options are declared in a similar fashion as arguments, but will be called on the CLI with a single dash (single letter) or 2 dashes (full name).

The CLI option name is automatically generated from the variable name, so `user_name` becomes `--user-name` automatically:

```python
from typing import Annotated

import typer

app = typer.Typer()


@app.command()
def main(user_name: Annotated[str, typer.Option()]):
    # On the CLI, the required user name can be specified with --user-name
    print(f"Hello {user_name}")


if __name__ == "__main__":
    app()
```

If you want to specify a different name, or want to add a short version, declare them in the `typer.Option`:

```python
from typing import Annotated

import typer

app = typer.Typer()


@app.command()
def main(user_name: Annotated[str, typer.Option("--name", "-n")]):
    # On the CLI, the required user name can be specified with -n or --name
    print(f"Hello {user_name}")


if __name__ == "__main__":
    app()
```

You can run this program as such:

```bash
python main.py -n "Rick"
python main.py --name "Morty"
```

### CLI options with multiple values

By declaring a CLI option as a list, it can receive multiple values:

```python
from typing import Annotated

import typer

app = typer.Typer()


@app.command()
def main(user: Annotated[list[str] | None, typer.Option()] = None):
    if not user:
        typer.echo("No users provided!", err=True)
        raise typer.Exit(code=2)
    for u in user:
        print(f"Processing user: {u}")


if __name__ == "__main__":
    app()
```

This can be executed like so:

```bash
python main.py --user Rick --user Morty --user Summer
```

## Rich

If the selected Typer version/dependencies use Rich and formatted human output
is appropriate, markup can set colors/styles. Preserve machine-readable output,
TTY/color policy and existing help formatting; do not add or mandate Rich. Escape
untrusted text before rendering it as markup. For example, with Rich available:

```python
from rich import print

print("[bold red]Alert![/bold red] [green]Portal gun[/green] shooting! :boom:")
```

Typer supports using Rich formatting in the docstrings and the help messages of CLI arguments and CLI options.


```python
from typing import Annotated

import typer

app = typer.Typer(rich_markup_mode="rich")


@app.command()
def create(
    username: Annotated[
        str, typer.Argument(help="The username to be [green]created[/green]")
    ],
):
    """
    [bold green]Create[/bold green] a new [italic]shiny[/italic] user. :sparkles:

    This requires a [underline]username[/underline].
    """
    print(f"Creating user: {username}")


@app.command(help="[bold red]Delete[/bold red] a user with [italic]username[/italic].")
def delete(
    username: Annotated[
        str, typer.Argument(help="The username to be [red]deleted[/red]")
    ],
):
    """
    Some internal utility function to delete.
    """
    print(f"Deleting user: {username}")


if __name__ == "__main__":
    app()
```

For supported versions, `rich_markup_mode=None` disables rich markup in help.
Inspect the installed version's defaults and other Rich behavior separately;
markup mode is not a universal switch for plain, machine-readable output.

### Rich markdown

You can also set `rich_markup_mode` to `"markdown"` to use Markdown in the docstring:

```python
from typing import Annotated

import typer

app = typer.Typer(rich_markup_mode="markdown")


@app.command(help="**Delete** a user with *username*.")
def delete(
    username: Annotated[
        str, typer.Argument(help="The username to be **deleted** :boom:")
    ],
):
    print(f"Deleting user: {username}")


if __name__ == "__main__":
    app()
```

## Click

Typer 0.26+ vendors Click. When targeting that line, inspect compatibility before
using external Click extensions or Click-derived internals. Existing older Typer
or independent Click applications are different contexts; this does not authorize
removing their extensions or migrating their framework.

Upstream flags the following older Click-derived `Option`/`Argument` settings
when moving to current Typer; verify support against the selected version: `expose_value`, `shell_complete`, `show_choices`, `errors`, `prompt_required`, `is_flag`, `flag_value` and `allow_from_autoenv`.

For an explicitly selected upgrade, inventory actual uses and preserve their
observable behavior using supported APIs. Otherwise retain working project
conventions; package availability is not an upgrade request.

For exit status, output channels, unattended use and tests, read
[CLI contracts](contracts.md). Return to [the entrypoint](../SKILL.md) for scope.
