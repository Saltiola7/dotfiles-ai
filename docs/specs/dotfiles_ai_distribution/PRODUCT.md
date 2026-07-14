# dotfiles-ai Product Intent

## Users And Outcomes

Developers should be able to install one public configuration repository and
receive a working DBSCTR, OpenCode, and Herdr environment without adopting the
maintainer's personal paths, account identifiers, or secrets.

The maintainer must be able to migrate an existing installation without losing
working configuration or allowing two chezmoi repositories to own the same
target files.

## Core Journeys

1. A developer copies the documented local TOML example, supplies machine-local
   values, initializes the independent chezmoi source, previews, and applies it.
2. OpenCode loads the managed control plane and DBSCTR tools from complete,
   rendered configuration.
3. Herdr runs on macOS with optional 1Password integration; absence of
   1Password never blocks Herdr or shell startup.
4. An existing user verifies parity, transfers ownership, and can roll back
   without deleting live configuration.

## Constraints And Trust

- Public Git history contains no credentials or machine-local identifiers.
- The real local TOML remains outside the Git checkout.
- macOS is the initial supported platform.
- Existing personal configuration remains authoritative until live cutover
  validation passes.
- Repository paths are not modeled until a concrete consumer needs them.

## Success Evidence

- Isolated rendering passes with and without optional 1Password values.
- OpenCode resolves the expected agents, commands, skills, and DBSCTR tools.
- Herdr configuration and LaunchAgent plists parse and run without embedded
  credentials.
- Personal and `dotfiles-ai` chezmoi managed-target sets do not overlap after
  cutover.
