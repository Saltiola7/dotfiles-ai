# Chezmoi State and Effect Boundaries

These are decision points, not a replacement deployment runbook. The official
references were checked against chezmoi v2.73.3; preserve the project's version
and verify its local help before using newer flags.

## Separate the state owners

Chezmoi computes target state from source files, configuration, template data and
external content, then compares it with destination state. Select source and
destination roots explicitly when the project uses a worktree, alternate config
or isolated fixture. Target arguments normally identify destination paths;
`--source-path` changes their interpretation. Use absolute paths when ambiguity
would change scope.

Source attributes can change permissions, symlink behavior, encryption or removal
semantics. Inspect the intended target type rather than comparing text alone.
An existing target may contain manual edits; neither source history nor a prior
successful apply proves that the live file can be replaced without reconciliation.

## Understand preview effects

- `diff` shows proposed differences; its success status alone does not assert that
  there are no differences. Configured diff tools and pagers can also execute.
- `apply --dry-run --verbose` previews destination changes. Chezmoi's dry-run
  guarantee concerns its destination writes, not every effect of code invoked by
  configuration, hooks, templates or initialization.
- `--exclude=scripts` excludes managed script entries. Configuration hooks are
  separate and can run even in dry-run mode. Inspect relevant hooks before
  describing a command as read-only.
- Template helpers, password-manager integrations and external content may run
  commands or use the network while computing state. Excluding scripts does not
  disable those mechanisms.
- `--refresh-externals=auto` respects cache refresh periods. Bare
  `--refresh-externals` means `always`. `never` still allows downloading a cache
  miss, so it is not an offline guarantee. Account for cache availability and the
  requested network policy without silently changing pins or cached content.

For a disposable probe, isolate source, destination, configuration, persistent
state and cache; inspect fixture code and use only synthetic non-secret data.
Do not treat a live-home dry-run as equivalent isolation.

## Preserve conflict and synchronization policy

`apply` without target arguments considers all targets. It can prompt when a
destination changed since the last write. Where supported, `--error-on-conflict`
provides a noninteractive error rather than silently overwriting divergence.
`--force` suppresses prompting; it is not a conflict-resolution strategy. An
older client's missing flag is not reason to substitute forced application.

`update` normally pulls the source repository and applies its changes. Its default
pull uses autostash and rebase unless configured otherwise. `--apply=false`
separates target application but still changes source Git state. Use the existing
repository Git owner and synchronization policy instead of treating update as a
preview or routine prerequisite.

An explicit request to apply selected targets authorizes that scoped operation;
it does not authorize unrelated source resets, removal rules, script activation
or remote pushes. Reconcile a partial failure from observed state before retrying.

## Interpret verification honestly

Use scoped `verify`, diff inspection and relevant direct destination checks.
`verify` returns success for matching state and fails when a destination change
would be required; inspect diagnostics to distinguish drift from an operational
error. Skipped encrypted targets, excluded scripts and unexercised template
branches remain outside the verified claim. A repeated clean file diff does not
prove that arbitrary hooks or scripts are idempotent.

## Official references

- [State concepts](https://www.chezmoi.io/reference/concepts/) and
  [source attributes](https://www.chezmoi.io/reference/source-state-attributes/)
- [Apply](https://www.chezmoi.io/reference/commands/apply/),
  [diff](https://www.chezmoi.io/reference/commands/diff/) and
  [verify](https://www.chezmoi.io/reference/commands/verify/)
- [Global flags](https://www.chezmoi.io/reference/command-line-flags/global/),
  [hooks](https://www.chezmoi.io/reference/configuration-file/hooks/) and
  [update](https://www.chezmoi.io/reference/commands/update/)
- [Version-pinned verify implementation](https://github.com/twpayne/chezmoi/blob/v2.73.3/internal/cmd/verifycmd.go)
