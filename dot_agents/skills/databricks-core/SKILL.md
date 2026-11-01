---
name: "databricks-core"
metadata:
  version: "0.1.0"
description: "Resolve Databricks CLI capabilities and existing workspace context for authorized platform work; support static repository review without setup or connection requirements."
license: LicenseRef-Databricks
---

> Modified by dotfiles-ai: scoped for project policy, static review and authorized Databricks Services work. See `UPSTREAM.md` for provenance and changes.

# Databricks

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


Core skill for Databricks CLI, authentication, and data exploration.

## Product Skills

For specific products, use dedicated skills:
- **databricks-jobs** - Lakeflow Jobs development and deployment
- **databricks-pipelines** - Lakeflow Spark Declarative Pipelines (batch and streaming data pipelines)
- **databricks-serverless** - Compute choice for jobs and pipelines (serverless, performance mode, classic fallback)
- **databricks-apps** - Full-stack TypeScript app development and deployment
- **databricks-lakebase** - Lakebase Postgres Autoscaling project management
- **databricks-model-serving** - Model Serving endpoint management and inference

For **data discovery, exploration, and query generation** — finding tables,
answering natural-language questions about the data, or generating SQL — use
**databricks-data-discovery** (it asks Genie One first, then falls back to manual
exploration). If it isn't installed, use the AI-tool commands below and
[Manual Data Exploration](manual-data-exploration.md).

## Live operation prerequisites and target selection

These prerequisites apply when live platform work is requested. Static repository
assessment does not require a CLI, login or workspace access.

1. Inspect the project-selected CLI or SDK and the exact operation's support.
   Use its version/help and current official documentation. If a required capability
   is missing, report the limitation and the smallest justified setup change; use
   [CLI Installation](databricks-cli-install.md) only for authorized setup work.
2. Preserve working authentication and the workspace/profile already selected in
   the task or project. Use explicit per-command targeting for live actions. Do not
   create, rename or switch profiles as a side effect of review.
3. If the target is genuinely unresolved, inspect available profile names/hosts
   without exposing credentials and ask only for the missing target. If credentials
   are unavailable, retain static findings and record live checks as not run.
4. Use [CLI Authentication](databricks-cli-auth.md) for an actual authentication
   task. Prefer the project's supported identity flow; do not replace an existing
   provider solely because an example uses OAuth or a token.

## Claude Code - IMPORTANT

Each Bash command runs in a **separate shell session**.

```bash
# WORKS: --profile flag
databricks apps list --profile my-workspace

# WORKS: chained with &&
export DATABRICKS_CONFIG_PROFILE=my-workspace && databricks apps list

# DOES NOT WORK: separate commands
export DATABRICKS_CONFIG_PROFILE=my-workspace
databricks apps list  # profile not set!
```

## Data Exploration — Use AI Tools

**Use these instead of manually navigating catalogs/schemas/tables:**

```bash
# discover table structure (columns, types, sample data, stats)
databricks experimental aitools tools discover-schema catalog.schema.table --profile <PROFILE>

# run ad-hoc SQL queries
databricks experimental aitools tools query "SELECT * FROM table LIMIT 10" --profile <PROFILE>

# find the default warehouse
databricks experimental aitools tools get-default-warehouse --profile <PROFILE>
```

**Names are literal.** Use catalog/schema/table names exactly as given — never change a
hyphen to an underscore or otherwise normalize them. In SQL, backtick-quote any name part
with special characters (e.g. `` `my-catalog`.schema.table ``); unquoted hyphens cause a
parse error.

These commands are first-class for running known SQL and profiling — Genie isn't
required for that. For natural-language data questions, locating data you can't
pin down, or generating a query from a question, prefer the `databricks-data-discovery`
skill (above) if it's installed. See [Manual Data Exploration](manual-data-exploration.md) for the
full command surface, quoting rules, and troubleshooting.

## Quick Reference

**⚠️ CRITICAL: Some commands use positional arguments, not flags**

```bash
# current user
databricks current-user me --profile <PROFILE>

# list resources
databricks apps list --profile <PROFILE>
databricks jobs list --profile <PROFILE>
databricks clusters list --profile <PROFILE>
databricks warehouses list --profile <PROFILE>
databricks pipelines list --profile <PROFILE>
databricks serving-endpoints list --profile <PROFILE>

# ⚠️ Unity Catalog — POSITIONAL arguments (NOT flags!)
databricks catalogs list --profile <PROFILE>

# ✅ CORRECT: positional args
databricks schemas list <CATALOG> --profile <PROFILE>
databricks tables list <CATALOG> <SCHEMA> --profile <PROFILE>
databricks tables get <CATALOG>.<SCHEMA>.<TABLE> --profile <PROFILE>

# ❌ WRONG: these flags/commands DON'T EXIST
# databricks schemas list --catalog-name <CATALOG>    ← WILL FAIL
# databricks tables list --catalog <CATALOG>           ← WILL FAIL
# databricks sql-warehouses list                       ← doesn't exist, use `warehouses list`
# databricks execute-statement                         ← doesn't exist, use `experimental aitools tools query`
# databricks sql execute                               ← doesn't exist, use `experimental aitools tools query`

# When in doubt, check help:
# databricks schemas list --help

# get details
databricks apps get <NAME> --profile <PROFILE>
databricks jobs get --job-id <ID> --profile <PROFILE>
databricks clusters get --cluster-id <ID> --profile <PROFILE>

# bundles
databricks bundle init --profile <PROFILE>
databricks bundle validate --profile <PROFILE>
databricks bundle deploy -t <TARGET> --profile <PROFILE>
databricks bundle run <RESOURCE> -t <TARGET> --profile <PROFILE>
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `cannot configure default credentials` | Check the already selected context; request missing authentication only for authorized live work |
| `configuration does not support OAuth tokens` | Verify the exact command and selected provider support in current docs before proposing an identity change. See [CLI Authentication](databricks-cli-auth.md). |
| `PERMISSION_DENIED` | Check workspace/UC permissions |
| `RESOURCE_DOES_NOT_EXIST` | Verify resource name/id and profile |

## Required Reading by Task

| Task | READ BEFORE proceeding |
|------|------------------------|
| First time setup | [CLI Installation](databricks-cli-install.md) |
| Auth issues / new workspace | [CLI Authentication](databricks-cli-auth.md) |
| Exploring tables/schemas | [Manual Data Exploration](manual-data-exploration.md) (or `databricks-data-discovery` if installed) |
| Deploying jobs/pipelines | Use `/databricks-dabs` |

## Reference Guides

- [CLI Installation](databricks-cli-install.md)
- [CLI Authentication](databricks-cli-auth.md)
- [Manual Data Exploration](manual-data-exploration.md)
