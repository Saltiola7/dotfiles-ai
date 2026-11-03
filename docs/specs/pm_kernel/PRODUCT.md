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

A personal Obsidian user may separately opt into automatic projection refresh
after editing canonical notes. The desired outcome is consistent SQL reports
without manual rebuild steps, while native Bases and ordinary editors retain
direct access to the notes. This journey uses the existing personal lab schema;
it neither creates PM reporting tickets nor makes personal notes lifecycle
evidence. [OBSIDIAN.md](OBSIDIAN.md) owns the adapter behavior.

## Non-Goals

- Replacing human prioritization, acceptance, or Jira publication approval.
- Treating story points as productivity measures or imposing a sprint commitment.
- Exposing private Jira or lifecycle evidence publicly.
- Requiring PostgreSQL for local work.
- Replacing personal note authority with a database, frozen report, or Prefect
  run; converting notes into the PM ticket schema; or publishing notes remotely
  through the optional adapter.

## Core Journeys

1. An operator directly invokes PM Kernel to record already authoritative evidence
   as a reporting ticket and refine its reporting readiness.
2. An operator selects any useful local ticket set, reviews a standalone Jira
   rollup preview, and explicitly approves that exact external write.
3. An operator selects Done Jira work and optional goals to generate a private,
   factual Sprint Review report.
4. An operator enables PostgreSQL for richer search, graph traversal, provenance,
   and coordination without changing lifecycle authority.
5. A personal operator explicitly enables the Obsidian adapter, edits notes, and
   receives validated derived generations plus refreshed SQL reports. Invalid
   input preserves the previous valid generation; unavailable Obsidian leaves
   refresh pending until the app returns. Disabling the adapter preserves notes
   and recoverable output.

## Constraints

- Ticket files remain useful in ordinary editors and local comparisons.
- Mutable workflow data cannot cause path churn.
- Missing evidence remains unknown rather than inferred.
- Jira project configuration and credentials remain machine-local.
- Disabled optional features create no runtime resources.
- The optional adapter uses the selected lab's exact uv runtime and lock,
  including Prefect 3.7.7, with a private localhost server and macOS watcher.
  Its operator owns service availability; sleep, logout, unavailable mounts, or a
  closed Obsidian app defer progress until reconciliation can resume.

## Privacy And Accessibility

Ticket bodies and reports may contain private project context. Public research and
telemetry exclude their text and identifiers. Markdown reports use meaningful
headings, text equivalents for informative visuals, and no color-only meaning.

The personal-note adapter keeps content, captures, configuration, and diagnostics
private on the host. Prefect records bounded orchestration metadata without note
text or raw tool output. Existing PM/Jira privacy rules remain unchanged.

## Compatibility And Retirement

Migration preserves every selected backlog row and its source evidence in the
explicit local PM workflow. Discovery, DBSCTR, DKS, Initiative handling, and
autonomous R&D never read those files. PostgreSQL or Jira adapters may retire
independently because PM files are reporting inputs rather than lifecycle authority.

The optional note adapter can retire independently of PM reporting. Its scoped
uninstall stops only its owned watcher and localhost server; canonical notes and
recoverable projections remain. The adapter's [Contract](OBSIDIAN.md#contract)
defines rollback and retention without granting authority to those projections.

## Visual Evidence

The table below retains the core PM workflow's canonical visuals. Additional
personal-note topology, ordering, state, and trust evidence is maintained in
[OBSIDIAN.md](OBSIDIAN.md#visual-evidence), with its accessible text equivalents;
it is not duplicated here.

| Concern | Decision |
|---|---|
| Boundary | required: authority diagram in the context README |
| Interaction | required: Jira publication sequence in the context README |
| State | required: ticket lifecycle in the context README |
| Data/trust | required: authority diagram in the context README |
| Schema | required: ticket/projection contract in the context README |
| Dependency/deployment | required: optional PostgreSQL topology in the context README |
| Quantitative | not_applicable: no product decision depends on a comparative metric |
