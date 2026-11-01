# Upstream attribution and local adaptation

- Upstream repository: https://github.com/polars-inc/skills
- Immutable commit: `b102cc948ba9a058f075e9794861ae5c56f31f6d`
- Selected skill root: `skills/polars`
- Original author: Polars; original license copyright (c) 2026 Robin
- License: MIT; complete unchanged notice in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [selected bundle](https://github.com/polars-inc/skills/tree/b102cc948ba9a058f075e9794861ae5c56f31f6d/skills/polars)

This adapted bundle remains MIT licensed. Attribution does not imply upstream
endorsement. Every original skill-root file is retained; `LICENSE.upstream` is
copied unchanged from the repository-root `LICENSE`. This attribution file and
generated `agents/openai.yaml` are local additions. Plugin manifests, hooks,
installers and the optional Polars MCP server are outside the selected bundle.

## Local changes

Scoped discovery to actual Polars work or an explicit migration, preserving the
project's engine, dependency and runtime choices. Qualified lazy/eager boundaries,
version-sensitive APIs and schema-resolution I/O. Preserved all six references;
corrected bounded pandas bins, interpolation-limit and monetary-rounding guidance,
anti-join versus SQL NOT IN null semantics, accepted iterable argument forms,
top-rank ties, missing calendar periods and zero denominators. Corrected the
filter-pushdown example and made documentation lookups tool/version independent.

Complete original paths, SHA-256 hashes, Git blobs and modes, packaged hashes and
zero-fuzz reversible adaptations are recorded in
`dbsctr/references/python-expansion-sources/data-testing/sources.lock.json`.
Updating requires deliberate review of the full pinned bundle and adaptations.
Ordinary loading uses the installed bytes without fetching upstream instructions.
Examples are guidance, not evidence of executing a dataframe engine, processing
user data or proving pandas/Polars equivalence on the project's installed versions.
