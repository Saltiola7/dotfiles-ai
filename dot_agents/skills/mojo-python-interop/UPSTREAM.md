# Upstream attribution and local adaptation

- Upstream repository: https://github.com/modular/skills
- Immutable commit: `1b2cc565ca7e0a8b66d96b4ee78fdfb7ec443a88`
- Selected skill root: `mojo-python-interop`
- Immutable source: [mojo-python-interop](https://github.com/modular/skills/tree/1b2cc565ca7e0a8b66d96b4ee78fdfb7ec443a88/mojo-python-interop)
- Original attribution: Modular and the contributors named in upstream notices.
- License: the exact composite upstream notice is retained in [LICENSE.upstream](LICENSE.upstream).

The upstream repository's `LICENSE` contains Apache License 2.0 with LLVM
Exceptions and a retained legacy University of Illinois/NCSA notice. It must not
be simplified to an unqualified Apache-2.0 label or have its exception/legacy
sections removed. This records the supplied composite notice, not a conclusion
that every legacy term applies to every file. Local adaptations to this upstream
material remain subject to its applicable terms; attribution does not imply
upstream endorsement.

## Local changes

Moved the complete interop example body into `references/interop-patterns.md` for selective loading. Bound conversions, extension builders and signatures to the selected SDK and Python ABI. Replaced Python source concatenation for sorting with `operator.itemgetter(field)`, keeping variable values as data. Marked evaluation/import as execution and importer caching/compilation as side effects. Added ownership, lifetime, exception and target evidence obligations without claiming examples compile.

Every original skill-root file path remains present. The original repository-root
`LICENSE` is copied byte-for-byte as `LICENSE.upstream`; original file modes are
retained. Added references provide progressive disclosure and this attribution
file is local. No sibling MAX lifecycle bundle, installer or downloaded executable
is included. Guidance availability is not installation, execution, compilation,
benchmark or target-support evidence.

Original Git blob and SHA-256 identities, complete packaged file sets/modes and
reversible original-to-local patches are maintained in
`dbsctr/references/specialist-sources/sources.lock.json` and its adjacent patch
resources. Updates require deliberate review of the full pinned bundle and local
adaptations. Ordinary selection uses installed resources without fetching upstream.
