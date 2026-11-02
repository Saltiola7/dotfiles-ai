# Upstream provenance

- Source: https://github.com/jfrog/jfrog-skills
- Commit: `e555af53c3f5ead14fcafb009380e76d3ddf17d1`
- Upstream root: `skills/jfrog-init`
- License: Apache-2.0; exact repository notice preserved as `LICENSE.upstream`.
- Full original resource paths and helper dependency closure are retained.
- Original entrypoint moves into an adapted complete workflow at
  `references/upstream-workflow.md`; relative Markdown links are rebased or
  redirected to the current active owner. The compact `SKILL.md` loads detail
  only for the actual operation.

## Reviewed adaptations

The original Claude-specific `disable-model-invocation`/tool grants become a
portable compact entrypoint plus native `agents/openai.yaml` manual invocation
policy. Setup workflow and all active operational references are adapted to
capability-specific readiness and existing native owners. Runtime/CLI bootstrap,
automatic OAuth, URL substitution, setup-state writes, marketplace/credential
migration, blanket prompt choreography and exit masking are removed from active
procedures. Legacy installers, config/auth detectors, batch helpers, credential
header helper and all transitive library resource paths remain complete.
Reviewed code/comment adaptations are recorded as reversible patches; resources
stay inert until actual task-specific effect/version review. OpenCode V1 and
inferred auth-store assumptions are explicitly unqualified for V2; Codex homes
and managed projectors retain their native ownership. Descriptive installer and
project-matching internals are retained with current interpretation boundaries.

The shared specialist source inventory records original Git blobs, hashes and
modes, packaged bytes, installed modes and reversible patches, including new
references and invocation metadata. Source executable bits do not imply installed
execution authority; invoke reviewed resources through the selected interpreter.

Updating this bundle requires review of the complete pinned tree, helper side
effects, client-version assumptions and all local patches. Installation proves
only source/file delivery; CLI compatibility, native discovery, authentication,
connected MCP tools and platform behavior need separate actual evidence.


### Credential-cache repair

The optional cross-invocation project enumeration cache is disabled: its former
SHA-256 fingerprint persisted a fast verifier derived from tokens/passwords.
Compatibility exports now always miss/no-op without inspecting credentials or
legacy files. The existing caller performs live enumeration for the selected
identity. Discovery comments, project-matching guidance and three atomic-writer
cross-references are updated. The helper paths and call interfaces remain; these
reviewed code/comment adaptations are retained as reversible patches, not an
unchanged-helper claim. Synthetic regression tests cover no retained state,
ignored untouched legacy cache and zero credential-property access. Native
CodeQL must qualify the repaired head without suppressions or alert dismissal.
