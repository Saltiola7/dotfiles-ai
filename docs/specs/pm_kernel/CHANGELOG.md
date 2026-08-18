# PM Kernel Changelog

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
