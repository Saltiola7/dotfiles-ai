# Bounded Host probe diagnostics

## Scope and authority

INT-044 records approval to prepare bounded diagnostics, not implementation or
deployment approval. Reuse `shell_auth_startup`, its Engineering Profile and the
existing signed probe-only Host. Risk is elevated: live reliability, private
metadata and signed deployment. No Herdr/OpenCode fork, automatic restart,
privacy-policy change, volume migration or permanent promotion helper.

Historical EIO classification does not prove a physical disk fault. The latest
follow-up observed another degraded interval beginning on 2026-10-09; private
evidence preserves that interval. Do not claim historical root cause or current
recovery from source inspection or a successful unrelated shell probe.

## Behavior and compatibility

- Given a probe fails, when health is published, diagnostic metadata identifies
  the failing stage and distinguishes a native errno from a synthesized legacy
  classification. Existing state, error category and errno semantics stay intact.
- Given volume identification uses a subprocess, when it fails, diagnostics
  distinguish launch failure, timeout, nonzero exit, invalid property list and
  missing volume identifier. Preserve exit status when available, not raw output.
- Given a later probe succeeds, when healthy status replaces degraded status,
  current diagnostic fields are absent and the latest failure remains retained.
- Given diagnostic persistence fails, when the normal probe result is published,
  diagnostics do not prevent health recovery or change its classification.
- Given an older record lacks diagnostics, when the candidate reads it, normal
  status/preflight behavior remains compatible. Existing schema-1 consumers must
  accept candidate records; rollback must read them without migration or deletion.

The current health schema remains **1**. Add one optional `diagnostic` object to
health/status/doctor output, absent on non-failure records. Its bounded vocabulary:

| Field | Allowed meaning |
|---|---|
| `stage` | state-root open, filesystem inspection, volume identification, volume match, filesystem recheck, sentinel open/inspection, or write/read/sync/cleanup probe stage; use stable enum tokens, not operation strings |
| `failure_kind` | native POSIX failure, subprocess launch/timeout/exit, plist decoding, missing UUID, volume mismatch or sentinel validation failure |
| `errno_origin` | `native`, `synthesized`, or absent where no errno is reported |
| `subprocess_status` | exit status only when available; absent otherwise |

Canonical stage/failure coverage, owned by this contract:

| Stage tokens | Source path and diagnostic distinction |
|---|---|
| `state_root_open` | root open failure; native errno |
| `filesystem_inspect` | every `fstatfs` used in initial device/UUID lookup; native errno |
| `volume_identify` | subprocess launch, timeout or exit; plist decode or missing UUID; legacy EIO/permission/unavailable errno is synthesized |
| `volume_match` | expected UUID mismatch; no errno |
| `filesystem_recheck` | native inspection errno versus synthesized changed-filesystem ESTALE |
| `sentinel_open` | native open errno, retaining existing permission/missing-sentinel category |
| `sentinel_inspect` | native `fstatfs`/`fstat` failure versus filesystem mismatch or non-regular sentinel; generated EINVAL is synthesized |
| `probe_directory_create`, `probe_directory_open`, `probe_directory_inspect` | native mkdir/open/inspection errno versus filesystem mismatch |
| `probe_file_create` | native create errno |
| `probe_write`, `probe_sync`, `probe_rewind`, `probe_read` | native write/sync/seek/read errno versus generated zero-write/short-read EIO |
| `probe_verify` | content mismatch; synthesized EIO |
| `probe_remove`, `probe_directory_sync` | native unlink/directory sync errno |

`failure_kind` uses `posix`, `subprocess_launch`, `subprocess_timeout`,
`subprocess_exit`, `plist_decode`, `missing_uuid`, `volume_mismatch`,
`filesystem_changed`, `sentinel_validation`, `short_io` or `content_mismatch`.
Deferred best-effort descriptor/file cleanup retains its existing semantics; do
not invent a probe failure for an ignored cleanup result. Diagnostic coverage
must not change EINTR retries, subprocess deadlines or normal failure mapping.

Native versus synthesized refers to the origin of the emitted legacy `errno`
value. A subprocess diagnostic still distinguishes timeout/exit even where the
legacy classifier emits EIO. No fields may be derived from unbounded exception
strings. Build must cover every failure return in `filesystemProbe`, not only
the old symptom's pre-sentinel path. No new diagnostics are required for unrelated
registration or signing commands.

## Private retention and trust

Keep one `last-failure.json` beside existing private health metadata, outside the
external authoritative state root. Maximum encoded/read size **4096 bytes**;
owner-only file mode **0600**, directory **0700**. The failure record contains
only its schema version, observed timestamp, health state/category/errno and the
diagnostic object. Successful probes leave it unchanged; subsequent failures
replace it atomically. No unbounded history or automatic archive cleanup.

Use existing descriptor-relative, no-symlink, user-ownership and atomic-replacement
conventions. Reject unsafe record input; do not read/follow a symlink or alter its
target. Failed writes clean their temporary file, preserve the prior failure
record and leave ordinary health behavior intact. Do not change the existing
health-record write-failure contract.

Exclude paths, device names, command arguments, subprocess stdout/stderr, free-form
errors, signing credentials, prompts, session IDs and database contents. Diagnostics
are explanatory metadata, never admission authority or conversation truth.

## Validation and delivery

Affected source: `.chezmoitemplates/herdr-host.swift`; affected tests:
`tests/test_herdr_launchagent.py`. Review the context README, OPERATION and
CHANGELOG; update durable operation/privacy truth in the same implementation PR.

Qualify actual source through isolated Host fixtures. Cover state-root open and
filesystem errors; each subprocess outcome; sentinel and write-probe failures;
native/synthesized distinction; legacy permission/unavailable mappings; optional
field compatibility; failure retention after recovery; file modes, bounds,
atomicity and unsafe records; diagnostic-write failure without recovery failure.
Fault injection remains testing-build-only. Run affected existing Host tests and
Swift compilation, not repository-wide QA.

INT-046 approves the unchanged source's isolated decoder fixture as backward
compatibility evidence. Keep production signing, registration, registered-agent
health and rollback checks mandatory at deployment. Source review finds schema
equality to 1 and keyed Swift/Python readers.

The unchanged Host source compiled with its existing testing-only define accepted
an additive field and ignored the sidecar without rewriting the input record.
An isolated copy of the installed production binary refused the disposable bundle
location under its native registration-identity guard. Preserve that refusal;
do not bypass the guard, forge launch provenance or modify live health for a test.
That production-binary refusal remains retained failed evidence. The approved
source fixture substitutes only for this isolated decoder check, never for live
identity, signing, registration, healthy-probe or rollback evidence.

Deploy only through a separately qualified, journaled signed probe-only replacement:
preserve prior signed bundle and health/ownership evidence, signature and expected
volume binding, unrelated configured-source overlays and every live Herdr
conversation/layout identity. Do not finish or retire the failed helper cycle.
Stop if replacement could stop the Herdr server or change child ownership. Obtain
fresh healthy registered-agent evidence and rollback qualification; a degraded
deployment is not successful merely because new diagnostics explain it.

Reuse the retained one-time repair procedure, not the unfinished permanent
helper. Its 16 existing synthetic signature/ownership/consent/interruption and
registration-recovery checks passed again during readiness review. For this slice,
the candidate's configuration must be **identical** to the current canonical
configuration, including expected volume UUID; the old procedure's allowance
for a UUID change is not authorization here. Both signed bundles must mutually
satisfy the same designated requirement. Requalify the exact candidate and
procedure digests before live execution, including failed/healthy diagnostic
record rollback and unchanged live server/layout metadata. No procedure mutation
or signed candidate was deployed during Discovery.

Kernel and Review/Integrate gates are required. Deploy, Operate and Maintain/Retire
are required; Release is not applicable because this is a machine-local signed
Host, not an independently published package. Keep failed evidence and private
recovery artifacts. Normal feature-branch draft delivery targets protected `main`.

## Readiness and approval

Specification readiness is established by the approved decoder evidence,
existing journaled replacement qualification and explicit failure-stage map.
No applicability-plan registration or live activation is claimed. The committed
applicability plan accompanies the Build-owned slice; copy it to the checkout's
ignored `.dbsctr/plans/` before native preflight. Issue a fresh Initiative receipt
immediately before launch, then present exact scope, risk, target and launch digest
for approval. Launch feasibility remains subject to native preflight, not Herdr
presentation state. Missing inherited Herdr context does not block Discovery,
coding, validation, native lifecycle preflight or harness continuation. It makes
only Herdr-specific inspection unavailable under the integration's caller-context
rule. Obtain fresh preservation evidence before any live operation that could
affect panes or sessions; do not fabricate environment identity or reuse stale
process evidence. A deployment-specific evidence gap is not a global coding gate.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | not_applicable: existing shell-auth Profile/OPERATION owns signed responsibility; does this add another runtime owner? No. |
| Interaction | required: ordered procedure below; can diagnostic failure prevent recovery? |
| State | required: behavior list and existing OPERATION Health Model; do diagnostics alter transitions? No. |
| Data/trust | required: private-retention field table/prose above; can sensitive process output be persisted? No. |
| Schema | not_applicable: bounded private records have no relational entities; optional-field contract above is canonical. |
| Dependency/deployment | required: delivery procedure above; can signed replacement disrupt live children? Stop if it can. |
| Quantitative | not_applicable: size bound is a safety limit, not comparative evidence. |

**Text Equivalent:** Probe establishes its normal result, attaches only allowlisted
failure metadata, publishes normal health and attempts bounded failure retention
without changing recovery on diagnostic-write failure. A successful later probe
publishes normal healthy status without deleting prior failure provenance. Signed
deployment preserves old bundle and live identities, qualifies replacement and
rollback, and never automatically restarts Herdr/OpenCode. This document owns the
ordered diagnostic contract; shell-auth owner updates it when behavior, fields,
retention or delivery changes.
