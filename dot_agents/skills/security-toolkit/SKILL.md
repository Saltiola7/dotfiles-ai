---
name: security-toolkit
description: Select and verify dotfiles-ai managed security skills for secure coding, scoped reviews, independent audits, CI review, or known-bug variants.
---

# Security Toolkit

Choose the smallest applicable technique and one coordinator. Installation or
loading this skill does not authorize an audit, target-code execution, tool
installation, remediation, external writes, or access changes. Respect the
current request and any existing denied or separately owned audit work.

Read [references/routing.md](references/routing.md) for selection and evidence
contracts. Read [references/review.md](references/review.md) when considering
updates, new sources or deferred tools. Exact commits, selected paths, original
and packaged hashes, licenses and dispositions are in
[references/sources.lock.json](references/sources.lock.json).

`vendored` means source content exists. Verify the complete files at the active
shared skill root before claiming installed readiness:

```sh
python3 <security-toolkit-dir>/scripts/verify_bundle.py --skills-root <shared-skill-root>
```

The verifier has no network calls or installer. It checks trusted directory
content against the local lock; it does not authenticate upstream, supply a
sandbox, prove safety or validate a finding. Source/model-provider disclosure
still follows the user's existing provider and data policy.

Do not fetch tools or rules just because a selected technique mentions them.
Use configured authorities; missing scanner, runtime, license eligibility or
OS isolation stays an explicit capability gap.

For explicitly requested local toolchain setup, read
[references/runtime.md](references/runtime.md). The pinned local profile installs
Semgrep CE, Gitleaks and OSV-Scanner in isolated generations with existing uv;
only sanitized version probes are allowed during setup. Subscription-backed
profiles remain disabled until the user confirms the required entitlement.
