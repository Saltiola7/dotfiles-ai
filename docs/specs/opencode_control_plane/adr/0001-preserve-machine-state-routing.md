# ADR 0001: Preserve Machine State Routing During OpenCode Deployment

- Status: accepted
- Date: 2026-09-06
- Scope: restore existing host configuration; no database migration or new runtime behavior

## Context

The workstation's machine-local `~/.config/dotfiles-ai/chezmoi.toml` correctly
configured `[data.dotfiles_ai.state] root = "/Volumes/ext/state"`, but its installed
`~/.local/bin/opencode` lacked the corresponding XDG exports and state-volume
guard. Older processes used the external database; newer managed-binary launches
used `~/.local/share/opencode/opencode.db`, making older history appear missing.

The managed-binary dispatch was introduced in `1056e06`. The source template
retained centralized-state routing. Rendering the rolling-stable source with an
empty TOML configuration reproduced the incorrect installed launcher byte for
byte; rendering with the machine configuration restored the omitted block.
The exact command responsible for the earlier overwrite was not recovered.

This was a deployment/configuration mismatch, not an established deletion of
session data or an intentional change to the database location. Existing
distribution checks covered binary dispatch and syntax but did not establish
that the deployed launcher retained the machine's storage routing.

## Decision

Keep state location in the existing machine-local configuration. Do not hard-code
this workstation's volume into portable defaults or add an unsupported database
setting to `opencode.json`.

```toml
[data.dotfiles_ai.state]
root = "/Volumes/ext/state"
```

The managed launcher derives `XDG_DATA_HOME=/Volumes/ext/state/xdg/data`, so
OpenCode selects `/Volumes/ext/state/xdg/data/opencode/opencode.db`. It also
retains the existing state-volume guard, related state exports, and binary
dispatch. Native-storage installations and isolated remote users keep their
existing configuration choices.

Deploy with an explicit machine config and a reviewed source revision. An empty
config is a test fixture, not this workstation's deployment configuration.
For routing-only recovery, apply only the launcher and exclude scripts, avoiding
unrelated package updates or service changes. Preview and verify every apply.

## Recovery Procedure

Set `SOURCE` to a clean checkout of the reviewed revision that preserves the
currently deployed binary dispatch. Do not substitute an older source that would
revert a separately deployed package-ownership change.

```sh
chezmoi --config "$HOME/.config/dotfiles-ai/chezmoi.toml" --source "$SOURCE" \
  apply --exclude scripts --dry-run --verbose "$HOME/.local/bin/opencode"
chezmoi --config "$HOME/.config/dotfiles-ai/chezmoi.toml" --source "$SOURCE" \
  apply --exclude scripts "$HOME/.local/bin/opencode"
chezmoi --config "$HOME/.config/dotfiles-ai/chezmoi.toml" --source "$SOURCE" \
  verify "$HOME/.local/bin/opencode"
bash -n "$HOME/.local/bin/opencode"
env -u HERDR_ENV -u XDG_DATA_HOME -u XDG_STATE_HOME -u DOTFILES_AI_STATE_ROOT \
  "$HOME/.local/bin/opencode" db path
```

For this host, the final command must print the external database path above.
Removing inherited routing variables ensures an older correct session cannot
mask a broken launcher. If Chezmoi reports target drift, compare the exact diff
before approving a targeted overwrite; never force an unreviewed full apply.

## Deployment Evidence

The operator authorized deployment, push, and merge. A clean checkout at
`9fbedae` supplied the existing rolling-stable launcher. The reviewed targeted
overwrite added only the missing state exports and guards, preserving managed
dispatch. No updater, installer, or service restart was requested by the apply.

- Before repair, the clean-environment path probe returned the home-directory database.
- After repair, the same probe returned `/Volumes/ext/state/xdg/data/opencode/opencode.db`.
- Chezmoi target verification and `bash -n` passed.
- Deployed launcher SHA-256: `d60a7f95785fc779a766504d56439f7f6b5e48ab93604953d0e09d572e00066e`.

## Consequences And Recovery Boundaries

New launches use the repaired routing. Existing processes keep their open
database connections until the operator quits and restarts them. Neither database
was moved, merged, deleted, or replaced; no session-body inspection was needed.
Sessions created in the accidental database remain there and need separately
validated reconciliation if they are to appear in the external history.

Never overwrite or symlink one live database onto the other. Any later migration
requires SQLite-consistent backups, accounting for WAL state and active writers.
If the external volume is unavailable, restore the volume rather than silently
falling back to a new native database. To roll back unrelated launcher changes,
render the reviewed prior template with the same machine config; do not restore
the known-broken empty-config render.

This repair restores an existing contract. Automatic rejection of wrong-config
deployments remains follow-up work; this ADR and its path probe are operational
controls, not a claim that a new automated deployment gate was implemented.

## Visual Evidence

No new diagram is required: the configuration-to-XDG-to-database mapping above
fully describes this single-path correction. No schema, trust boundary, or new
state transition is introduced.
