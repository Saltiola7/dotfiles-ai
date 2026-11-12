---
name: database-audit
description: Audit repository database architecture and Python data-access boundaries for DuckDB, ClickHouse and Databricks, then propose evidence-backed refactor batches. Use for explicit database assessments and refactoring roadmaps.
---

# Database Audit

Assess the actual repository stack and produce an opinionated, evidence-backed
roadmap. Default to report-only. Keep one primary; specialists own techniques,
project policy owns targets/acceptance, QA owns checks, and DBSCTR owns later gates.

## Scope and snapshot

Read instructions, architecture/specs, manifests, lockfiles, CI, deployment
metadata and existing validation. Record commit and reviewed dirty/untracked
overlay, or identify an unversioned snapshot. Preserve local edits. Consult an
existing graph when useful, verifying source; do not generate one to begin.
Resolve material ambiguity from project facts before asking the user.

Inventory relevant SQL/DDL, migrations, Python clients/models/tests, notebooks,
pipeline/job definitions, bundle YAML, schema/storage contracts and consumers.
Map nested environments and actual engine/driver/platform versions. Disposition
generated, vendor, archived and unsupported artifacts. Review notebooks as source
without executing cells. Inventory is not review or completed check coverage.

Detect stacks from actual dependencies, calls, dialect and owned configuration;
an incidental mention is insufficient. This release covers DuckDB, ClickHouse
and Databricks. Disclose other engines as unsupported by these lenses, without
applying another engine's rules. No relevant database means not applicable with
evidence, not a reason to introduce one.

## Select relevant guidance

Load selected installed entrypoints through the catalog or exact managed sibling
fallback. Read resources progressively. Reuse DBSCTR's common selection contract
when needed. An equivalent native plugin can supply a lens; choose one reviewed
copy and record its revision. Do not fetch moving upstream instructions or install
missing guidance. Missing selected guidance leaves a visible coverage gap.

| Evidence | Relevant guidance |
|---|---|
| DuckDB SQL/relations | [duckdb-query](../duckdb-query/SKILL.md) |
| DuckDB analytical files, attachments or API verification | [duckdb-read-file](../duckdb-read-file/SKILL.md), [duckdb-attach-db](../duckdb-attach-db/SKILL.md), [duckdb-docs](../duckdb-docs/SKILL.md), for actual concerns only |
| ClickHouse schemas, queries, ingestion or config | [clickhouse-best-practices](../clickhouse-best-practices/SKILL.md), with relevant rule resources |
| ClickHouse workload/update/late-data architecture | [clickhouse-architecture-advisor](../clickhouse-architecture-advisor/SKILL.md) plus applicable engine rules |
| Databricks code/resources | [databricks-core](../databricks-core/SKILL.md) for context; static review needs no CLI or credentials |
| Lakeflow pipelines or direct Spark streaming | [databricks-pipelines](../databricks-pipelines/SKILL.md) or [databricks-spark-structured-streaming](../databricks-spark-structured-streaming/SKILL.md), according to selected API |
| Databricks orchestration/deployment | [databricks-jobs](../databricks-jobs/SKILL.md), [databricks-dabs](../databricks-dabs/SKILL.md), for actual definitions |
| Databricks governance, SQL warehouses or Python SDK/Connect | [databricks-unity-catalog](../databricks-unity-catalog/SKILL.md), [databricks-dbsql](../databricks-dbsql/SKILL.md), [databricks-python-sdk](../databricks-python-sdk/SKILL.md), only matching concerns |
| Python database/platform-client boundary | [python-database-boundaries](../python-database-boundaries/SKILL.md); relevant retry/async/resource/testing/type techniques as needed |

Mark other lenses not applicable with reasons rather than loading every bundle.
Databricks material is service-scoped, not generic Spark policy. Do not force
migrations, fashionable tools or findings for each lens.

## Review and validate

Trace schema/grain, query semantics, conversion, ownership, trust boundaries,
transaction/statement units, ordering, late/duplicate data, recovery and consumers.
Retain sound choices and state costs of alternatives. Apply rules using actual
versions, workloads and project policy. A heuristic, missing index or different
library alone is not a defect.

Use [QA](../qa/SKILL.md) for project-selected local authorities when execution is
authorized. Inspect commands first; preserve scope, environment, exit status,
findings and suppressions. Do not install engines/extensions/SDKs, change profiles,
authenticate, initialize state, attach databases, query/profile, submit remote jobs
or deploy merely to finish this report. Existing explicit execution authorization
remains usable; otherwise propose a bounded follow-up with target/cost constraints.

Keep static findings separate from live schema/plan/workload observations. Missing
live evidence cannot establish production performance, effective permissions or
readiness. EXPLAIN and SELECT may execute code, access files/network or incur
cost; inspect semantics rather than relying on a prefix or LIMIT.

## Report and handoff

Use [the report contract](references/report.md). Reconcile component/lens review
and check coverage separately. Deduplicate cross-layer root causes. When called
by `python-audit`, return a database subreport to that primary; do not recursively
invoke a full Python audit or create another roadmap/ledger.

Rank source/contract defects, advisory designs, modernization options and
performance hypotheses by impact, confidence, compatibility and justified effort.
Give bounded batches with prerequisites, retained contracts, owner and validation.
Debt/failed checks can coexist with audit completion; samples and gaps stay partial.

Return in conversation unless project/user authority selects an artifact path.
Do not copy consumer evidence into shared source, create tickets or begin fixes.
Selected remediation reuses DBSCTR and QA, without implied deployment authority.
