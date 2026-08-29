# Initiative Discovery

This Initiative delivers durable, compaction-safe decomposition and orchestration
for broad intent spanning bounded contexts and repositories.

The coordinator repository is `Saltiola7/dotfiles-ai`. The canonical machine
ledger is [`MANIFEST.json`](MANIFEST.json). Context homes retain their own
profiles, feature specifications, contracts, and tickets.

## Architecture

The coordinator captures and reconciles material intent. Approved context lanes
run in ownership-disjoint Herdr tabs. A ready delivery slice receives stable PM
Kernel tickets and may start an explicitly approved repository-local DBSCTR cycle
while the coordinator continues the remaining Initiative.

Cross-context contracts have one named home and immutable consumers. Fleet status
does not replace repository-local Cycle Records. Herdr and OpenCode identifiers
remain private operational correlation.

## Delivery Order

1. `lifecycle-foundation` defines the Initiative manifest, profile, readiness,
   compaction, and orchestration contracts.
2. `control-plane-orchestration` adds docs-only agents, typed session control,
   compaction context injection, and exact fork/fallback behavior.
3. `pm-ticket-handoff` makes specification-ready, ownership-safe ticket creation
   explicit without making PM Kernel the cross-repository authority.
4. `herdr-skill-deployment` installs the release-matched Herdr skill and validates
   the live managed runtime.

The control-plane and PM slices may proceed concurrently after the lifecycle
foundation. Herdr deployment follows the control-plane slice. The coordinated
release group completes only after all members provide current evidence.

`V3.38-1` is the self-bootstrap cycle for this mechanism. It may implement the
dependent lanes before the new launcher exists, but the manifest cannot promote
or complete those lanes until their normal validation and deployment evidence is
recorded. Later Initiatives receive no bootstrap exception.

## Privacy

The Initiative retains material statement coverage, not another raw transcript.
Public or Context7 research uses generic privacy-safe queries through Scout. Local
repository research uses Explore. No Initiative artifact stores credentials,
machine paths, or transient session identifiers.
