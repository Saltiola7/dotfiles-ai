# Upstream attribution and local adaptation

- Upstream repository: https://github.com/trailofbits/skills
- Immutable commit: `2be6433b39e009cd2b6fd3be1895f6b1faa5af9a`
- Selected skill root: `plugins/testing-handbook-skills/skills/atheris`
- Original author/attribution: Trail of Bits
- License: CC-BY-SA-4.0; complete unchanged terms in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [selected bundle](https://github.com/trailofbits/skills/tree/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a/plugins/testing-handbook-skills/skills/atheris)

This adapted directory, including local changes to upstream material, remains
licensed under CC-BY-SA-4.0. The complete bundled license retains the warranty
disclaimer and applicable terms. Attribution does not imply upstream endorsement.
Every original skill-root file is retained, including the original icon asset;
`LICENSE.upstream` comes unchanged from the repository-root `LICENSE`. This
attribution is local. Generated UI metadata preserves the upstream icons/brand.
Sibling plugin manifests, hooks, installation scripts and unrelated skills are
outside the selected bundle and are not installed.

## Local changes

Scoped discovery to selected coverage-guided fuzz work. Preserved sanitizer,
instrumentation, structured-input and native-extension guidance while qualifying
execution authority, fixture/corpus/artifact ownership and finite resource budgets.
Replaced the stale blanket Python floor with selected-release/runtime checks;
the pinned official Google README at
`e36da74cf42b5834c4e31d7cabb58d796695d29f` distinguishes current-source support
from older PyPI releases. Qualified Linux preload versus macOS and historical
CPython examples, removed the hardcoded Python 3.11 preload path and automatic
OOM/leak suppression, required an explicit container Atheris version, and used
distribution metadata for version checks. Narrowed documented input rejections,
made the HTTP example parse actual header bytes, retained unexpected exceptions,
and clarified corpus draw-order/surrogate compatibility. Optional sibling guidance
uses immutable external links rather than assumed installed dependencies.

Complete original paths, SHA-256 hashes, Git blobs and modes, packaged hashes and
zero-fuzz reversible adaptations are recorded in
`dbsctr/references/python-expansion-sources/data-testing/sources.lock.json`.
Updating requires review of the full pinned bundle and adaptations. Ordinary
loading uses installed bytes without fetching upstream instructions. Installing
these resources did not install Atheris, rebuild an extension, build a container
or run a fuzz campaign; static/offline checks cannot establish native coverage,
sanitizer loading or fuzz effectiveness.
