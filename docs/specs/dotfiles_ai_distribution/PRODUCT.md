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
5. A developer opts into Hermes orchestration and receives context-isolated
   backlog refinement plus resumable OpenCode Discovery workers.
6. The operator uses host or VM Herdr to inspect Hermes and resume blocked
   OpenCode sessions, explicitly authorizes implementation, and manually manages
   resulting draft pull requests.
7. An opted-in operator receives bounded CLI/JSON evidence about merged
   improvement effects while private runtime state conservatively adjusts worker
   cadence without changing source configuration or granting workers delivery
   authority.
8. An operator enters a client-specific Fedora VM, reattaches to persistent VM
   Herdr panes, and runs auto-approved OpenCode against only declared host paths.
9. Host R&D reviews sanitized evidence from host and VM histories, pauses for
   explicit approval, and hands implementation to a visible configured-workspace Build
   session without moving databases or credentials across trust boundaries.
10. An opted-in developer reaches each managed VM from authorized tailnet hosts
    with native Herdr remote attach while public configuration remains free of
    peer identity, policy, and enrollment secrets.
11. A developer or teammate keeps coherent automatic Gate Commits on an isolated
    feature branch and submits a draft pull request into the configured `main`
    branch; automation never commits or pushes cycle work directly to `main`.
12. High-impact P0/P1 claims enter Discovery automatically, while an operator
    reviews waiting P2/P3 claims through `/dbsctr-backlog`; promotion remains a
    separate governed capability.
13. An operator combines completed feature branches on an ephemeral batch branch,
    reviews the exact merge commits, and explicitly publishes the batch for normal
    pull-request review without granting Hermes authority over `main`.
14. An operator can inspect bounded local Herdr pane history for the prior 30 days
    without publishing terminal content or weakening filesystem ownership checks.

## Visual Evidence

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | required: product journey boundary flowchart | Where does the operator cross from portable setup into isolated automation and governed delivery? | Core Journeys and context README architecture | Product owner; journey or trust-boundary changes |
| Interaction | not_applicable: detailed approval ordering is canonical in the context README sequence | - | Context README Visual Evidence | Distribution owner |
| State | not_applicable: product outcomes do not define a separate state machine | - | Core Journeys | Product owner |
| Data/trust | required: product journey boundary flowchart | Which outcomes must preserve local identity and secrets? | Constraints And Trust | Product owner; privacy outcome changes |
| Schema | not_applicable: Product Intent owns outcomes rather than configuration schema | - | Context README contracts | Distribution owner |
| Dependency/deployment | not_applicable: deployment topology is canonical in the context README | - | Context README Visual Evidence | Distribution owner |
| Quantitative | not_applicable: success is verified by invariants and runtime checks, not a comparative dataset | - | Success Evidence | Product owner |

```mermaid
flowchart LR
    accTitle: dotfiles-ai product journey boundaries
    accDescr: A developer configures portable public defaults with private local values, applies managed host and workspace environments, explicitly opts into automation, approves implementation, and reviews draft pull requests while secrets and identities remain local.
    P[Public repository] -->|Add private local values| C[Machine-local configuration]
    C -->|Preview and apply| W[Managed host and workspaces]
    W -->|Optional opt-in| A[Isolated automation profiles]
    A -->|Discovery asks and waits| U[Operator approval]
    U -->|Explicit proceed| I[Isolated implementation cycle]
    I -->|Draft pull request| R[Human review and merge]
    C -.->|Never publish| X[Secrets and machine identity]
```

**Text Equivalent:** Public defaults become usable only after private local
values are supplied. Applying them creates managed host and workspace
environments; automation remains optional and isolated. Discovery waits for the
operator before implementation, and delivery ends at a draft pull request for
human review. Secrets and machine identity never enter the public repository.
The product owner updates this view when a core journey, privacy boundary, or
approval outcome changes.

## Constraints And Trust

- Public Git history contains no credentials or machine-local identifiers.
- Tailnet policy, tags, peer names, and enrollment credentials remain external
  private state; shared Tailscale defaults are disabled.
- The real local TOML remains outside the Git checkout.
- macOS is the initial supported platform.
- Fedora Linux is supported only inside managed Lima client VMs; it is not a
  general standalone-host commitment.
- Existing personal configuration remains authoritative until live cutover
  validation passes.
- The writable source path is machine-local and never a public default or
  general navigation allowlist.
- Hermes owns scheduling, Kanban, and delegation; Herdr owns optional terminal
  presentation; OpenCode owns implementation; the DBSCTR ledger owns lifecycle
  coordination and approval state.
- Adaptive lens cadence remains between monthly and daily, allows at most three
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
- Enabled and disabled Hermes profiles, backlog mirrors, Herdr attachment, and
  review jobs are repeatable, while Discovery still pauses for human input.
- Concurrent workers claim distinct opportunities durably, recover exact
  sessions without duplicate work, and cannot merge their draft pull requests.
- Every claim carries P0-P3 priority; P0/P1 may enter Discovery automatically,
  while P2/P3 remain claimed and visible through a report-only operator queue.
- Confirmed P2/P3 promotion atomically enters Discovery; batch previews and
  integration retain exact source SHAs while batch publication remains an
  explicit operator action and `main` remains pull-request protected.
- Herdr scrollback is bounded to 10 MB and private daily snapshots older than 30
  days are pruned without following symlinks or changing source history.
- A cycle started from `main` creates an isolated feature branch, while a cycle
  started in a dedicated clean teammate worktree may retain that feature branch;
  both publish only a draft pull request into configured `main`.
- Monthly cadence decisions are reproducible from sanitized evidence, preserve
  the human Discovery and delivery boundaries, and fail closed on malformed
  authoritative state.
- Client mounts, protected submodules, VM identity, restored auto-approved
  sessions, bounded federated evidence, and guest configuration revisions are
  verified on the real Lima runtime before sandbox deployment passes.
- Disabled Tailscale rendering, secret-safe one-off enrollment, direct SSH, and
  cross-host Herdr reattachment are verified before tailnet deployment passes.
