# V2 one-time distribution source

Status: source implementation contract; live qualification remains separate.
Owner: project maintainers. Profile: ../PROFILE.md. Product: ../PRODUCT.md.
Risk: critical. Authority: opencode-rolling-stable INT-010–018, INT-022–030,
INT-033–034 and opencode-v2-recovery.md. Modules: Python, Security, Cloud.

## Scope and dependencies

Implement the one-time CLI artifact staging and managed generation boundary in
the existing distribution helper and launcher. Reuse atomic writes, ownership
checks, bounded subprocesses and locking. Do not create another updater daemon,
history converter or continuation bridge. Recurring OpenCode/Codex update work
remains deferred. Desktop, service/data admission, real guest qualification and
active-route retirement remain required in v2-fleet-cutover-retirement.

Native-workspace source for both harnesses was delivered in PR 193. The Codex
dependency is satisfied at source level: merged sandbox/approval preservation,
retired continuation hooks, shared CLI validation and 99 refreshed affected tests
with native Codex 0.155.1. PR 194 supplies the ordered OpenCode configuration,
native preferences and V2 plugin qualification. Neither dependency claims rollout.

## Artifact and generation contracts

- Resolve the official stable CLI npm metadata only during explicit staging.
  Bind the release, platform package name/version, registry SHA-512 SRI, archive
  length/digest and executable digest. Qualified initial candidate is 2.0.22;
  replacing it requires new qualification, not an automatic latest lookup during
  activation or launch. Support the profile's Darwin arm64, Linux arm64 and Linux
  x64 artifact identities; each platform still needs its own native qualification.
- Accept only official HTTPS registry/artifact locations, bounded metadata and
  archives, expected package identity/platform and regular archive members.
  Reject traversal, links, duplicate members, digest drift and unexpected payloads.
  Execute no npm lifecycle hooks. Preserve staged/failure evidence on interruption.
- Use an explicitly versioned V2 generation record with its actual npm provenance.
  Do not forge a V1 GitHub-assets lock. Validate exact keys/types, local ownership,
  file modes, platform, candidate identity and executable checksum. Unknown or
  malformed generations refuse startup and mutation without rewriting the record.
- Staging remains separate from activation. Version/help and other staging probes
  use disposable roots and no production provider/history access. They do not
  constitute live service, permission, history or Desktop admission.
- An ordinary full apply/update must recognize a valid V2 generation and report
  that recurring updates are held. It must neither consult the V1 feed, downgrade
  the binary, rewrite V2 provenance nor run V1 validation/recovery against it.
  A malformed generation fails; a healthy retained generation is not reported as
  freshly upgraded. Existing V1 users retain their supported behavior.
- Managed launch verifies the admitted V2 generation before exec. It preserves
  native arguments and external-state-root refusal. It must not repair, convert
  history, start an alternate internal data root or silently roll back on launch.
- Explicit maintenance activation must preserve the previous binary and lock and
  an interrupted-transition record. A partial binary/lock pair blocks normal
  startup. V1 binary-only rollback must never run across a V2 data transition.
  Admission requires the coherent configuration/service/data recovery evidence
  from opencode-v2-recovery.md; source tests cannot fabricate this live evidence.
  After new V2 work, recovery preserves that generation rather than restoring an
  old database. No backup/archive disposal belongs to this source slice.

## Acceptance and validation

### Concrete interface boundary

Extend `opencode-update-all` with explicit `stage-v2`, `activate-v2` and
`admit-v2` maintenance modes. Existing `exec-managed` and no-argument update
entrypoints remain stable. Maintenance requests are bounded JSON on stdin,
never credentials or history bodies. `stage-v2` takes an exact release and the
verified official platform artifact metadata; it cannot follow a moving latest
selector. `activate-v2` names the canonical staged candidate digest and exact
current-generation preimage. `admit-v2` names that same generation and a private
recovery/admission manifest whose bytes are bound by SHA-256. Missing, stale or
changed preimages fail closed. These requests are operator workflow records, not
authenticated native actor identity or a replacement writer lease.

The V2 `release-lock.json` uses schema version 2. Its generation fields are
`schema_version`, `channel`, `release`, `platform`, `binary_sha256`, `artifact`,
`validator_revision`, `admission` and `previous`. `artifact` contains exact
`package`, `version`, `url`, `integrity`, `size` and `sha256`; `integrity` is
publisher SHA-512 SRI and `sha256` binds the verified archive. `previous` is null
or the validated prior generation, without recursive prior-history embedding.
`admission` is null until the explicit maintenance checks succeed, then records
the immutable private admission-manifest digest. The manifest binds candidate,
configuration, service and data generation identities plus retained recovery
references and completed reconciliation evidence. Startup verifies its digest
and generation association without rereading message bodies. Candidate locks
remain separate from active locks. The local manifest is private retained
evidence, not a claim of cryptographically authenticated operator consent.

All public status output is bounded to version, phase/result, target count and
closed reason codes. Private paths, credentials, service tokens, session IDs and
recovery contents do not enter status output. The source slice qualifies these
interfaces on synthetic manifests; actual admission remains a downstream gate.

1. Valid fixture metadata/archive stages the exact executable without hooks,
   network fallback, production access or implicit activation.
2. Wrong package/platform, duplicate or malformed metadata, archive hazards,
   digest changes and unsupported schemas fail without changing active state.
3. V1 projection, startup, update and recovery regression tests remain passing.
4. A valid admitted V2 fixture launches with exact arguments; tampered, partial,
   unadmitted or unknown generations refuse. Missing external storage refuses.
5. Full apply/update retains a healthy V2 fixture with an explicit held result;
   no V1 fetch, revalidation, guest rollback or mutation occurs on that path.
6. Interrupted maintenance preserves preimages and reports recovery required;
   no automatic database restoration or previous-generation deletion occurs.
7. Existing pytest, chezmoi rendering and shell syntax authorities cover the
   changed source. Native host artifact smoke is additional bounded evidence;
   Linux fixtures do not qualify a guest and CLI does not qualify Desktop.

Kernel, Refactor, Review/Integrate and Maintain/Retire are required. Release,
Deploy and Operate are not applicable to this source-only PR; the downstream
live slice retains its mandatory deployment and operations gates. Merge passing
PRs under the operator's explicit approval; no direct main-branch push.

## Visual Evidence

Boundary and data/trust: required, reuse V2-MIGRATION.md's canonical boundary flow
and opencode-v2-recovery.md's recovery-unit contract. Dependency/deployment:
required, reuse the Initiative dependency table. Interaction and state: required,
the transition table below is canonical for this source delta. Schema:
not_applicable, strict generation serialization is specified in prose and tests;
no relational model. Quantitative: not_applicable, no comparative claims.

| State | Permitted transition | Refused automatic action |
|---|---|---|
| Existing V1 | Explicit isolated V2 staging | Unqualified V2 activation |
| Staged V2 | Qualified maintenance preparation | Full-apply activation |
| Maintenance incomplete | Evidence-preserving recovery/reconciliation | Normal launch or V1 binary-only rollback |
| Admitted V2 | Verified native launch; held recurring update | V1 validation, downgrade or history conversion |
| V2 with new work | Evidence-preserving forward recovery | Old snapshot restoration over new work |

**Text Equivalent:** Stage outside production. Maintenance preparation retains
preimages and blocks normal launch until the entire generation is admitted.
Admitted V2 launches without mutation and holds unsupported recurring updates.
Interrupted or post-admission recovery preserves both historical and new work.
Owner: distribution maintainer; update on generation, admission or recovery changes.
