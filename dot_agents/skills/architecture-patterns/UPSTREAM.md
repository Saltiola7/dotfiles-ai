# Upstream attribution and local adaptation

- Upstream repository: https://github.com/wshobson/agents
- Immutable commit: `7e2fb559cf4b824b27f1fec49fe88f7511066d26`
- Selected skill root: `plugins/backend-development/skills/architecture-patterns`
- Original author: Seth Hobson, Copyright (c) 2024
- License: MIT; unchanged full notice in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [selected bundle](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/backend-development/skills/architecture-patterns)

This adapted bundle remains MIT licensed. Upstream attribution does not imply
endorsement. Every original skill-root file is retained; `LICENSE.upstream`
comes unchanged from the repository-root license. This attribution and
`agents/openai.yaml` are local additions. Plugin manifests, agents, hooks,
installers and external workflow runners are outside the selected skill root.

## Local changes

Preserved the complete selected resource tree and scoped patterns to demonstrated architectural costs, project policy and compatible incremental choices. Kept modular monolith and simpler interface alternatives; made layers, repositories, ORM mapping, eventing and tool execution conditional. Moved fake tests on demand with explicit integration limits, corrected the borrowed-pool factory and quantity-aware Money totals with explicit unit rounding, populated required order-submission event fields from actual order values, replaced the blocking/global Stripe example with an injected asynchronous boundary, and made outbox encoding/commit/event ownership explicit. Added original attribution, generated UI metadata and immutable provenance.

The exact originals, Git blob identities, source/installed modes, packaged hashes
and reversible per-file adaptations are recorded in
`dbsctr/references/architecture-sources/sources.lock.json`. All files are plain
non-executable resources. Updating this bundle requires review of its complete
resources and patches; ordinary loading uses the reviewed installed bytes,
not moving upstream instructions. Code snippets are illustrative fragments,
not proof that an integration or architecture contract passed.
