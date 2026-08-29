# dotfiles-ai

Portable macOS configuration for DBSCTR, OpenCode, Herdr, and optional Hermes
orchestration, managed as an independent chezmoi source repository.

This repository installs OpenCode from its official Homebrew tap and configures
the AI workbench. It does not install Herdr, store provider credentials, or
replace the DBSCTR specifications as lifecycle authority.

## Choose Your Path

| Goal | Start here |
|---|---|
| Install on a new workstation | [Safe Quickstart](#safe-quickstart) |
| Transfer files from another chezmoi source | [Existing Chezmoi Migration](#existing-chezmoi-migration) |
| Enable autonomous R&D | [Optional Autonomous RD](#optional-autonomous-rd) |
| Create isolated Fedora workspaces | [Optional Lima Workspaces](#optional-lima-workspaces) |
| Maintain this repository | [Update And Validate](#update-and-validate) and [Documentation Authority](#documentation-authority) |

## Requirements

- macOS
- [Homebrew](https://brew.sh/)
- [chezmoi](https://www.chezmoi.io/)
- [Herdr](https://herdr.dev/)
- Python 3.12+ and `uv` for repository validation
- Optional: 1Password CLI for `op-session`
- Optional: Lima for managed Fedora workspaces
- Optional: Hermes for autonomous R&D; enabled installations manage it through
  this source

## Safe Quickstart

> [!WARNING]
> Review the dry-run before applying. Back up any target already managed by
> another chezmoi source; two sources must not own the same live file.

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
override public defaults without entering Git history. Restart OpenCode after an
apply because it loads configuration only at startup.
The first macOS apply installs the native OpenCode release from
`anomalyco/tap/opencode`; later applies rerun Homebrew only when the Brewfile
changes.

## Configuration

- `opencode`: provider profile/region, models, local endpoint, and theme.
- `sandbox`: named Lima workspaces, mounts, Git protection, references,
  federation, aliases, and the approved Build destination.
- `herdr`: theme, Aqua LaunchAgent ownership for the Herdr server, and executable.
- `rnd`: optional Hermes profiles, schedule, review workspace, writable source,
  and non-secret GitHub identity.
- `onepassword`: optional account UUID, alias, and Keychain service.
- `tailscale`: default-off workspace enrollment and SSH policy switch; secrets,
  peer identities, and tailnet policy stay external.

When 1Password is disabled, `op-session` is not managed. Herdr and OpenCode keep
their ordinary environment-based authentication.

## Optional Autonomous R&D

> [!WARNING]
> Enable R&D only after `gh` is authenticated for the configured repository and
> the writable source path is verified. Hermes may schedule and refine work, but
> it cannot answer unresolved Discovery questions, publish a batch without
> exact operator confirmation, mark a pull request ready, or merge it.

Hermes owns scheduling, profile-local Kanban state, and OpenCode dispatch. The
DBSCTR private ledger remains lifecycle authority. Six independent lenses scan
all federated history; only the governance lens reviews prior R&D sessions.
Evidence-ready noncritical P1-P3 claims may proceed autonomously, while P0 and
material uncertainty wait for the operator. Delivery pushes only a feature
branch and creates a draft pull request into protected `main`.

See [`docs/RND_RUNBOOK.md`](docs/RND_RUNBOOK.md) for configuration, continuous use,
promotion, batch integration, health, recovery, history retention, and rollback.

## Optional Lima Workspaces

Managed Fedora workspaces keep OpenCode, Herdr, credentials, sessions, and
Hermes profiles isolated. Only declared mounts cross the VM boundary. Optional
Tailscale enrollment creates an external tailnet identity that disabling local
configuration does not revoke.

See [`docs/LIMA_SANDBOX.md`](docs/LIMA_SANDBOX.md) for creation, protected mounts,
credentials, federation, updates, recovery, and explicit peer retirement.

## Existing Chezmoi Migration

Do not apply two sources indefinitely. Compare ownership while the personal
source still owns the live files:

```sh
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml managed > /tmp/dotfiles-ai-managed
chezmoi managed > /tmp/personal-managed
comm -12 <(sort /tmp/dotfiles-ai-managed) <(sort /tmp/personal-managed)
```

Back up overlapping live targets, apply this source, verify OpenCode and Herdr,
then remove the transferred source-state files from the personal repository. Do
not add transferred targets to the personal repository's `.chezmoiremove`; that
would delete files now owned here. Complete only after a personal-source dry-run
no longer mentions transferred targets.

Before cutover, retire obsolete deployed DBSCTR V2 paths reversibly:

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

Rollback before ownership cleanup by reapplying the personal source. After
cleanup, disable this source's managed services, apply that change, rename this
checkout, restore the personal repository's ownership commit, apply the personal
source, and verify its managed list. Never leave both sources active.

## Update And Validate

```sh
git -C ~/.local/share/chezmoi-dotfiles-ai pull --ff-only
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply
uv run --group test pytest
```

Restart OpenCode after managed prompt or configuration changes. Hermes updates
are separate, manual maintenance using `hermes update --backup` followed by
profile health verification.

## Documentation Authority

| Bounded context | Authority |
|---|---|
| [`dbsctr_v3_lifecycle`](docs/specs/dbsctr_v3_lifecycle/) | Lifecycle method, gates, evidence, delivery, and retirement |
| [`dotfiles_ai_distribution`](docs/specs/dotfiles_ai_distribution/) | Portable distribution, Hermes, R&D, Lima, and delivery operations |
| [`opencode_control_plane`](docs/specs/opencode_control_plane/) | Providers, agents, prompts, permissions, skills, and routing |
| [`shell_auth_startup`](docs/specs/shell_auth_startup/) | Shell, 1Password, Keychain, and Herdr startup boundaries |
| [`writing_skills`](docs/specs/writing_skills/) | Jira and Pyramid writing behavior and evidence contracts |
| [`pm_kernel`](docs/specs/pm_kernel/) | Explicit local PM reporting, Jira rollups, and optional PostgreSQL projection |
| [`dbsctr_knowledge_store`](docs/specs/dbsctr_knowledge_store/) | Rebuildable private knowledge projection, local model services, cited hybrid retrieval, and derived graph evidence |

Within each context, `README.md` and supporting specifications own durable truth.
Private Cycle Records own implementation evidence; `CHANGELOG.md` owns completed
cycle evidence. Historical V2
source is retained under [`docs/_archive/`](docs/_archive/) and is not deployed or
current guidance. Public lifecycle entry points are `/discovery`, `/dbsctr`, and
`/qa`; Method Revision 3.28 is current.

## License

[MIT](LICENSE)
