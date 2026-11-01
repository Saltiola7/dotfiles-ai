# Upstream attribution and local adaptation

- Upstream repository: https://github.com/duckdb/duckdb-skills
- Immutable commit: `7feda8e01e22bc0886c86123f3884947e36d8c69`
- Selected skill root: `skills/attach-db`
- License: MIT; unchanged complete notice in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [attach-db](https://github.com/duckdb/duckdb-skills/tree/7feda8e01e22bc0886c86123f3884947e36d8c69/skills/attach-db)

## Local adaptation

Namespaced the entrypoint; preserved optional upstream session conventions in a linked reference. Made attachment read-only when sufficient, persistence explicit, existing connection/state ownership authoritative and metadata scoped; removed automatic installs, file creation, global state search and counts.

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
