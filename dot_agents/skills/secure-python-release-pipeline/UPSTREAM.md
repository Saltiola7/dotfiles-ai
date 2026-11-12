# Upstream attribution and local adaptation

- Upstream repository: https://github.com/tiran/agent-skills
- Immutable commit: `0c51c24122b33afed31fd8d50534e089534f77a7`
- Selected skill root: `skills/secure-python-release-pipeline`
- Original author/maintainer: Christian Heimes and upstream contributors
- License: Apache-2.0; unchanged full text in [LICENSE.upstream](LICENSE.upstream)
- Upstream maturity: **Experimental**, retained in the adapted guidance
- Immutable source: [selected bundle](https://github.com/tiran/agent-skills/tree/0c51c24122b33afed31fd8d50534e089534f77a7/skills/secure-python-release-pipeline)

This adapted bundle remains Apache-2.0 licensed. Attribution does not imply
upstream endorsement or qualification. Every selected skill-root file is retained.
`GUARDRAILS.md` is a reviewed local adaptation of upstream `skills/GUARDRAILS.md`;
`LICENSE.upstream` is an exact copy of the repository-root `LICENSE`.
This file and `agents/openai.yaml` are local additions. Modified original resources
carry a local-adaptation notice. Unselected sibling skills and the grounding list
are optional immutable external references, not installed dependencies.

## Local changes

Preserved every selected root resource and mapped shared guardrails into the bundle. Retained Experimental maturity and Apache notices. Scoped GitHub Actions release guidance to the existing project, task and QA/Release owners. Reconciled mandatory uv, versioning, updater, cooldown, cache, approval and CI conventions with project authority. Added build-from-sdist and clean installed-artifact evidence, clarified metadata/attestation limits, scoped publication permissions, corrected cache trust and release-cancellation claims, and qualified workflow examples, tool setup and sdist selection. Generated UI metadata through the original Skill Creator helper.

Exact original file paths, SHA-256 hashes, Git blob identities and modes,
complete adapted file hashes/modes and zero-fuzz reversible patches are recorded in
[the runtime source inventory](../dbsctr/references/python-expansion-sources/runtime/sources.lock.json).
The `upstream_paths` mapping explicitly identifies root-license and shared-resource
origins for each original bundle key. All bundled files are non-executable resources.
Review the complete bundle and patches when updating; loading uses reviewed local
bytes, not moving upstream instructions. Illustrative snippets and source-only
checks do not establish a real package build, live runtime or publication result.
