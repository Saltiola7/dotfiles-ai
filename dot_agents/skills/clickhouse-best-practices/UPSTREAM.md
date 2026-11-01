# Upstream attribution and local adaptation

- Upstream repository: https://github.com/ClickHouse/agent-skills
- Immutable commit: `69a8354b05b5942e5cea77b6c87be7788303fc18`
- Selected skill root: `skills/clickhouse-best-practices`
- License: Apache-2.0; unchanged complete notice in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [clickhouse-best-practices](https://github.com/ClickHouse/agent-skills/tree/69a8354b05b5942e5cea77b6c87be7788303fc18/skills/clickhouse-best-practices)

## Local adaptation

Preserved complete root including all31rules, metadata, template and README. Adapted static/live access and connection ownership; removed installers, credential reset/discovery/inline passwords and fixed model selection. Corrected restricted ORDERBY changes, index/pruning absolutes, null/precision semantics, unsafe format API, optimizer pushdown assumptions and partition examples. Added workload/version qualifications and rebuilt compiled AGENTS from locally adapted rules.

Every original selected skill-root file remains present. Added portable UI
metadata, this attribution and any on-demand references required by the adapted
workflow. Source-root LICENSE is retained verbatim as LICENSE.upstream.
Source-root [NOTICE.upstream](NOTICE.upstream) is also retained verbatim.

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
