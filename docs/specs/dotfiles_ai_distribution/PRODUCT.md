# dotfiles-ai Product Intent

## Users And Outcomes

Developers should be able to install one public configuration repository and
receive a working DBSCTR, OpenCode, Herdr, and opt-in launchd R&D automation
environment without adopting the maintainer's personal paths, account
identifiers, or secrets.

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
5. A developer opts into R&D scheduling, supplies machine-local source and GitHub
   identity, and receives visible daily OpenCode R&D workers that review global
   history but publish only sanitized draft pull requests for this source.
6. The operator opens `herdr`, answers Discovery questions in blocked worker
   tabs, explicitly authorizes implementation, and manually manages resulting
   draft pull requests.
7. An opted-in operator receives bounded CLI/JSON evidence about merged
   improvement effects while private runtime state conservatively adjusts worker
   cadence without changing source configuration or granting workers delivery
   authority.

## Constraints And Trust

- Public Git history contains no credentials or machine-local identifiers.
- The real local TOML remains outside the Git checkout.
- macOS is the initial supported platform.
- Existing personal configuration remains authoritative until live cutover
  validation passes.
- The writable source path is machine-local and never a public default or
  general navigation allowlist.
- Launchd owns process scheduling, Herdr owns terminal presentation, OpenCode
  owns agent execution, and the DBSCTR ledger owns durable coordination.
- Adaptive cadence remains between weekly and daily, allows at most three
  nonterminal workers, halts on repeated failures, and requires manual reset.
- Private session, project, and repository provenance never appears in public
  findings, branches, documentation, or pull requests.

## Success Evidence

- Isolated rendering passes with and without optional 1Password values.
- OpenCode resolves the expected agents, commands, skills, and DBSCTR tools.
- Herdr configuration and LaunchAgent plists parse and run without embedded
  credentials.
- Personal and `dotfiles-ai` chezmoi managed-target sets do not overlap after
  cutover.
- Enabled and disabled launchd rendering, Herdr integration, and review jobs are
  repeatable, while Discovery questions still pause for human input.
- Concurrent workers claim distinct opportunities durably, recover exact
  sessions without duplicate work, and cannot merge their draft pull requests.
- Monthly cadence decisions are reproducible from sanitized evidence, preserve
  the human Discovery and delivery boundaries, and fail closed on malformed
  authoritative state.
