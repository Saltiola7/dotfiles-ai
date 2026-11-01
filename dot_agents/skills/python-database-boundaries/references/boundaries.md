# Python data-access techniques

Read relevant sections only. Verify version-specific advice against selected
package/server documentation; these questions are not universal defects.

## Lifetime and concurrency

Identify who creates, borrows, closes and invalidates each client/factory,
connection/session, cursor/result and stream. For SQLAlchemy, Session is mutable
transaction state; use separate sessions for concurrent threads/tasks under its
documented model. Closing and committing differ. Resolve required lazy ORM data
inside its valid lifetime or deliberately materialize domain values; do not
globally disable expiration merely to conceal detached-object errors.

Preserve borrowed handles. Inspect acquisition failure before context entry,
early return, exceptions during iteration, generator abandonment and cancellation.
Use actual driver context/transaction APIs rather than guessing commit/close
semantics. Bound buffering and how long consumers hold connections. Size pools
from actual worker/process counts and server capacity, not a universal constant.

DuckDB convenience/module connections and explicit connections have different
sharing implications. Inspect the selected API's concurrency model; successful
in-process threads do not prove multi-process writable-file safety. File-based
connections, remote SQL sessions and Spark sessions are different resources.

## Transactions and retries

Name the atomic unit and commit/rollback owner. Inspect autocommit, isolation,
implicit flush, savepoints and DDL behavior for the actual driver/engine. Leaf
functions should respect caller-owned units; do not remove required commits
under a generic context-manager assumption. Identify partial-batch visibility
and recovery information independently of a successful client return.

A timeout may leave a write committed remotely. Replay needs appropriate
idempotency, engine-supported deduplication or reconciliation. A failed statement
may invalidate the transaction; retry its documented unit with a bounded total
budget. Preserve cancellation; avoid multiplied SDK/driver/application retries.
Local cancellation does not prove remote work stopped.

Do not transfer another engine's transactional assumptions to ClickHouse.
Distinguish insert atomicity, table/partition/shard restrictions, async inserts
and supported transaction features at the selected version. Databricks jobs,
SDK submissions and distributed table operations need actual API completion and
replay contracts rather than a guessed connection rollback.

## Queries and secrets

Bind values through supported driver parameters. Identifiers, paths and SQL
fragments need separate validated choices/quoting; value placeholders cannot
substitute arbitrary SQL structure. Inspect bulk inserts and raw-text escape
hatches too. Resolve credentials only at the existing client boundary; do not
log connection strings, parameters, source data or unapproved raw exceptions.
Use existing secret-serialization guidance for credential-bearing objects.

EXPLAIN, profiling, UDFs, file readers, remote URLs and extension loading have
actual effects and costs. SELECT prefixes, LIMIT and rollback alone do not prove
safe read-only execution. Static review needs no statements submitted. Live
checks retain the existing authorized target and execution policy.

## Typed conversion and evolution

Distinguish missing row, SQL NULL, application None, empty and zero. Preserve
Decimal precision/scale, timezone/instant semantics, integer bounds, binary data
and parameter round trips. Arrow/pandas/Polars conversion can change nullable
types, timestamp resolution and materialization cost; inspect actual schemas and
APIs rather than assuming zero-copy behavior.

Use useful row-to-domain validation seams. Protocols can narrow driver coupling
without inventing a universal cross-engine query API. Typing is not runtime
validation. Keep project checker authority; do not hide stub limitations with
broad Any or unchecked casts.

Migration autogeneration proposes SQL; inspect it against schema and consumers.
Evaluate compatibility windows, backfill order, locks, partial failure and
recovery using actual DDL guarantees. Preserve project migration/installation
ownership; this skill does not select Alembic or an ORM.

## Validation and evidence

Use fast tests for binding/mapping/ownership, and selected-engine integration for
claims about isolation, DDL, query plans, conversion or actual resource semantics.
Mocks or a substitute engine cannot establish those contracts. Properties can
cover meaningful round-trip/null/precision invariants. Test exact transient
classes and ambiguous completion separately. Keep fixtures isolated.

Measure query count, transferred rows/bytes, buffering, pool wait and end-to-end
workload before performance refactors. State cold/warm/cache and server conditions;
a surrogate or microbenchmark does not establish production gains.

## Primary reference starting points

- [SQLAlchemy session lifecycle/concurrency](https://docs.sqlalchemy.org/en/20/orm/session_basics.html), for that selected release family; choose matching docs otherwise.
- [DuckDB Python DBAPI](https://duckdb.org/docs/stable/clients/python/dbapi) and [concurrency](https://duckdb.org/docs/stable/connect/concurrency).
- [ClickHouse insert/transaction guarantees](https://clickhouse.com/docs/concepts/features/operations/insert/transactions).
- [Databricks Python SQL Connector](https://docs.databricks.com/aws/en/dev-tools/python-sql-connector); select matching cloud, connector and runtime.

These links are lookup starting points, not pinned API guarantees. Installed
versions and project contracts determine applicability.
