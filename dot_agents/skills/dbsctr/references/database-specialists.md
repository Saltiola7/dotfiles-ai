# Database specialist guidance

Use the existing common selection contract when needed. The Data module owns
outcomes and project-selected authority; these are conditional techniques.
The canonical Python technique triggers remain in the Python module.

| Actual task evidence | Preferred guidance |
|---|---|
| DuckDB query/relational SQL | `duckdb-query` |
| DuckDB file readers/schema conversion | `duckdb-read-file` |
| DuckDB attachments and database lifetimes | `duckdb-attach-db` |
| DuckDB version/API documentation question | `duckdb-docs` |
| ClickHouse schema/query/config/ingestion review | `clickhouse-best-practices` |
| ClickHouse workload architecture, late data, updates or preaggregation | `clickhouse-architecture-advisor` plus relevant engine rules |
| Actual Databricks project/target context | `databricks-core`; static review does not need setup/auth |
| Lakeflow pipeline definitions | `databricks-pipelines` |
| Direct Spark Structured Streaming code on Databricks | `databricks-spark-structured-streaming` |
| Databricks jobs/tasks/triggers | `databricks-jobs` |
| Databricks bundle targets/deployment definitions | `databricks-dabs` |
| Databricks governance/privileges/lineage | `databricks-unity-catalog` |
| Databricks SQL warehouse behavior | `databricks-dbsql` |
| Databricks Python SDK/Connect/API boundary | `databricks-python-sdk` |
| Python database/ORM/driver/control-plane boundary | `python-database-boundaries` |
| Explicit repository database assessment | `database-audit` |

Load the smallest set needed. An incidental import or stack mention is not a
request to install/authenticate/query. For explicit full repository assessment,
`database-audit` selects relevant lenses, records static/live/check coverage and
returns ordered refactor batches. `python-audit` delegates matching database
concerns without recursive audits or duplicate root causes.

Native ClickHouse plugin guidance may supply an equivalent selected lens; choose
one reviewed copy per task. Managed copies provide portable CLI availability,
not a second mandatory pass. A missing lens stays a guidance gap. MCP/CLI access
provides execution capability, not architectural policy or authorization.

Preserve actual engines, versions, targets, profiles, dependency/install owners
and validation authority. Static review works without services or credentials.
Live checks retain project authorization, cost/data limits and actual results.
No engine heuristic or version-specific recipe becomes a universal project gate.
Databricks material applies only to Databricks Services under its upstream license;
missing optional sibling skills do not authorize installation of a larger bundle.

Complete pinned resources, license/notices, original hashes/blobs, modes and
reversible adaptations are recorded under `python-data-sources/engines/sources.lock.json`
and `python-data-sources/databricks/sources.lock.json`; the five Python additions
use `python-data-sources/python/sources.lock.json`. Local boundary and audit
skills have no vendored upstream. Review complete bundles and patches on update,
then validate provenance, resource closure and exact-target delivery. Do not
fetch moving upstream instructions during ordinary execution. Retain previous
matching source/live evidence for recovery and preserve independent live edits.
