# PM Kernel Changelog

## 2026-08-19 - PMK-002 Private Adapter Activation

- Added owned host-loopback PostgreSQL forwarding, stdin-only Podman secret
  provisioning, 1Password-backed host access, verified seven-generation weekly
  backups, and retained-volume disable behavior.
- Added strict ACLI create/update previews, deterministic publication labels,
  private pending/unknown/success receipts, bounded reconciliation, and
  machine-local project/type wrappers. No live Jira mutation was performed.
- Affected QA passed 116 tests and canonical ticket validation. The pinned ARM64
  PG19 Beta 3 service is healthy; relational and graph projections contain all
  146 tickets; host listening is loopback-only; a real dump and scratch restore
  passed; and the weekly LaunchAgent is loaded. Independent review ended clean.
  Gate Commits: `998214e`, `79bd60c`, `0d5a3fc`, `5eadd94`. Gate Exceptions:
  none. The local OpenCode permission target retained unrelated drift and was not
  overwritten. Intended Final Push: feature branch and draft PR into `main`.

## 2026-08-19 - PMK-001-F1 PostgreSQL 19 Repair

- Corrected the PostgreSQL 19 Beta 3 property-graph migration to use supported
  drop/recreate syntax and graph-local vertex aliases while preserving relational
  data across schema reapplication.
- Restricted activation to the canonical Docker Hub Beta 3 image name plus exact
  digest and added accepted/rejected rendering coverage.
- Affected QA passed 69 tests. The exact ARM64 Beta 3 image applied the schema
  twice, preserved a seeded ticket, and returned it through `GRAPH_TABLE`.
  Independent review findings were resolved. Gate Commit: `cdb7df5`. Gate
  Exceptions: none. Deployment: reserved for the post-merge activation cycle.
  Intended Final Push: follow-up draft pull request into the PMK-001 branch.

## 2026-08-18 - PMK-001 Canonical Ticket Context

- Replaced six lifecycle backlog tables with 143 independently validated,
  provenance-bound tickets and added one PM cycle ticket.
- Added dependency-free validation and recoverable migration, evidence-gated PM
  skills, revision-bound fake Jira publication, private Sprint Review reports,
  sanitized envelope/ticket projection, and optional pinned PostgreSQL 19
  SQL/PGQ deployment.
- Full QA passed 339 tests with one expected skip before review remediation;
  focused final PM/distribution evidence passed 23 tests. Independent review
  ended with no findings. Managed deployment, idempotence, command resolution,
  144-ticket validation, and fixed-commit audit passed. Gate Exceptions: none.
  Gate Commits: `31d6c0c`, `7a43c51`, `b872a08`. PostgreSQL and live Jira writes:
  not run because both remain explicitly unconfigured. Intended Final Push:
  feature branch and draft pull request into protected `main`.
