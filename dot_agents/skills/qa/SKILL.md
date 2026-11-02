---
name: qa
description: Run DBSCTR affected-scope quality gates or explicit repository-wide audits, including optional Engineering Profile capability coverage.
---

# Quality Assurance

## Inputs And Scope

- `scoped`: evaluate touched files, imports, manifests, packages, tests, specs,
  direct downstream contracts, and optional Engineering Profile requirements.
- `full`: inventory configured repository concerns only when explicitly requested;
  keep baselined debt visible.

Ask one short question when mode or affected scope is ambiguous. Never expand a
scoped gate silently.

Calls without an Engineering Profile retain configured-tool behavior. DBSCTR
calls supply applicable Capability Requirements and Gate Ledger context.

## Toolchain Profile

Read project instructions, manifests, lockfiles, task runners, CI, pre-commit,
and documented commands. For each configured concern, record command, scope,
baseline/suppressions, availability, and one project-selected authority:

- formatting/linting, typing, tests/coverage
- code/application security and secrets
- dependencies, vulnerabilities, licenses, and current Dependabot alerts
- dead code/complexity, docs, mutation/fuzz/property tests
- build/package/release/publish
- deployment, operations, recovery, and maintenance evidence when configured

Use relevant configured concerns and **do not install tools**. Suppressions limit
evidence; they do not prove suppressed code passed. An unavailable required tool
records a blocker and next-best evidence, never a pass. Overlapping tools may
inform but only one authority gates each concern.

Use configured JFrog Xray as vulnerability authority when declared; otherwise
use configured `pip-audit` for resolved Python dependencies. For actual configured
JFrog/Xray work, load `jfrog` and only the relevant security reference; installing
that guidance does not configure Xray or create an additional audit gate. Authenticated
Dependabot alerts are finding inputs, not a competing gate.

## Python typing evidence

Use the project-selected checker, commands and environment bindings. Temporary
compatibility checks follow the consumer's migration policy; report their distinct
roles without treating checker agreement as proof of correctness.

Reconcile execution against an independent inventory of the selected Python
population, including tests, notebooks and relevant new files. Report excluded,
generated, vendored and archived artifacts with their approved disposition;
exclusions never count as checked. Bind every selected artifact to each required
environment. A root invocation does not prove nested-project or notebook coverage.

Report the denominator and completed analysis units separately from diagnostic
results, actual child exit codes, Any/unknown limitations and suppressions. An
empty population is not applicable, not 100%. Missing evidence is not zero
findings; paths or a successful exit alone do not prove every file was analyzed.
Affected-scope percentages are not repository-wide coverage. Full-coverage
acceptance requires the full approved population.

Missing environments, crashes, incomplete analysis or unsupported notebook/cell
mapping remain coverage gaps. Ordinary type errors may coexist with completed
analysis but remain failed diagnostic evidence. Setup success does not waive a
required typing gate or create a Gate Exception. Preserve original failures and
replacement evidence; report gaps and typing failures through the Gate Ledger.

Reject blanket ignores, broad exclusions, unjustified Any/casts, diagnostic
disabling, exit-code masking or an automatic green baseline. Narrow suppressions
need rationale, scope and a review condition; suppressed concerns are not passes.
Classify conflicts before proposing bounded repairs, preserving runtime contracts
and intentional negative tests. Keep detailed checker comparisons project-owned.

## Capability Coverage

For PR evidence, select affected mappings and workflow definitions from the trusted
target base, not changed-branch self-exemption. Verify exact tested head/base and
native producer identity; names, branch claims or helper assertions are not proof.
Unknown closure requires conservative repository-selected broad checks or blocks.
Only success passes affected checks; unrelated pending requires trusted explicit
classification and exact-repository opt-in. Keep failed/expired/drifted waivers
visible and never waive mandatory security/data-loss/auth safeguards. `dbsctr-pr-review`
owns the recommendation/checkpoint; QA does not authenticate or authorize merges.

When an Engineering Profile is supplied, map every applicable Capability
Requirement to its authority or equivalent evidence and classify it:

- `evidenced`: required evidence passed
- `missing`: no authority or equivalent evidence exists; this is a capability gap
- `unavailable`: configured authority could not run
- `failed`: authority ran and failed
- `deferred`: owner and concrete follow-up recorded
- `accepted_risk`: rationale, owner, and expiry/review condition recorded

Missing, unavailable, or failed required capability blocks a scoped pass unless
the lifecycle records valid deferral or `accepted_risk`. QA never prescribes a
universal tool when an outcome can be evidenced another project-approved way.

## Execute

1. Establish mode, affected scope, repository state, Toolchain Profile, and
   optional Engineering Profile.
2. Select the minimum authorities covering the scope and required capabilities.
3. Run independent read-only checks concurrently; serialize shared caches,
   generated files, lockfiles, or outputs.
4. Collect issues that can cause wrong behavior, failed validation, security
   exposure, data loss, misleading output, or lifecycle evidence gaps.
5. Verify and normalize source, location, concern, severity, confidence, scope,
   capability status, and remediation state. Deduplicate by root cause.
6. Report findings before editing; omit unrelated noise in scoped mode unless it
   prevents isolation.
7. Rank actionable findings into collision-safe Fix Batches with ownership,
   safety class, expected files, and focused validation.

## Fix Classes

- `safe`: deterministic formatting or unambiguous tool correction with no
  behavior, contract, schema, dependency, policy, or lifecycle change
- `review_required`: dependency, suspected dead code, security policy, mutation
  survivor, complexity redesign, broad typing, or uncertain semantics
- `escalate_dbsctr`: behavior, contract, schema, orchestration, validation rule,
  capability policy, or downstream-visible change

Never auto-delete suspected dead code; verify references, dynamic loading,
public APIs, and generated boundaries. Do not broaden dependency updates. Re-run
the concern authority and focused tests after each applied safe batch.

## Delegation And Git

Delegate only independent work with explicit read/write/off-limits paths,
collision risk, output, and validation. Subagents never stage, commit, push,
deploy, publish, or write externally. The primary reviews and integrates all
changes and alone performs requested Git writes.

## Report

Lead with findings ordered by severity. Include mode and scope, authorities and
unavailable checks, capability coverage, each finding's location/confidence and
status, Fix Batches/escalations, validation, changed files, accepted risks, and
residual risk.

Also return a structured block for DBSCTR consumption. Each entry contains
`capability`, `authority`, `scope`, `Gate Result`, `evidence`, and `residual_risk`.
Gate Result is `passed`, `failed`, `unavailable`, or `not_run`; applicability and
any Gate Exception remain separate lifecycle decisions.

A scoped gate passes only when applicable findings and Capability Requirements
are resolved, validly deferred, or accepted as risk and all required available
authorities ran. A full audit may complete with debt but exposes every verified
finding and disposition.
