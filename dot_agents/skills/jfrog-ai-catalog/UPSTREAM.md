# Upstream provenance

- Source: https://github.com/jfrog/jfrog-skills
- Commit: `e555af53c3f5ead14fcafb009380e76d3ddf17d1`
- Upstream root: `skills/jfrog-ai-catalog`
- License: Apache-2.0; exact repository notice preserved as `LICENSE.upstream`.
- Full original resource paths and helper dependency closure are retained.
- Original entrypoint moves into an adapted complete workflow at
  `references/upstream-workflow.md`; relative Markdown links are rebased or
  redirected to the current active owner. The compact `SKILL.md` loads detail
  only for the actual operation.

## Reviewed adaptations

The root trigger is restricted to a selected JFrog catalog; generic skill or
plugin discovery does not activate governance. The complete workflow and all
operation references retain discovery, versions, policy, installation/update,
inventory/removal and publication capabilities while preserving native/managed
source owners, exact target/version and existing concrete task consent. Automatic
repository provisioning, server/project-wide fallback, default scan bypass,
suppressed security results, missing-attestation overrides and recursive shared
removal are replaced by project-selected provenance/scan gates and honest
partial-state reporting. Agent Guard remains a separate reviewed runtime; no
floating npm fetch, login, plugin or hook installation occurs on skill apply.
The original policy script and every local resource remain complete and inert.

The shared specialist source inventory records original Git blobs, hashes and
modes, packaged bytes, installed modes and reversible patches, including new
references and invocation metadata. Source executable bits do not imply installed
execution authority; invoke reviewed resources through the selected interpreter.

Updating this bundle requires review of the complete pinned tree, helper side
effects, client-version assumptions and all local patches. Installation proves
only source/file delivery; CLI compatibility, native discovery, authentication,
connected MCP tools and platform behavior need separate actual evidence.
