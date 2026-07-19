# dotfiles-ai

Portable macOS configuration for DBSCTR, OpenCode, and Herdr, managed by an
independent chezmoi source repository.

## Requirements

- macOS
- [chezmoi](https://www.chezmoi.io/)
- [OpenCode](https://opencode.ai/)
- [Herdr](https://herdr.dev/)
- Python 3.12+ and `uv` for repository tests
- Optional: 1Password CLI for the opt-in `op-session` helper

This repository configures those tools and can opt in to native launchd
scheduling for autonomous OpenCode review workers. It does not install OpenCode
or Herdr or store provider credentials.

## Install

```sh
mkdir -p ~/.config/dotfiles-ai
git clone https://github.com/Saltiola7/dotfiles-ai.git ~/.local/share/chezmoi-dotfiles-ai
cp ~/.local/share/chezmoi-dotfiles-ai/config.example.toml \
  ~/.config/dotfiles-ai/chezmoi.toml
$EDITOR ~/.config/dotfiles-ai/chezmoi.toml
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply
```

The real TOML stays outside the checkout. Its `[data.dotfiles_ai]` values
override the public defaults without entering Git history.

Restart OpenCode after applying because it loads configuration only at startup.

## Configuration

- `opencode`: Bedrock profile/region, default models, LM Studio endpoint, and an
  optional machine-local `seo-data-science` repository reference.
- `herdr`: theme, LaunchAgent toggle, and executable path.
- `rnd`: opt-in daily review hour/minute, watchdog interval, managed workspace,
  writable source, and non-secret GitHub identity.
- `onepassword`: optional account UUID, account alias, and Keychain service.

When 1Password is disabled, `op-session` is not managed. Herdr and OpenCode
remain usable with their normal environment-based authentication.

When R&D scheduling is enabled, apply loads a daily worker spawner and a
five-minute watchdog through launchd. Shared defaults keep it disabled; enable
it only in the machine-local config, authenticate GitHub separately, then verify:

```sh
herdr integration status
launchctl print gui/$(id -u)/dev.dotfiles-ai.dbsctr-spawner
launchctl print gui/$(id -u)/dev.dotfiles-ai.dbsctr-watchdog
```

Launchd runs the loop in the background; opening a terminal does not require a
startup command. Run `herdr` to attach to the persistent workspace and review
one OpenCode tab per scheduled worker.

Each worker reviews sanitized evidence from the global OpenCode database but may
change only this source. It claims one distinct improvement, waits in Discovery
for your answers and explicit `proceed`, then completes an isolated DBSCTR cycle,
pushes only its feature branch, and opens a human-merge-only draft pull request.
Workers and claims are durable across terminal or pane failures.

See [`docs/RND_RUNBOOK.md`](docs/RND_RUNBOOK.md) for status, manual runs,
Discovery handoff, pause, recovery, logs, and rollback.

## Existing Personal-Chezmoi Migration

Do not apply two sources indefinitely. First compare the intended rendering
while the personal source still owns the live files:

```sh
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml managed > /tmp/dotfiles-ai-managed
chezmoi managed > /tmp/personal-managed
comm -12 <(sort /tmp/dotfiles-ai-managed) <(sort /tmp/personal-managed)
```

Back up the live targets, apply this source, verify OpenCode and Herdr, then
remove the corresponding source-state files from the personal repository. Do
not add transferred targets to the personal repository's `.chezmoiremove`; that
would delete files now owned here. A personal `chezmoi apply --dry-run` must no
longer mention transferred targets before the migration is complete.

Before cutover, retire obsolete DBSCTR V2 files without making public apply
delete possibly user-owned paths:

```sh
backup="$HOME/.local/state/dotfiles-ai/legacy-backup"
for path in \
  .agents/skills/discovery2 \
  .agents/skills/dbsctr2 \
  .config/opencode/commands/discovery2.md \
  .config/opencode/commands/dbsctr2.md
do
  if [ -e "$HOME/$path" ]; then
    mkdir -p "$backup/$(dirname "$path")"
    mv "$HOME/$path" "$backup/$path"
  fi
done
```

The backup makes this cleanup opt-in and reversible. Verify those four live
paths are absent before restarting OpenCode.

Rollback before personal-source cleanup by reapplying the personal source.
Rollback afterward in this order: set `data.dotfiles_ai.herdr.launchagent=false`
in the local config, apply this source, verify the `dev.dotfiles-ai.herdr-server`
job is absent, stop invoking this source, rename its checkout to
`~/.local/share/chezmoi-dotfiles-ai.disabled`, revert the personal repository's
ownership-removal commit, apply the personal source, and confirm its managed list
contains the restored targets. The local `dotfiles-ai` config continues pointing
at the now-missing original source path, preventing accidental dual application.

## Update And Validate

```sh
git -C ~/.local/share/chezmoi-dotfiles-ai pull --ff-only
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply
uv run --group test pytest
```

Lifecycle and release artifacts live in `docs/specs/dotfiles_ai_distribution/`.
