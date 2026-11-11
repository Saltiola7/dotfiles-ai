# Upstream attribution and local adaptation

- Auditor repository: https://github.com/TarkinLarson/asvs-auditor
- Immutable auditor commit: `2ca0ad8e1367060080fccf3028690d1292358069`
- Selected root: `skills/agent-asvs` (19 original files: `SKILL.md`, reference
  attribution README and all 17 requirement chapters)
- Reviewed source archive SHA-256:
  `4efc881e6420bd45170d932ca22a31c8bb77f8c9747e435bf52e5395e754e472`
- Original auditor copyright: © 2026 TarkinLarson; unchanged MIT terms in
  [LICENSE.upstream](LICENSE.upstream)
- Requirement text: OWASP Application Security Verification Standard 5.0.0,
  © OWASP Foundation; CC-BY-SA 4.0 terms retained in
  [LICENSE.asvs](LICENSE.asvs) and attribution in
  [reference/README.md](reference/README.md)
- Official ASVS release tag: `v5.0.0_release`, resolving to immutable commit
  `5cf9b032440be53ce345ab3c130fda46ba1ce7a2`
- [Immutable official ASVS source](https://github.com/OWASP/ASVS/tree/5cf9b032440be53ce345ab3c130fda46ba1ce7a2/5.0/en)

The upstream auditor labels its reference source `v5.0.0`, but that tag was not
present in official Git refs during review. The official release tag above was
resolved independently. All 345 bundled requirement IDs, levels and texts match
that release exactly (70 L1, 183 L2, 92 L3). Local chapter changes correct the
source URL and mark that correction; requirement rows remain unchanged.

The two license scopes remain separate. CC-BY-SA applies to the ASVS-derived
reference chapter content and its adaptations. MIT applies to the auditor's
methodology and the local non-ASVS review guidance. Attribution does not imply
endorsement by TarkinLarson or OWASP.

## Local changes

Replaced the 51,514-byte interactive root with a scoped entrypoint and concise
lazy workflow. Removed persona rhetoric, provider-specific tool grants, blanket
full-audit defaults and large duplicate examples. Retained exact requirement
resources and their original relative paths; corrected installed attribution and
license links. Added this provenance record and the full applicable ASVS license.

The adapted workflow preserves attack-surface enumeration, taint tracing,
control/absence evidence, external-control uncertainty and requirement coverage.
It follows the operator's activation policy and active DBSCTR router, retains one
coordinator, and distinguishes sampled, unknown and unchecked evidence from
verification. It groups one defect per root cause with multiple supported ASVS
mappings, preserves project risk authority, treats example-file credentials as
candidates, requires redaction, and separates implementation preferences from
literal ASVS obligations. ASVS does not exclude otherwise valid security issues.
Missing chapters produce a mapping gap instead of a network fallback.

The upstream CI variant, report schema, provider launcher, smoke runner,
reference generator and hooks are not installed. No scanner, MCP, provider,
credential setup, live probe or production audit is part of this adaptation.
The distribution's security-toolkit inventory records exact original and
packaged hashes, selected paths and reversible modifications. Updating requires
review of the full pinned bundle, adaptations and licensing. Static reference
and packaging checks do not establish model recall, compliance or finding truth.
