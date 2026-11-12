# Upstream attribution and local adaptation

- Upstream repository: https://github.com/duckdb/duckdb-skills
- Immutable commit: `7feda8e01e22bc0886c86123f3884947e36d8c69`
- Selected skill root: `skills/query`
- License: MIT; unchanged complete notice in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [query](https://github.com/duckdb/duckdb-skills/tree/7feda8e01e22bc0886c86123f3884947e36d8c69/skills/query)

## Local adaptation

Namespaced the entrypoint; kept Friendly SQL in a linked on-demand reference. Replaced implicit tool installation, state discovery/execution, full counts and retries with task-scoped static/live modes, existing connection ownership, semantic preservation, resource budgets and truthful execution reports.

Every original selected skill-root file remains present. Added portable UI
metadata, this attribution and any on-demand references required by the adapted
workflow. Source-root LICENSE is retained verbatim as LICENSE.upstream.

Plugin manifests, hooks, installer/build tooling and unrelated sibling skills are
outside the selected roots and are not installed. The managed bundle supplies
reviewed guidance under current task authorization; it does not execute its
examples, install tools, configure authentication or prove runtime validation.
Use one reviewed plugin or managed copy per task, preserving the selected origin.

The managed source inventory at
`dbsctr/references/python-data-sources/engines/sources.lock.json` records upstream
Git blob/mode and SHA-256 identities, complete packaged hashes/modes and
reversible adaptation patches. Updates require review of the complete bundle and
its dependencies; ordinary loading uses installed reviewed bytes, not moving
upstream downloads.
