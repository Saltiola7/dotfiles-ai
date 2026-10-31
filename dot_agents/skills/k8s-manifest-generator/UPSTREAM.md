# Upstream Attribution and Local Adaptation

- Upstream repository: https://github.com/wshobson/agents
- Immutable commit: `7e2fb559cf4b824b27f1fec49fe88f7511066d26`
- Selected skill root: `plugins/kubernetes-operations/skills/k8s-manifest-generator`
- License: MIT; unchanged upstream notice in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [selected bundle](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/kubernetes-operations/skills/k8s-manifest-generator)

## Local changes

Kept the complete selected resource tree while making policy/target/validation boundaries explicit. Replaced generic long field tutorials with scoped Deployment/Service design references, qualified resource/probe/provider defaults, scoped live examples, protected secret handling and made unselected sibling guidance optional. Corrected RWO to single-node writable mounting (which can include multiple same-node Pods), distinguished supported RWOP single-Pod exclusion and retained application/storage concurrency and recovery contracts.

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
