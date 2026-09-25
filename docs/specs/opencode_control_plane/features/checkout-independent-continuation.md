# Checkout-Independent OpenCode Adapter

Status: specification ready; implementation and native qualification pending.
Initiative: `../../../initiatives/dbsctr-delivery-lifecycle/MANIFEST.json`.
Profile: `../PROFILE.md`; owner: dotfiles operator; risk: critical. Modules:
Python, Security and ML/AI. Use Bun/TypeScript, existing Python fixtures and the
managed native probe. This slice delivers source and disposable qualification;
installed host activation belongs to the dependent rollout slice.

## Authority And Baseline

The [core contract](../../dbsctr_v3_lifecycle/features/checkout-independent-continuation.md)
owns all identity, private schema, approval binding, state transitions and replay.
Core source merged as `24ff69a256808c3b9f0d85bcca63dadb703c10e9` in PR #178 after
Python 3.12/3.13/3.14 CI passed. This establishes the implementation dependency,
not installed or independently reviewed capability. The operator's core review
deferral expires before adapter rollout or any live v2 activation. No review was
present on that PR at this readiness check; preserve that availability honestly.

The reported original conversation still has a v1 adapter, invalid target routing
and no exposed release control. Restarting it did not install the missing source.
Its reported Plan mode also denies mutation. Switching another conversation to
Build does not establish this conversation's authority. Do not ask the operator
to restart again until reviewed, qualified deployment is ready to load.

Current source gaps: the before-hook validates the selected target before typed
diagnostics; `tools/dbsctr.ts` routes inspect/audit/status through a cached target;
`continuation.ts` validates only the v1 envelope and duplicates branch-derived
target lookup; runtime transport does not admit `continuation-v2`; no typed bind
or release exists. The correction belongs at these shared boundaries.

## Interfaces And Compatibility

Keep the exact core v1/v2 envelopes authoritative; do not duplicate the state
machine in TypeScript. Extend the existing bounded input runner to transport the
core `continuation-v2` command. Validate exact fields, types, enums, bounds and
nullable evidence before use. Reject malformed/unknown responses and never print
raw helper errors, private paths, registration custody or native storage bodies.

The new adapter requires a valid v2 read-only response from its paired helper
before admitting mutations. A missing/old/unreadable helper reports bounded
protocol or capability unavailability; it is not permission to retry a failed
v2 mutation through v1. No persistent helper-version cache may hide a replacement.
For a validated v2-capable helper, unbound cycles may continue their existing v1
execution path. Bound cycles use v2 admission and resolution. Binding remains
explicit; ordinary check, restart, read, attach and tool execution never upgrade
an existing legacy cycle silently.

| Typed tool | Arguments | Required behavior |
|---|---|---|
| `dbsctr_preflight` | existing optional worktree | Bounded diagnostic projection plus loaded adapter/protocol metadata; never attach, enroll, bind, recover or repair |
| `dbsctr_continuation_bind` | required worktree string | For a new unenrolled target, request exact v2 enrollment consent; for enrolled reader-only target, request exact bind consent. Owned/uncertain state requires separate recovery first. Return with no writer claim. |
| `dbsctr_attach` | existing optional worktree and reader/writer mode | Select the already-bound v2 target, or preserve qualified unbound v1 behavior; never combine ownership recovery with attachment implicitly |
| `dbsctr_continuation_recover` | existing optional worktree | Use v2 exact-state recovery including INT-049 route-only recovery; invalid explicit targets must not select an alternative cycle. No automatic quiescence assertion. |
| `dbsctr_continuation_handover` | existing optional worktree and explicit target session | Existing exact drain/transfer semantics using the appropriate validated protocol |
| `dbsctr_continuation_release` | empty object | Prepare and release only the caller's selected route; no arbitrary session/worktree selector, no redundant idle-writer confirmation; outstanding work still requires exact completion/recovery |

Request IDs come from native call identity, retained for retries of that same
request; they are not model arguments. Permission receipt IDs use existing native
approval handling. Approval binds the helper's exact expected snapshot and is
rechecked by the helper. Bind/enroll, provider change, handover and quiescence
remain separate confirmations. Never encode a model-supplied approval boolean.

Preflight adds `adapter_revision` with value `checkout-continuation-opencode-2`
and `capabilities` containing exactly `protocol` (2 or null), `bind`, `recover`,
and `release` (booleans). Preserve `adapter_available` as process-local plugin
registration evidence only. Capability booleans describe loaded implementations
with a validated helper protocol, not completed review, installed-byte attestation,
tool visibility in Plan, target eligibility, ownership or live qualification.
The core's `next_action` and unavailable fields retain their meanings. No generic
`qualified: true` may be inferred from a revision string or successful import.

Strip `local_target` from typed projections. Consume a successful core `resolve`
path only inside the adapter after exact response validation. Associate its cache
entry with cycle ID and route version, not branch name. Preserve existing
`cycleTarget` callers through shared cache helpers; do not create another registry.

## Diagnostic Routing And Tool Mediation

Validate native primary identity before applying exemptions. Preflight, bind,
recovery, handover and release are control operations outside the mutation they
must drain. Invalid target eligibility must not prevent typed inspect, audit or
status from reporting evidence. Preserve child restrictions and ordinary file-read
permissions; these exemptions do not admit shell calls or unknown tools.

- Fixed-commit `dbsctr_inspect` and `dbsctr_audit` use the independently valid native
  repository home when execution selection cannot resolve. They must not consume
  an invalid cached cycle cwd. This is an explicit read-only diagnostic path, never
  a canonical-home fallback for cycle writes.
- `dbsctr_status` retains ordinary authoritative status when a target is valid;
  otherwise it returns bounded diagnostic availability with the known cycle and
  ownership facts. Unknown state is unavailable, never no-selection or completed.
- Unbound v1 routes remain eligible only after their existing validation. Bound
  v2 routes resolve through the helper, not a duplicated Git branch hash.
- Before an edit/patch/shell/lifecycle call, validate target eligibility and obtain
  the proper generation-bound admission. A successful diagnostic response alone
  is insufficient: inspect target availability and the action-specific expected
  snapshot. Preserve path containment, symlink/Git-metadata rejection, per-call
  environment propagation and unknown-mutator refusal.
- Store protocol, native identity, cycle/route version and operation ID per call.
  Finish through the same admitted protocol; a failed or absent completion hook
  retains uncertainty. Preserve the exact native failed-call completion facility.
- On release or terminal completion, clear only a matching cached cycle/version.
  Replay of an old result cannot clear a later same-cycle attachment. Before the
  next tool, restore selection from the durable helper state.
- Direct/unmediated shell entry still requires matched admission. Cwd is not an
  OS sandbox; no detached mutating work or arbitrary shell classifier is added.

The adapter may return the helper's valid route-only recovery snapshot when target
evidence is unavailable. It must not guess an explicit target, re-create an active
pointer, perform Git repair, or edit a Cycle Record to obtain that snapshot.

## Permissions, Modes And Reload

Add `dbsctr_continuation_bind: ask` and `dbsctr_continuation_release: allow` only to
validated Build primaries, including the existing provider-affine Build profiles.
Default both to deny; Plan and children keep mutation denied. Preserve existing
recover/enroll/provider/storage/handover asks and raw continuation CLI denial.
Capability checks must fail before asking for consent when native authority is
missing; absence of a tool in Plan is not a request to use Bash instead.

No new global allow rule, provider change, session copying, automatic restart or
native directory rebinding. Config-time modules load once: after the separate
qualified rollout, the operator restarts the serving OpenCode process and opens
the exact existing conversation. Both loaded v2 controls and actual Build authority
must be demonstrated before any recovery/release attempt.

## Ownership And Validation

Implementation ownership is limited to existing continuation/runtime libraries,
plugin, typed DBSCTR tools, their necessary permission entries, provider-affine
Build instruction entries, scoped tests and the managed native probe. The core
helper and normative contracts remain outside adapter Build ownership. Material
core findings return readiness_reopened with evidence rather than silently
changing the merged helper. All work remains in the primary without delegation.

Reuse `tests/test_opencode_continuation.py`, relevant control-plane/permission
tests, the core conformance fixtures, and
`dot_local/share/opencode-continuation/native_probe.py`. Use the existing wrapper
`tests/opencode_continuation_native_probe.py`. No new framework or provider call.

Required disposable native scenarios:
1. Expose bind/recover/release in Build; Plan can preflight/inspect/status but cannot
   mutate, claim a writer or initiate quiescence consent. Children remain denied.
2. A selected invalid legacy route can inspect a fixed Git commit, report bounded
   status, obtain exact recovery consent when necessary and explicitly release.
3. Source branch switch/removal does not break an independent target. Bound target
   branch drift denies writes while diagnostic/recovery/release paths remain usable.
4. Release an unfinished dirty cycle, read the canonical Discovery checkout, then
   reattach to the preserved cycle in the same native session after process reload.
5. Denied/stale approval, running/uncertain calls, concurrent call contexts, old
   release replay and a later same-cycle selection preserve generation fencing.
6. Missing/old helper, malformed response, failed plugin initialization and mixed
   versions fail safely. Unbound legacy execution is not silently upgraded.
7. Preserve existing reader denial, provider transitions, terminal pointer-removal
   completion and interrupted-storage recovery. Local resolver paths never appear
   in typed outputs or the published fixture summaries.

Use distinct registered worktrees for native home, historical source and execution
target, sharing one Git common directory where the scenario needs them. The probe may manipulate only disposable
fixture state, using loopback scripted responses and copied public dependencies.
No production conversation or hosted model is a test fixture. Exact tool exposure,
successful/denied calls and native identity must be observed, not inferred from
source imports, version/help output or a mocked before-hook alone.

Kernel, Review/Integrate and Maintain/Retire are required. Release is not applicable
without a separately versioned artifact. Deploy/Operate are not applicable to this
source-only slice; host rollout owns them. The existing applicability plan remains
valid. Review context README and CHANGELOG; record actual completion evidence only
after implementation. All adapter implementation/qualification evidence is pending.

## Visual Evidence

| Concern | Decision | Owner / change trigger |
|---|---|---|
| Boundary | required: interface and ownership tables/prose above | Control-plane Discovery; authority changes |
| Interaction | required: flow below | Control-plane Discovery; approval or completion order changes |
| State | required: core transition tables, referenced rather than duplicated | Lifecycle Discovery; state-machine changes |
| Data/trust | required: diagnostic/local-path rules and flow below | Control-plane Discovery; disclosure changes |
| Schema | not_applicable: exact core envelopes/private schema are canonical; only bounded adapter capability metadata is added | Control-plane Discovery; interface changes |
| Dependency/deployment | required: flow below separates source qualification from rollout | Distribution Discovery; reload/activation changes |
| Quantitative | not_applicable: no comparative performance claim | No chart justified |

```text
Native primary identity
  -> paired-helper read-only capability/route check
  -> diagnostics: valid native Git home or bounded unavailable status
  -> controls: exact snapshot, required consent, atomic core transition
  -> execution: validated target, generation admission, per-call completion
  -> release result: clear only the matching cycle/version cache
Qualified source -> independent review -> targeted rollout -> controlled reload
  -> original-conversation Build preflight -> exact recovery/release
```

**Text Equivalent:** Diagnostic access does not depend on valid execution selection
and grants no writer. Controls use core snapshots and separate consent, while
execution requires target validation and generation-bound admission. Durable
release precedes matching-cache removal. Source qualification and independent
review precede targeted installation and reload; only then may the original
conversation prove its loaded Build controls and perform exact recovery.
