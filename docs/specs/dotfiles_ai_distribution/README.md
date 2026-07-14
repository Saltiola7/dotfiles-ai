# dotfiles-ai Distribution

**Status:** Released locally; public Final Push pending

## Engineering Profile

### Defaults

| Field | Value |
|---|---|
| Deliverable | Public standalone chezmoi source for DBSCTR, OpenCode, and Herdr configuration |
| Languages/frameworks | Go templates, TOML, JSON, Markdown, Python, Bash, launchd plist |
| Modules | Python, Security |
| Runtime/platform support | macOS; chezmoi; OpenCode; Herdr; Python `>=3.12` tests |
| Public compatibility | Stable local TOML keys and managed target paths; sanitized defaults |
| Trust/data classification | Public configuration; credentials and machine identifiers remain local |
| Operational owner | Saltiola7 maintains releases, compatibility, and migration guidance |
| Product Intent | `docs/specs/dotfiles_ai_distribution/PRODUCT.md` |

## Bounded Context

`dotfiles_ai_distribution` owns portable defaults, local configuration shape,
rendered target ownership, installation, migration, rollback, release, and
maintenance for the DBSCTR/OpenCode/Herdr workbench.

Adjacent contexts remain authoritative for lifecycle semantics, OpenCode
control-plane behavior, and shell authentication behavior.

## Goals

- Reproduce the maintainer's current working AI development configuration.
- Permit curated machine-local customization without committing it.
- Keep optional 1Password integration fail-open for Herdr startup.
- Transfer managed targets from personal dotfiles without downtime or overlap.

## Non-goals

- Managing unrelated shell, AWS, editor, Kitty, or personal secret bundles.
- Installing OpenCode, Herdr, 1Password, Graphify, RTK, or provider credentials.
- Mapping repositories while zoxide and current-directory discovery suffice.
- Supporting Linux or Windows in the first release.

## Behavior

### Fresh installation

- Given a developer has a valid local TOML, when the standalone chezmoi source
  renders and applies, then complete OpenCode, DBSCTR, and Herdr targets are
  installed without personal identifiers.

### Credential-neutral Herdr

- Given 1Password is absent or unconfigured, when Herdr and shell startup run,
  then neither blocks or attempts interactive authentication.

### Existing-user cutover

- Given personal dotfiles currently own the targets, when parity validation
  passes and ownership transfers, then live files remain present and exactly
  one chezmoi source owns each target.

## Interfaces And Contracts

- Tracked `.chezmoidata.toml` supplies public defaults.
- `config.example.toml` documents the separate local chezmoi config and curated
  `[data.dotfiles_ai]` overrides.
- The actual config lives at `~/.config/dotfiles-ai/chezmoi.toml` with separate
  persistent state.
- Public templates contain no usernames, home paths, account IDs, UUIDs,
  credential values, or private repository names.
- Vendor-managed OpenCode plugins remain vendor-managed and are validated, not
  copied.
- Removal from personal source never uses `.chezmoiremove` for transferred live
  targets.

## Validation Strategy

| Authority | Scope |
|---|---|
| `pytest` | DBSCTR, OpenCode, Herdr, auth, and public-safety contracts |
| `chezmoi data/cat/apply --dry-run` | Local data and rendered targets |
| `opencode debug config` | Resolved control plane |
| `bash -n`, `plutil -lint` | Scripts and LaunchAgent |
| Git/content scan | Public identifiers, credentials, and ownership overlap |
| Runtime status | One healthy Herdr server and current OpenCode integration |

## Risks

- Global target overlap can make apply order silently change configuration.
- LaunchAgent handoff can interrupt persistent Herdr panes.
- Local account identifiers can leak if templates are copied without conversion.
- External plugins can drift independently of this repository.

## Operations And Maintenance

- The maintainer owns compatibility with current chezmoi, OpenCode, Herdr, and
  supported Python versions.
- Security and compatibility reports use the repository issue tracker.
- Updates require preview before apply; breaking local-TOML or target ownership
  changes require migration and rollback notes.
- LaunchAgent handoff can terminate active panes; capture a Herdr snapshot and
  expect a brief restart even when session restoration succeeds.
- Retirement restores ownership to the prior source before disabling this
  source and booting out its LaunchAgent.
