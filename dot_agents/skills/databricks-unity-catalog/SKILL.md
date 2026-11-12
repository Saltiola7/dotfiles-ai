---
name: databricks-unity-catalog
metadata:
  version: "0.3.0"
description: "Review Databricks Unity Catalog ownership, privileges, row filters, masks, external locations and lineage; perform workspace operations only within existing authorization."
license: LicenseRef-Databricks
---

> Modified by dotfiles-ai: scoped for project policy, static review and authorized Databricks Services work. See `UPSTREAM.md` for provenance and changes.

# Unity Catalog

## Scope and execution boundaries

Use this bundle only within or connecting to Databricks Services, under the
included `LICENSE.upstream` and `NOTICE.upstream`. It is not generic Spark guidance.

For a repository audit, review source, SQL, bundle configuration and declared
runtime/dependency evidence first. Do not install or upgrade tools, authenticate,
select or change profiles, query a workspace, execute notebooks/examples, or
deploy resources merely to complete a static review. Record unavailable runtime,
workspace and performance evidence as coverage gaps. Examples below illustrate
APIs; they do not authorize their side effects.

For requested live work, retain the already selected workspace, profile,
authentication provider, runtime and dependency constraints. Resolve a target only
when missing or conflicting; do not repeatedly ask for an already selected
profile. Check the selected tool's actual version/help and current official
documentation for the specific operation. Propose a necessary migration or tool
upgrade separately instead of requiring the newest CLI for every task.

Read only relevant references. If a named sibling skill is unavailable, state the
guidance gap and use current official documentation within scope; do not install
an entire skill bundle. Treat design defaults as workload-dependent recommendations,
not automatic defects. Keep review findings distinct from measured execution
results. DBSCTR owns authorized remediation and delivery.

For live CLI, authentication or workspace targeting, read
[databricks-core](../databricks-core/SKILL.md) and reuse the selected context.


Guidance for Unity Catalog **governance** — access control, the privilege model,
external locations, securable DDL, and fine-grained access — plus system tables and
volume file operations.

> **Before running `databricks` CLI commands, confirm the CLI and the subcommand exist.**
> Inspect the selected version/help for the exact operation rather than enforcing a universal minimum. Several
> subcommands shown here (`experimental aitools`, `system-schemas`, `external-lineage`,
> `grants`) vary by version or workspace availability; if one is missing or rejects a flag,
> fall back to the SQL form or the Python SDK rather than guessing. Each reference notes its
> own version floor where relevant.

## When to Use This Skill

Use this skill when:

**Governance & access control (start here):**
- **Granting or revoking access** — `GRANT`/`REVOKE`, the UC privilege model, ownership (`ALTER … OWNER TO`), `SHOW GRANTS`, "who can read/write this table?"
- **Row- and column-level security** — row filters, column masks, dynamic views with `current_user()` / `is_account_group_member()`
- **External locations & storage credentials** — `CREATE STORAGE CREDENTIAL`, `CREATE EXTERNAL LOCATION`, backing external tables/volumes
- **Securable DDL & metadata** — creating/altering catalogs, schemas, managed vs external tables, views; comments, tags, table properties, ownership

**Observability & files:**
- Working with **volumes** (upload, download, list files in `/Volumes/`)
- Querying **lineage** (table dependencies, column-level lineage)
- Analyzing **audit logs** (who accessed what, permission changes)
- Monitoring **billing and usage** (DBU consumption, cost analysis)
- Tracking **compute resources** (cluster usage, warehouse metrics)
- Reviewing **job execution** (run history, success rates, failures)
- Analyzing **query performance** (slow queries, warehouse utilization)
- Profiling **data quality** (data profiling, drift detection, metric tables)

## Reference Files

| Topic | File | Description |
|-------|------|-------------|
| **Access Control** | [references/1-access-control.md](references/1-access-control.md) | Privilege model, securable hierarchy, GRANT/REVOKE, ownership, inheritance, `SHOW GRANTS` |
| **External Locations** | [references/2-external-locations.md](references/2-external-locations.md) | Storage credentials (AWS/Azure/GCP), external locations, validation |
| **Securables DDL** | [references/3-securables-ddl.md](references/3-securables-ddl.md) | CREATE/ALTER/DROP catalogs/schemas/tables/views, comments, tags, ownership |
| **Fine-Grained Access** | [references/4-fine-grained-access.md](references/4-fine-grained-access.md) | Row filters, column masks, dynamic views |
| System Tables | [references/5-system-tables.md](references/5-system-tables.md) | Lineage, audit, billing, compute, jobs, query history |
| Volumes | [references/6-volumes.md](references/6-volumes.md) | Volume file operations, permissions, best practices |
| Data Profiling | [references/7-data-profiling.md](references/7-data-profiling.md) | Data profiling, drift detection, profile metrics |

## Quick Start

### Create Unity Catalog Objects (CLI)

**Use `--json` for `create` commands.** Positional argument order differs per command and
has changed across CLI versions, so `--json` is the order-independent, version-stable form
shown throughout this skill.

```bash
# Create a catalog
databricks catalogs create --json '{"name": "my_catalog"}'

# Create a schema
databricks schemas create --json '{"name": "my_schema", "catalog_name": "my_catalog"}'

# Create a managed volume
databricks volumes create --json '{
  "catalog_name": "my_catalog",
  "schema_name": "my_schema",
  "name": "my_volume",
  "volume_type": "MANAGED"
}'

# List catalogs, schemas, volumes (read commands take simple positional args)
databricks catalogs list
databricks schemas list my_catalog
databricks volumes list my_catalog.my_schema
```

Positional `create` args still work if you prefer them, but the order is **not** uniform
across commands — this is the per-command order (and the reason `--json` is recommended):

| Command | Positional `create` order |
|---------|---------------------------|
| `databricks catalogs create` | `NAME` |
| `databricks schemas create`  | `NAME CATALOG_NAME` |
| `databricks volumes create`  | `CATALOG_NAME SCHEMA_NAME NAME VOLUME_TYPE` |

> **CLI surface varies by version.** If a `databricks` subcommand or positional signature is
> missing in your install, prefer `--json`, the SQL form, or the Python SDK rather than
> guessing flags.

### Volume File Operations (CLI)

`databricks fs` requires the `dbfs:` scheme prefix even for UC Volume paths — without it the CLI treats the path as local filesystem and errors with `no such directory`.

```bash
# List files in a volume
databricks fs ls dbfs:/Volumes/catalog/schema/volume/path/

# Upload a directory's contents to a volume (-r copies contents, not the directory itself)
databricks fs cp -r --overwrite /tmp/data dbfs:/Volumes/catalog/schema/volume/dest

# Download a file from a volume
databricks fs cp dbfs:/Volumes/catalog/schema/volume/file.csv /tmp/file.csv

# Create a directory in a volume
databricks fs mkdirs dbfs:/Volumes/catalog/schema/volume/new_folder
```

### Grant & Revoke Access

`GRANT`/`REVOKE` is the core governance operation. See [references/1-access-control.md](references/1-access-control.md) for the full privilege model.

```sql
-- Grant read access on a schema to a group
GRANT USE CATALOG ON CATALOG analytics TO `data_readers`;
GRANT USE SCHEMA ON SCHEMA analytics.gold TO `data_readers`;
GRANT SELECT ON SCHEMA analytics.gold TO `data_readers`;

-- Who can access this table?
SHOW GRANTS ON TABLE analytics.gold.customers;

-- Revoke
REVOKE SELECT ON SCHEMA analytics.gold FROM `data_readers`;
```

### Enable System Tables Access

```sql
-- Grant access to system tables
GRANT USE CATALOG ON CATALOG system TO `data_engineers`;
GRANT USE SCHEMA ON SCHEMA system.access TO `data_engineers`;
GRANT SELECT ON SCHEMA system.access TO `data_engineers`;
```

### Common Queries

```sql
-- Table lineage: What tables feed into this table?
SELECT source_table_full_name, target_table_full_name
FROM system.access.table_lineage
WHERE target_table_full_name = 'catalog.schema.table'
  AND event_date >= current_date() - 7;

-- Audit: Recent permission changes
SELECT event_time, user_identity.email, action_name, request_params
FROM system.access.audit
WHERE action_name LIKE '%GRANT%' OR action_name LIKE '%REVOKE%'
ORDER BY event_time DESC
LIMIT 100;

-- Billing: DBU usage by workspace
SELECT workspace_id, sku_name, SUM(usage_quantity) AS total_dbus
FROM system.billing.usage
WHERE usage_date >= current_date() - 30
GROUP BY workspace_id, sku_name;
```

`table_lineage` exposes table/path dependencies. For column-level relationships,
use `system.access.column_lineage` and its `source_column_name` /
`target_column_name` fields; do not select column names from `table_lineage`.
Check the [lineage system-table schemas](https://docs.databricks.com/aws/en/admin/system-tables/lineage).

## Running SQL from the CLI

> **`databricks experimental aitools tools query` is an experimental command.** The
> `experimental` namespace is not guaranteed to be stable across CLI versions and may be
> absent in your install. Prefer running system-table SQL from a **SQL warehouse** (SQL
> editor, scheduled query) or the **Python SDK** (`w.statement_execution.execute_statement`),
> or a **notebook**. Use the experimental CLI only for quick ad-hoc checks.

> **Getting the IDs these examples use.** `WAREHOUSE_ID` — run `databricks warehouses list`
> (or copy it from a SQL warehouse's *Connection details* in the UI). `METASTORE_ID` (used in
> [references/5-system-tables.md](references/5-system-tables.md)) — `w.metastores.current().metastore_id`
> via the SDK, or the Catalog UI → metastore details.

Experimental CLI form (convenience only):

```bash
databricks experimental aitools tools query --warehouse WAREHOUSE_ID "
  SELECT source_table_full_name, target_table_full_name
  FROM system.access.table_lineage
  WHERE event_date >= current_date() - 7
"
```

Stable SDK fallback (works on any CLI version):

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

w = WorkspaceClient()
resp = w.statement_execution.execute_statement(
    warehouse_id="WAREHOUSE_ID",
    statement="""
        SELECT source_table_full_name, target_table_full_name
        FROM system.access.table_lineage
        WHERE event_date >= current_date() - 7
        LIMIT 100
    """,
)
state = resp.status.state if resp.status else None
handle = {"statement_id": resp.statement_id, "state": state.value if state else None}
if state in {StatementState.PENDING, StatementState.RUNNING}:
    # Return the handle; follow up with get_statement using the same ID and a
    # project-selected overall polling deadline. Do not resubmit the statement.
    print(handle)
elif state == StatementState.SUCCEEDED:
    if resp.result is None:
        print({**handle, "result": "No inline result; fetch by statement ID"})
    else:
        for row in resp.result.data_array or []:
            print(row)
        if resp.result.next_chunk_index is not None:
            print({**handle, "next_chunk_index": resp.result.next_chunk_index})
else:
    error = resp.status.error if resp.status else None
    # Preserve failure state/ID/code; route detailed diagnostics through the
    # existing safe error handler instead of printing raw query/credential data.
    raise RuntimeError("SQL statement did not succeed", {
        **handle, "error_code": error.error_code if error else None,
    })
```

`execute_statement` can return a pending/running handle after its server-side wait,
or a terminal failure without result data. Inspect status before accessing results;
retrieve remaining chunks explicitly when a complete result is required. See the
[Statement Execution lifecycle](https://docs.databricks.com/aws/en/dev-tools/sql-execution-tutorial).

> **CLI surface varies by version.** If a `databricks` subcommand (e.g. an `experimental`
> tool, `system-schemas`, or `external-lineage`) is missing, fall back to the SQL warehouse
> or the Python SDK shown above rather than guessing flags.

## Best Practices

1. **Grant minimal access** - Apply least privilege; grant at the narrowest securable that works
2. **Filter by date** - System tables can be large; always use date filters
3. **Use appropriate retention** - Check your workspace's retention settings
4. **Schedule reports** - Create scheduled queries for regular monitoring
5. **Prefer SQL/SDK over experimental CLI** - For anything beyond quick checks

## Related Skills

This skill owns Unity Catalog **governance**: access control, the privilege model,
external locations / storage credentials, securable DDL, fine-grained access, system
tables, and volumes. For adjacent concerns, use the sibling skill instead:

- **databricks-core** (declared parent) — auth, profile selection, generic CLI, and catalog/table *exploration*
- **[databricks-metric-views](https://github.com/databricks/databricks-agent-skills/blob/9f105c9aa0b0f2f9f3aa914c9f341985f765394e/skills/databricks-metric-views/SKILL.md)** — metric view definitions / DDL (`WITH METRICS LANGUAGE YAML`)
- **[databricks-iceberg](https://github.com/databricks/databricks-agent-skills/blob/9f105c9aa0b0f2f9f3aa914c9f341985f765394e/skills/databricks-iceberg/SKILL.md)** — Managed Iceberg, External Iceberg Reads (fka Uniform), and **Iceberg REST Catalog (IRC) credential *vending*** for external engines — distinct from UC storage credentials (see [references/2-external-locations.md](references/2-external-locations.md))
- **[databricks-ml-training](https://github.com/databricks/databricks-agent-skills/blob/9f105c9aa0b0f2f9f3aa914c9f341985f765394e/skills/databricks-ml-training/SKILL.md)** — UC model registration and `@prod`/`@challenger` aliases
- **[databricks-vector-search](https://github.com/databricks/databricks-agent-skills/blob/9f105c9aa0b0f2f9f3aa914c9f341985f765394e/skills/databricks-vector-search/SKILL.md)** — Vector Search indexes
- **[databricks-pipelines](../databricks-pipelines/SKILL.md)**, **[databricks-jobs](../databricks-jobs/SKILL.md)**, **[databricks-lakeflow-connect](https://github.com/databricks/databricks-agent-skills/blob/9f105c9aa0b0f2f9f3aa914c9f341985f765394e/skills/databricks-lakeflow-connect/SKILL.md)** — *producing* tables via pipelines/jobs/managed ingestion
- **[databricks-lakebase](https://github.com/databricks/databricks-agent-skills/blob/9f105c9aa0b0f2f9f3aa914c9f341985f765394e/skills/databricks-lakebase/SKILL.md)** — Lakebase / synced tables (OLTP)
- **[databricks-ai-functions](https://github.com/databricks/databricks-agent-skills/blob/9f105c9aa0b0f2f9f3aa914c9f341985f765394e/skills/databricks-ai-functions/SKILL.md)** — AI functions such as `ai_mask` / `ai_classify` (AI *transforms*, **not** access control — see [references/4-fine-grained-access.md](references/4-fine-grained-access.md))
- **[databricks-aibi-dashboards](https://github.com/databricks/databricks-agent-skills/blob/9f105c9aa0b0f2f9f3aa914c9f341985f765394e/skills/databricks-aibi-dashboards/SKILL.md)** — AI/BI dashboards on UC data
- **[databricks-synthetic-data-gen](https://github.com/databricks/databricks-agent-skills/blob/9f105c9aa0b0f2f9f3aa914c9f341985f765394e/skills/databricks-synthetic-data-gen/SKILL.md)** — generating data stored in UC volumes

### Roadmap (not yet covered — deferred to a later version)

These governance areas are intentionally **out of scope for v0.3.0** and planned for later:

- Delta Sharing / Marketplace / Clean Rooms
- Lakehouse Federation (connections + foreign catalogs)
- ABAC / governed tags as policy

## Resources

- [Unity Catalog Privileges & Securable Objects](https://docs.databricks.com/data-governance/unity-catalog/access-control/privileges-reference)
- [Unity Catalog System Tables](https://docs.databricks.com/admin/system-tables)
- [Audit Log Reference](https://docs.databricks.com/admin/account-settings/audit-logs)
- [Manage External Locations and Storage Credentials](https://docs.databricks.com/connect/unity-catalog/cloud-storage)
