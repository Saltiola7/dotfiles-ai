# Upstream attribution and local adaptation

- Upstream repository: https://github.com/modular/skills
- Immutable commit: `1b2cc565ca7e0a8b66d96b4ee78fdfb7ec443a88`
- Selected skill root: `mojo-gpu-fundamentals`
- Immutable source: [mojo-gpu-fundamentals](https://github.com/modular/skills/tree/1b2cc565ca7e0a8b66d96b4ee78fdfb7ec443a88/mojo-gpu-fundamentals)
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

Moved the complete GPU example body into `references/gpu-patterns.md` for selective loading. Conditioned APIs and hardware facts on the selected SDK/runtime/device. Replaced the blanket compile-time-dimensions rule with actual API requirements and supported dynamic shapes. Scoped the optional MAX benchmark example to already selected compatible dependencies and actual synchronized correctness/performance evidence; no unrelated MAX installation or hardware-support claim follows. Corrected the shared-memory reduction example to atomically accumulate the completed tree root once from thread zero, instead of warp-summing overlapping partial reductions. Documented the fixed launch/input, output initialization, integer range and barrier assumptions. The local arithmetic repro uses only a CPU integer model and does not establish Mojo compilation or GPU execution.

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
