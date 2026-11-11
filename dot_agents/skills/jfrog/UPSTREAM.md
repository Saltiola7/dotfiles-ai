# Upstream provenance and local adaptation

- Upstream: https://github.com/jfrog/jfrog-skills
- Commit: `e555af53c3f5ead14fcafb009380e76d3ddf17d1` (v0.44.0)
- Original root: `skills/jfrog`
- License: Apache-2.0; exact repository notice retained as `LICENSE.upstream`.

The complete upstream root and supporting resources are retained. Original blob
identities, hashes/modes, packaged hashes/installed modes and reversible patches
are recorded by the shared DBSCTR specialist source inventory. Source execution
bits and installed readable-resource modes are distinct; review helpers before
invoking their selected interpreter.

## Adaptations

- Replaced broad discovery keywords with concrete JFrog tasks and a compact active entrypoint; moved the complete upstream workflow body to `references/upstream-workflow.md`, rebasing relative Markdown links and adapting unsafe setup/runtime sections.
- Added `references/local-ownership.md`: existing installer, client configuration, authentication, task authority and selected QA owners override upstream automatic probes, telemetry, login, install/upgrade and global MCP governance.
- Reworked reachable CLI-install and login references to retain useful setup mechanics without floating shell installers, default-server changes, compulsory browser login, blanket escalation or unconditional upgrade offers. Credential exports are treated as sensitive rather than decoded for discovery, including the OneModel target-resolution example; schema-cache keys reject path-bearing identifiers and network calls retain explicit server IDs.
- Kept all original scripts byte-for-byte and source modes intact. They remain inert resources; environment/version helpers can contact networks/write state, and login helpers issue sessions/exchange tokens/write credentials. Their presence is not execution or permission.
- Preserved same-server targeting, endpoint discovery, bounded pagination, private output handling and conditional domain guidance. Denied access does not justify switching transport/credentials. Updated the index for local ownership and extended workflow references.

Installation supplies portable guidance/resources only. It neither executes
helpers nor establishes CLI availability, native discovery, authentication, MCP
connectivity or verified live platform behavior. Existing native/project owners
and current task authority remain authoritative.

The original empty `assets/.gitkeep` VCS placeholder is retained in source and
provenance as `source_only_files`; native chezmoi omits it. Every workflow, helper,
license and referenced runtime resource remains in the installed inventory.
