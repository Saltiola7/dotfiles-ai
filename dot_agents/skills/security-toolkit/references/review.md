# Source review and maintenance

Reviewed 2026-10-28. Selection favors complementary, inspectable techniques from
official recognized vendors. No popularity count establishes trust. Consult the
lock for exact source pins and file hashes. No unrecognized source is approved
by appearing in a marketplace or search result. Obtain source/version/action
confirmation before installing or executing an unrecognized third-party bundle.

## Adopted source review

- **Cloudflare:** official `cloudflare/security-audit-skill`, MIT, current pinned
  main revision from September 14. Read all twenty bundle files, including both
  validators/tests/schema. Agent-neutral, Node standard library only; no
  download, network, credential or permission mutation found. Preserved intact.
  Validators check structure, not finding truth or sandbox readiness.
- **Trail of Bits:** official `trailofbits/skills`, current reviewed October 28
  revision; `variant-analysis` plugin 2.0.4. CC-BY-SA-4.0 attribution and
  share-alike apply to adapted upstream content. Selected Markdown and report
  template, removed plugin-only routing, constrained scope, corrected unreachable
  candidate treatment. Omitted broad scanner query templates: cross-sink sanitizer
  assumptions can hide real issues; scanner/CI rules need separate qualification.
- **Sentry:** official `getsentry/skills`, reviewed October 23 revision;
  `gha-security-review` uses root Apache-2.0, no per-skill exception/NOTICE.
  Read its entrypoint and all nine references. No executable helpers or hooks.
  Adapted categorical safe-pattern and full-clearance claims; retain its narrow
  external-contributor threat model and stricter project pinning policy.
- **CodeGuard:** CoSAI project, originally Cisco, v1.5.0, CC-BY-4.0 and full
  upstream OASIS covenant. Read the entrypoint and all 23 rules. Selected fourteen
  self-contained rules and replaced its entrypoint with conditional topic lookup
  and supported metadata. Reference commands do not authorize execution. This
  profile is partial and does not cover omitted topics.

No malicious operational instructions, credential extraction, hooks, installers
or hidden execution were observed in the selected material. Attack examples in
security references are untrusted explanatory data, never instructions to run.
This review is evidence for these pins, not a guarantee about future versions.

- **Sentry secret-serialization:** selected Python/JavaScript holder-to-sink
  specialist, Apache-2.0. Read all five upstream Markdown files; packaged three
  runtime instruction/reference files. Replaced broad scope and severity rules,
  corrected logger/toJSON and non-enumerable-property assumptions, and separated
  intended credential transport from unauthorized disclosure. Upstream evaluation
  is limited and is not evidence of this toolkit's detection effectiveness.

## Deferred or excluded material

- **CodeGuard omitted nine rules:** additional cryptography (overlap and KMS
  assumptions), crypto algorithms (project-specific PQC and incomplete AEAD
  example), digital certificates (issuer/subject heuristic), hardcoded credentials
  (public identifiers/test material conflated with secrets), safe C functions
  (nonportable replacements), XML/serialization (fail-open hardening example),
  privacy (unconditional pinning), MCP (prompt/parameter logging), mobile
  (conflicting password/general platform guidance). These need separate review.
- **Trail of Bits sharp-edges 1.1.3:** no malicious directives found, but unsafe
  crypto ordering/path containment examples and incorrect Rust/Kotlin/Ruby
  claims, plus a missing plugin agent. Deferred pending corrected qualification.
- **Sentry skill-scanner:** helper may print original secret lines and read
  external symlink content before structural checking; unbounded reads and
  unpinned PyYAML through `uv run`. Not installed or executed.
- **OpenAI canonical Codex Security:** reviewed source identifies Apache-2.0,
  plugin 0.1.95 and CLI 0.8.1. This differs from stale `openai/plugins` catalog
  0.1.32 marked Proprietary. Current native/MCP workflows need matched runtime,
  supported Node/Python, provider access and platform sandbox qualification.
  `cs skills add` installs generated CLI guidance, not the full plugin. No
  portable runtime install or scan is claimed here; do not copy installed catalog
  skill bodies as proof of portable installation.
- **Old OpenAI security trio:** `openai/skills` is deprecated in favor of current
  plugins; not selected as maintained primary tooling.
- **Semgrep marketplace:** Rules License v1.0 redistribution restrictions need
  a separate license-fit decision before vendoring into a public source.
- **Current Claude Security plugin:** proprietary platform-specific licensing;
  not portable redistribution material. The older MIT review Action is a
  different product. No new provider integration is part of this bundle.
- **Other full marketplaces:** plugin agents, hooks and scanner/download helpers
  need their own complete review. No indiscriminate marketplace installation.

## Updating and rollback

Use the distribution feature runbook in the source repository for exact chezmoi
commands. Review a candidate in an isolated branch: provenance and official
ownership, maintenance/archive state, exact license exceptions/notices, complete
file set and links, instructions/scripts, execution dependencies, data destinations,
permissions, conflicts and overlap. Do not execute freshly downloaded helpers
just to assess them. Obtain required source-specific approval before adopting
unrecognized material.

Download the full immutable source archive into temporary review storage and
record its SHA-256. Select only listed paths. Preserve licenses and attribution;
mark all modified upstream files and record exact unified patches. Revalidate
bundle files and references, regenerate lock hashes after human-readable review,
and compare the patch with the pin. A checksum alone does not establish trust.

Run the original creator validator, integrity/delivery tests, affected instruction
checks and isolated second apply. Reconcile deployed drift before exact-target
installation. Keep the previous pin in Git for rollback; restore the previous
complete source bundle/lock and preview exact-target apply. Removal or replacement
of divergent live files needs an explicit migration decision. Reverting a skill
does not revoke runtime credentials or clean audit artifacts.

## Local toolchain profile

The explicit local setup profile adds Semgrep CE 1.182.1 from official PyPI
(LGPL-2.1-or-later), Gitleaks 8.30.1 from its official GitHub release (MIT),
and Google OSV-Scanner 2.7.0 from its official release (Apache-2.0). Full binary
digests, commit/source records, license copies and Python dependency hashes are
in `runtime/tools.lock.json` and its adjacent files. Toolchain dependencies are
allowed when explicitly requested; no good candidate is excluded solely for
needing an existing or approved local executable.

Gitleaks matches release checksums/API digest; no independent build signature
was found. OSV subject/source match SLSA metadata, but cryptographic signature
verification remains unavailable. Semgrep's selected Apple Silicon wheel has
PyPI publisher attestation; its complete runtime lock uses binary distributions
only. These provenance limits remain visible rather than presented as signed
build verification.

Semgrep version checks can contact the vendor by default, so setup uses disabled
version checks/metrics and empty temporary settings/environment. It never runs
Pro flags, login, registry rules or CI/MCP setup. Gitleaks setup never scans;
later scans require redaction and scope. OSV setup downloads no vulnerability
database: strict-offline scan readiness and freshness remain unavailable.

Codex Security, Daybreak, Semgrep Pro and organizational Gitleaks Actions stay
subscription-gated and disabled. The local CLI/source pins do not establish
entitlement. No subscription purchase, credentials, provider configuration or
permission expansion occurs in setup.
