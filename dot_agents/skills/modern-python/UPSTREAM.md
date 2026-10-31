# Upstream Attribution and Local Adaptation

- Upstream repository: https://github.com/trailofbits/skills
- Immutable commit: `2be6433b39e009cd2b6fd3be1895f6b1faa5af9a`
- Selected skill root: `plugins/modern-python/skills/modern-python`
- Original author/attribution: Trail of Bits; upstream credits William Tan and trailofbits/cookiecutter-python
- License: CC-BY-SA-4.0; complete upstream license in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [modern-python](https://github.com/trailofbits/skills/tree/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a/plugins/modern-python/skills/modern-python)

This adapted directory, including local changes to upstream material, remains licensed under CC-BY-SA-4.0. The bundled license includes the warranty disclaimer and applicable terms.

## Local changes

Preserved the complete upstream skill resource tree. Made tool, dependency, runtime, layout, lock, coverage, hook and migration recipes conditional on project policy and current authorization in the entrypoint and supporting references. Removed scheduled-CI removal and shared-cache cleanup prescriptions; preserved dependency constraints and active consumers. Clarified bounded security setup and optional update automation. Added managed integration boundaries, license metadata and attribution.

Every original skill-root file is retained. `LICENSE.upstream` is copied unchanged
from the repository-root `LICENSE`; this attribution file is added locally.
Sibling plugin manifests, hooks/shims and external evaluation runners are not part
of the selected skill root and are not installed. Their upstream documentation is
not evidence of local installation, execution or effectiveness. Upstream attribution
does not imply upstream endorsement of this adaptation.

Original SHA-256 hashes and Git blob identities, packaged hashes and reversible
patches are recorded in the managed source inventory at
`dbsctr/references/python-specialists/sources.lock.json`. Updates require deliberate
review of the complete pinned bundle and its adaptations; ordinary skill loading
uses the installed bytes without fetching upstream content.
