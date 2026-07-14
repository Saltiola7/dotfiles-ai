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

This repository configures those tools. It does not install them or store
provider credentials.

## Install

```sh
mkdir -p ~/.config/dotfiles-ai
git clone git@github.com:Saltiola7/dotfiles-ai.git ~/.local/share/chezmoi-dotfiles-ai
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

- `opencode`: Bedrock profile/region, default models, and LM Studio endpoint.
- `herdr`: theme, LaunchAgent toggle, label, and executable path.
- `onepassword`: optional account UUID, account alias, and Keychain service.

When 1Password is disabled, `op-session` is not managed. Herdr and OpenCode
remain usable with their normal environment-based authentication.

Repository mappings are intentionally absent. Herdr and OpenCode operate on the
current directory, while zoxide or another navigator remains user-owned.

## Update And Validate

```sh
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml update
uv run --group test pytest
```

Lifecycle and release artifacts live in `docs/specs/dotfiles_ai_distribution/`.
