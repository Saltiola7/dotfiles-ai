---
name: python-database-boundaries
description: Design and review Python database clients, sessions, transactions, pooling, async boundaries and typed row conversions. Use when an actual Python data-access boundary changes or is explicitly audited.
---

# Python Database Boundaries

Trace callers and domain values through the driver/ORM to the database, then back
through rows, streams and failures. Preserve project-selected engines, drivers,
ORM, versions, migration owner and validation authority. SQLAlchemy, DBAPI and
Arrow are conditional examples, not required dependencies.

Establish the actual connection/session/result owner, transaction or statement
unit, concurrency model, target and credentials boundary. Separate borrowed from
owned handles and client factories from mutable transaction state. Keep commit,
retry, cleanup and cancellation responsibilities at the layer that can decide
the whole operation's outcome. Avoid new abstractions when existing boundaries
already express those responsibilities clearly.

Read [boundary techniques](references/boundaries.md) for relevant resource,
transaction/retry, async, query safety, conversion and migration questions.
Select engine guidance through the Data module for SQL/storage/platform semantics;
this skill does not redefine them. Databricks SDK control-plane calls, Spark
actions and SQL connector sessions have different effects and lifetimes.

Trace representative callers, failures and cleanup. Distinguish source/contract
contradictions from advisory designs and unmeasured performance hypotheses.
State unsupported driver/version behavior rather than assuming uniform DBAPI
guarantees. A mocked integration cannot prove production isolation or retry safety.

Use existing test/checker authorities. Consider zero/one/many rows, NULL/precision,
early stream exit, acquisition/commit failure, concurrent ownership and ambiguous
remote completion when they are actual contracts. Suggest real-engine checks
only for claims mocks cannot establish. Loading this guidance does not authorize
installing a driver, authenticating, executing queries, migrating or remote work.
Reuse explicit task authorization and keep missing evidence visible.

Repository audits remain report-only by default. Hand findings to the current
primary and existing QA evidence; do not create another ledger or start fixes.
