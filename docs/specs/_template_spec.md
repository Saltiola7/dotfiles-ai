# [Spec Name]

**Status:** Draft | Experimental | Stable
**Created:** YYYY-MM-DD
**Last updated:** YYYY-MM-DD

## Engineering Profile

### Defaults

| Field | Value |
|---|---|
| Deliverable | |
| Languages/frameworks | |
| Applicable modules | |
| Runtime/platform support | |
| Public compatibility | |
| Trust/data classification | |
| Operational owner | |

## Overview

Brief description of what this bounded context covers.

## File Map

| Path | Purpose |
|------|---------|
| `path/to/file` | Description |

## Architecture

Describe the high-level architecture. Implement each required view selected by
the Visual Evidence Plan below; prose does not silently replace a required view.

## Visual Evidence

The Visual Evidence Plan uses `required: TYPE` or `not_applicable: REASON`.

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | | | | |
| Interaction | | | | |
| State | | | | |
| Data/trust | | | | |
| Schema | | | | |
| Dependency/deployment | | | | |
| Quantitative | | | | |

Each required Mermaid visual includes `accTitle` and `accDescr`, meaningful
directional labels, and an adjacent **Text Equivalent**. A quantitative chart
also includes an adjacent source-data table with values, units, period, source,
denominator, and uncertainty. Verify non-trivial Mermaid in the rendered GitHub
pull request and update represented facts in the same change.

## Domain

### Bounded Context

Name the bounded context and adjacent contexts.

### Entities

- **EntityName** — description

### Value Objects

- **ValueObjectName** — description

### Domain Events

- `EventNamePastTense` — when/why it fires

### Ubiquitous Language

| Term | Definition |
|------|-----------|
| term | meaning in this context |

## Behavior Scenarios

### Feature: [Feature Name]

**Scenario: [Happy path]**
- Given [precondition using domain terms]
- When [action using domain terms]
- Then [expected outcome]

**Scenario: [Error/edge case]**
- Given [precondition]
- When [action that triggers the edge case]
- Then [expected error handling behavior]

## Contracts & Invariants

### Function: function_name
- **Pre:** precondition
- **Post:** postcondition

### Entity/Module: Name
- **Invariant:** what must always be true

## Gate Ledger

| Gate | Capability | Applicability | Result | Authority/evidence | Exception | Owner |
|---|---|---|---|---|---|---|

Applicability is `required` or `not_applicable`. Result is `pending`, `passed`,
`failed`, `unavailable`, or `not_run`. Exceptions are user-approved `deferred`
or `accepted_risk` records with rationale, owner, and review condition.

For a new V3.2 cycle, export these decisions as JSON for
`dbsctrctl start --plan PATH`. The plan names this committed README and defines
every gate; each `not_applicable` gate includes its reason.

## Artifact Review

- README: reviewed; changed or no-change reason
- BACKLOG: reviewed; active cycle item
- CHANGELOG: reviewed; completion entry required at cycle close

## Verification

```bash
# Commands to verify the system is working
```

## Gotchas

- Known sharp edges and caveats.
