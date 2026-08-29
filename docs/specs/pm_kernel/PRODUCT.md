# PM Kernel Product Intent

## Users And Outcomes

The primary user is an OpenCode operator maintaining detailed local engineering
context while reporting selected outcomes through Jira. Direct PM invocations need
deterministic, collision-safe records without treating an external board as
complete project memory or making reporting data lifecycle authority.

Success means each local ticket is independently readable and queryable, operators
can retrieve relevant dependencies and provenance, Jira receives deliberate
sprint-sized narratives only on request, and Sprint Review reports remain factual
and reproducible from bounded source selections.

## Non-Goals

- Replacing human prioritization, acceptance, or Jira publication approval.
- Treating story points as productivity measures or imposing a sprint commitment.
- Exposing private Jira or lifecycle evidence publicly.
- Requiring PostgreSQL for local work.

## Core Journeys

1. An operator directly invokes PM Kernel to record already authoritative evidence
   as a reporting ticket and refine its reporting readiness.
2. An operator selects any useful local ticket set, reviews a standalone Jira
   rollup preview, and explicitly approves that exact external write.
3. An operator selects Done Jira work and optional goals to generate a private,
   factual Sprint Review report.
4. An operator enables PostgreSQL for richer search, graph traversal, provenance,
   and coordination without changing lifecycle authority.

## Constraints

- Ticket files remain useful in ordinary editors and local comparisons.
- Mutable workflow data cannot cause path churn.
- Missing evidence remains unknown rather than inferred.
- Jira project configuration and credentials remain machine-local.
- Disabled optional features create no runtime resources.

## Privacy And Accessibility

Ticket bodies and reports may contain private project context. Public research and
telemetry exclude their text and identifiers. Markdown reports use meaningful
headings, text equivalents for informative visuals, and no color-only meaning.

## Compatibility And Retirement

Migration preserves every selected backlog row and its source evidence in the
explicit local PM workflow. Discovery, DBSCTR, DKS, Initiative handling, and
autonomous R&D never read those files. PostgreSQL or Jira adapters may retire
independently because PM files are reporting inputs rather than lifecycle authority.

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
