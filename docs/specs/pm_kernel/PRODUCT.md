# PM Kernel Product Intent

## Users And Outcomes

The primary user is an OpenCode operator maintaining detailed local engineering
context while reporting selected outcomes through Jira. Agents need deterministic,
collision-safe work records and enough evidence to refine, execute, and review
work without treating an external board as complete project memory.

Success means each local ticket is independently readable and queryable, agents
can retrieve relevant dependencies and provenance, Jira receives deliberate
sprint-sized narratives only on request, and Sprint Review reports remain factual
and reproducible from bounded source selections.

## Non-Goals

- Replacing human prioritization, acceptance, or Jira publication approval.
- Treating story points as productivity measures or imposing a sprint commitment.
- Exposing private Jira or lifecycle evidence publicly.
- Requiring PostgreSQL for local work.

## Core Journeys

1. An operator or agent records evidence as an intake ticket, resolves material
   questions, and marks it ready only when the PM gates pass.
2. A Build agent pulls one ready ticket, uses dependencies and ownership to avoid
   collisions, and records review evidence before completion.
3. An operator selects any useful local ticket set, reviews a standalone Jira
   rollup preview, and explicitly approves that exact external write.
4. An operator selects Done Jira work and optional goals to generate a private,
   factual Sprint Review report.
5. An operator enables PostgreSQL for richer search, graph traversal, provenance,
   and coordination without changing Git authority.

## Constraints

- Ticket files remain useful in ordinary editors, Git diffs, and code review.
- Mutable workflow data cannot cause path churn.
- Missing evidence remains unknown rather than inferred.
- Jira project configuration and credentials remain machine-local.
- Disabled optional features create no runtime resources.

## Privacy And Accessibility

Ticket bodies and reports may contain private project context. Public research and
telemetry exclude their text and identifiers. Markdown reports use meaningful
headings, text equivalents for informative visuals, and no color-only meaning.

## Compatibility And Retirement

Migration preserves every existing backlog row and its source evidence. The old
table format is retired only after fixed-commit audit and Hermes refinement read
ticket files. PostgreSQL or Jira adapters may later retire independently because
canonical Git tickets preserve work identity and history.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: authority diagram in the context README |
| Interaction | required: Jira publication sequence in the context README |
| State | required: ticket lifecycle in the context README |
| Data/trust | required: authority diagram in the context README |
| Schema | required: ticket/projection contract in the context README |
| Dependency/deployment | required: optional PostgreSQL topology in the context README |
| Quantitative | not_applicable: no product decision depends on a comparative metric |
