# Project-local setup choices

This reference adapts the pinned upstream setup walkthrough. Its former moving
release numbers, unpinned examples and automatic host/tool installation are not
compatibility authorities. Use the selected SDK/channel's current primary docs
and preserve the project's manager and constraints. Consult only the applicable
manager section; do not initialize several competing environments.

## Establish compatibility first

Record the selected Mojo version/channel, supported OS/architecture and target
runtime. If Python interop is required, also record Python version/ABI and package
sources. Inspect manifests/locks before invoking an environment wrapper: `run`,
`sync`, `add` and environment creation commands can resolve or install packages.
Do not use them as supposedly read-only inventory checks.

Check an existing compiler's version through the project's established environment
when that action is available without unintended resolution. A compiler executable
in an unrelated ambient environment is not evidence for the project. Use the
configured lock/task authority to reproduce resolution only when authorized.

## Pixi

Preserve an existing `pixi.toml` or Pixi-enabled `pyproject.toml`, `pixi.lock`,
channels, platform list, named environments and tasks. For a genuinely new project
where Pixi is selected, verify which Modular channel and `mojo` package constraint
provide the chosen SDK. Add only the needed dependency and selected platforms;
retain a reviewed lockfile and explicit build/test tasks. Use the project's task
invocation rather than requiring an interactive `pixi shell`.

The pinned upstream uses the stable `https://conda.modular.com/max/` channel and
nightly `https://conda.modular.com/max-nightly/`, with `conda-forge`. Those names
do not authorize changing a selected channel, mixing release trains or replacing
an exact version with an unconstrained package. Confirm selected-release support
before applying a channel recipe. Python and PyPI dependencies are conditional on
the actual project, not part of every Mojo setup.

## uv

Preserve `pyproject.toml`, `uv.lock`, Python requirements, indexes and the project's
workspace policy. Distinguish a maintained uv project from an explicitly requested
scratch environment; do not replace one with the other. Verify the selected
release's supported Mojo distribution/index before constructing a dependency
command. Nightly package names and indexes are not stable-release equivalents.
Do not copy the upstream stable `max[all]` recipe into a Mojo-only project.

Keep package-specific index/source selection and credentials within existing
project policy. Python packaging resolution alone does not prove native compiler,
linker, Python ABI or accelerator compatibility. An unavailable supported package
path is a setup question to resolve, not a reason to install unrelated MAX extras.

## pip or Conda

Use these only when selected by the project. For pip, retain the chosen Python
environment and constraints/lock authority; do not use a global interpreter or
substitute pip into a managed Pixi/uv project. Confirm the chosen release's package
and index before installing. Avoid `--pre` unless the chosen channel requires it.

For Conda, retain the selected environment file, channels, supported platforms and
version constraints. The pinned upstream's Modular channel forms are documented
in the Pixi section; confirm them against the selected release. Use the project's
existing resolution/export policy rather than introducing a competing lock format.

## Prerequisites and existing MAX consumers

A missing compiler/linker, platform support, manager or GPU runtime is a capability
gap. Report it and a bounded plan using the platform's existing installation owner.
Do not automatically run `sudo apt`, `sudo dnf`, `xcode-select --install`, WSL
installation, downloaded installers or global shell mutations.

If the authorized project already requires both Mojo and MAX, verify the selected
release's documented compatible pair. Their version strings may use different
schemes; do not force numerical equality, move channels or resolve to whatever is
latest. Preserve existing dependency constraints. Adding MAX, `max[all]` or
`max-all` is not a general remedy for a Mojo setup or interop issue.

## Primary documentation

Choose the selected channel and release; moving documentation is not a version pin.

- [Mojo installation](https://mojolang.org/install)
- [Mojo stable documentation](https://mojolang.org/docs/)
- [Mojo nightly documentation](https://mojolang.org/nightly/docs/)

If a page no longer describes the selected release, use that release's primary
archive or installed sources and preserve the unresolved compatibility question.
