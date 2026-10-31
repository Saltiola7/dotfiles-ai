# Upstream attribution and local adaptation

- Upstream repository: https://github.com/wshobson/agents
- Immutable commit: `7e2fb559cf4b824b27f1fec49fe88f7511066d26`
- Selected skill root: `plugins/shell-scripting/skills/bats-testing-patterns`
- Upstream attribution: Seth Hobson
- License: MIT; the complete unchanged notice is in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [bats-testing-patterns](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/shell-scripting/skills/bats-testing-patterns)

## Local adaptation

Made Bats selection conditional on project policy. Consolidated examples into the existing supporting reference; corrected status assertions, temporary fixtures, undefined helper use, child-status aggregation, permission-test limits, platform differences and current CLI options. Replaced automatic installation/stale CI recipes with existing project authority and explicit unavailable-evidence semantics.

Every original selected skill-root file remains present. The focused entrypoint
and existing `references/details.md` retain the relevant methods with corrected,
project-conditional examples. `LICENSE.upstream` is copied verbatim from the
repository-root `LICENSE`; this attribution file is added locally. The bundle
remains under MIT with its retained upstream copyright and warranty notice.

Sibling plugin manifests, hooks, external evaluation runners and automatic tool
installation are outside the selected skill root and are not installed. Loading
this bundle supplies guidance under existing task authorization and project
policy; it does not establish runtime execution, validation success or deployment.

The managed source inventory at
`dbsctr/references/specialist-sources/sources.lock.json` records original Git blobs
and SHA-256 identities, complete packaged file hashes and reversible adaptation
patches. Maintainers review the full bundle and its supporting resources before
changing the pin. Ordinary skill loading uses installed reviewed bytes rather
than fetching moving upstream content.
