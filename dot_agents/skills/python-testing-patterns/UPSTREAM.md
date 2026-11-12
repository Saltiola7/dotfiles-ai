# Upstream Attribution and Local Adaptation

- Upstream repository: https://github.com/wshobson/agents
- Immutable commit: `7e2fb559cf4b824b27f1fec49fe88f7511066d26`
- Selected skill root: `plugins/python-development/skills/python-testing-patterns`
- Original author/attribution: Seth Hobson (Copyright (c) 2024)
- License: MIT; complete unchanged upstream license in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [python-testing-patterns](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/python-development/skills/python-testing-patterns)

This adapted directory remains licensed under MIT. The bundled license retains
the upstream copyright and warranty disclaimer. Upstream attribution does not
imply endorsement of this adaptation.

## Local changes

Preserved the complete upstream skill resource tree. Bounded runner, dependency, workflow and coverage examples to project policy; retained QA/lifecycle ownership. Corrected yield/async fixture cleanup, deterministic environment tests, mocked request timeouts, selected-engine integration limits, multiset property assertions and a relative resource link. Replaced obsolete workflow-action recipes with project-owned CI invocation and removed blanket coverage exclusions. Added managed provenance and generated discovery metadata.

Every original skill-root file is retained. `LICENSE.upstream` is copied unchanged
from the repository-root `LICENSE`; this attribution file and `agents/openai.yaml`
are local additions. Sibling plugin manifests, agents, hooks, installers and
external evaluation runners are outside the selected skill root and are not
installed. Their documentation does not prove local execution or effectiveness.

Original SHA-256 hashes, Git blob identities and modes, packaged hashes and modes,
and reversible per-file patches are recorded in the managed source inventory at
`dbsctr/references/python-data-sources/python/sources.lock.json`. Updates require
review of the complete pinned bundle and its adaptations. Ordinary skill loading
uses installed bytes without fetching upstream content.
