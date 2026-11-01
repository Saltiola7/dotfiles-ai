# Upstream attribution and local adaptation

- Upstream repository: https://github.com/pulumi/agent-skills
- Immutable commit: `82f222a529a499e8005a820000148cc5e28c934c`
- Selected skill root: `pulumi/skills/pulumi-component`
- License: Apache-2.0; the complete unchanged repository notice is in
  [LICENSE.upstream](LICENSE.upstream).
- Immutable source: [pulumi-component](https://github.com/pulumi/agent-skills/tree/82f222a529a499e8005a820000148cc5e28c934c/pulumi/skills/pulumi-component)

## Local adaptation

This bundle contains locally modified instructions derived from that source.

Compact discovery/entrypoint with conditional interface/packaging detail. Adapted
the full component method and examples in `references/details.md`: corrected type
tokens versus URNs, known topology switches versus Output objects, naming/provider
inheritance, secret propagation, registration completion and schema-qualified
cross-language types. Qualified version-sensitive packaging/host examples and
separate installation/code generation/publication authority; removed automatic CI
publication and unselected-skill requirements.

Every original selected skill-root path remains present. The original top-level
`version` field is normalized out of `SKILL.md`; immutable provenance above owns
that identity. Original `agents/openai.yaml` and `use_cases.yaml` remain byte-for-byte
intact. Native implicit invocation remains enabled by default. Use-case queries
are selection examples, not permission to execute their requested operations or
proof of routing behavior. The original repository license is copied verbatim;
no additional or combined upstream copyright/license notice is invented.

The shared managed specialist-source inventory records original Git blobs,
SHA-256 identities, modes, complete packaged hashes and reversible adaptations.
Maintainers review the complete bundle before changing the pin. Ordinary skill use
reads installed reviewed resources; it does not fetch moving upstream content.

Sibling plugins/manifests, broad routers, operational credentials, helpers and
unselected skills are outside this selected root. Loading this bundle supplies
guidance under existing task and project authority; it proves neither tool/runtime
availability, actual provider validation nor deployment success.
