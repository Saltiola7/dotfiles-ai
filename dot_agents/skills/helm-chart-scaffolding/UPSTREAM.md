# Upstream Attribution and Local Adaptation

- Upstream repository: https://github.com/wshobson/agents
- Immutable commit: `7e2fb559cf4b824b27f1fec49fe88f7511066d26`
- Selected skill root: `plugins/kubernetes-operations/skills/helm-chart-scaffolding`
- License: MIT; unchanged upstream notice in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [selected bundle](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/kubernetes-operations/skills/helm-chart-scaffolding)

## Local changes

Kept every original resource and executable mode. Replaced the helper with bounded local lint/render checks and truthful exit status, preserving paths with spaces. Standalone library charts use the explicit `--lint-only` path, which reports consumer rendering as unverified; rendering library helpers requires a selected application consumer chart. Qualified chart/dependency/hooks/cluster examples, removed sample passwords, scoped live operations and documented rendering limits. Preserved library-chart named helpers in `templates/_*` and required application-consumer rendering evidence for helper behavior. Corrected hook timing after rendering, CRD ordering and integer-string weights; qualified migration hooks with an explicit bounded project contract.

Every selected upstream skill-root resource remains at its original relative path.
`LICENSE.upstream` is copied unchanged from repository-root `LICENSE`; this
attribution file and any named focused references are local additions. Plugin
manifests, unrelated siblings and provider hooks are not installed. No downloaded
helper executes during acquisition or installation. Upstream attribution does not
imply upstream endorsement of these changes.

The managed source inventory at
`dbsctr/references/specialist-sources/sources.lock.json` records original Git blobs
and SHA-256 hashes, complete adapted file hashes, executable modes and reversible
patches. Updates require deliberate review of the full bundle and its adaptations;
ordinary skill loading uses installed bytes rather than fetching moving content.
