# Supported retirement journey

Status: Discovery specification; runtime qualification pending. Owner: OpenCode
control-plane maintainer. Profile: [../PROFILE.md](../PROFILE.md). Risk: critical;
modules ML/AI and Security. Canonical state, interfaces and preservation rules:
[lifecycle retirement recovery](../../dbsctr_v3_lifecycle/features/cycle-retirement-recovery.md).

## User outcome and boundary

The user asks to stop, replace or retire work and receives one supported journey:
inspect, choose disposition, approve exact closure, inspect preservation, approve
capture/preparation/removal and recover interruptions. Do not prescribe private
record editing, forced deletion, manual reset/stash surgery or a fake completed
replacement. Record closure and physical removal are distinct outcomes.

Support terminal and exact chat-confirmed CLI operations. Present each exact
preview effect and digest before action; a generic continue, permission grant or
earlier closure approval is not removal consent. The primary's agent-confirmed
flag is a consent assertion, never authenticated actor proof. Plan stays read-only.
No custom identity service, continuation plugin, new session or provider switch.

Reuse existing native session_move for current-conversation handoff. Preserve
history, attachments and saved compaction; inspect returned unchanged identity
and canonical directory. Finish/pause writers and synchronize compatible clean
primary by approved fetch/fast-forward before moving. For explicit archived
non-success work, local preservation replaces merge proof only under the lifecycle
contract. Never require merging cancelled work merely to move its conversation.

Idle MCP/read-only consumers may coexist with operator-confirmed record closure.
Before closure, old writers must be stopped and incompatible clients kept out as
an operational prerequisite; updated clients enforce terminal records, not universal
fencing. Shared held locks or positively identified live writers refuse closure.
Historical unfinished intervals alone are uncertain, not live-writer proof;
optional/missing history never proves inactivity. Obtain explicit writer-quiescence
assertion rather than infer it from history. No new liveness/identity service.
Before checkout preparation/removal, all relevant consumers must leave. Session
move is not proof that child MCP processes moved or exited. Recheck process/open
file inventory after handoff. No automatic signaling or guessed PID ownership.
If supported native session/tool shutdown or restart is necessary, present exact
scope and get separate operator approval; preserve conversation and in-flight
outcomes. Qualify actual native behavior on installed runtime before claiming the
journey is hands-off. If unavailable, return `consumer_shutdown_required` with
supported operator UI/service action, not shell kill instructions. Keep cycle
retired and checkout retained, with resumable removal status.

Idle historical checkout needs no recreated conversation. Current-live handoff
unavailable, conflicting ownership or other writers retain checkout. Repeating
retirement after successful closure returns recorded outcome rather than asking
for fake completion. Changed archive/checkout/selection requires renewed approval.
Closure replay retains original approved digest, verified original-byte preimage
and custody; validate intent and terminal record against original plus exact
approved metadata. Only pointer_status may reconcile under the lifecycle contract.
Initial pointer conflict refuses; post-terminal reassignment retains pointer,
reports recovery_required and blocks registration. Prepared evidence remains a
private sidecar, not an active-record retirement state. Drift cannot authorize a
different outcome under stale consent; genuine completed history stays intact.

## Validation and source ownership

Update managed `private_dot_config/opencode/AGENTS.md`, shared DBSCTR/Discovery
guidance and narrowly related existing permission configuration only as needed.
Retain native deny/ask boundaries and projection privacy. Existing shared CLI is
harness-neutral; this slice qualifies OpenCode only, not new Codex runtime controls.
Do not add a standalone skill or wrapper when existing lifecycle guidance suffices.

Use `tests/test_opencode_control_plane.py`, `tests/test_dbsctr_lifecycle.py`,
`tests/test_native_workspace_execution.py`, `tests/test_native_cli_projection.py`
and `tests/test_native_opencode_permissions.py`. Cover Plan denial, both consent
methods, no premature removal, preserved historical failure, current-session move
plus lingering MCP consumer, declined restart, move-success/removal-failure and
status/retry from primary. CLI end-to-end reachability remains lifecycle-owned.
Add focused guidance regressions for live/held-lock versus historical-uncertain
classification, explicit assertion despite missing history, incompatible-client
operational exclusion and original-digest-only reconciliation without outcome drift.
Publication check uses existing portable-distribution authority. Native runtime
tests must preserve same conversation history; fixture success is not live proof.

All kernel gates, Review/Integrate, Maintain/Retire required; source Release,
Deploy/Operate not applicable under CONTROL-PLANE-SOURCE.plan.json. Results
pending, no exceptions. Installed qualification belongs to distribution rollout;
unavailable native shutdown cannot block delivery of record-only closure.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: reuse lifecycle ownership table |
| Interaction | required: journey table below |
| State | not_applicable: lifecycle state table is canonical |
| Data/trust | not_applicable: existing native handoff and lifecycle privacy contracts remain canonical |
| Schema | not_applicable: consumes lifecycle CLI results, no new schema |
| Dependency/deployment | not_applicable: Initiative and rollout specification own dependencies |
| Quantitative | not_applicable: no performance claim |

| Step | Evidence / decision |
|---|---|
| Inspect and close | Exact preview, shared-lock/live-writer checks, explicit quiescence and old-writer/incompatible-client exclusion; separate approval, checkout stays. |
| Preserve | Exact artifact inventory and archive verification; no body forwarding or automatic ignored-file capture. |
| Handoff | Compatible primary and same native conversation; preserve messages/attachments/compaction. |
| Drain consumers | Fresh inventory; separately approved native shutdown if needed, otherwise retain. |
| Prepare/remove | Separate exact approval, supported supervisor/hook, verified membership and retained branch. |
| Resume | Validate original digest, intent, preimage/hash, custody and exact terminal record; only pointer_status reconciles, reassigned pointer retained and registration blocked. Cleanup needs its independent approval. |

**Text Equivalent:** Closure may succeed with an idle consumer only after shared-lock
and positive live-writer checks, explicit quiescence and operational exclusion of
old writers/incompatible clients. Historical intervals or absent history cannot
establish inactivity. Retry validates original authority and exact terminal outcome,
changing only pointer_status; reassignment retains pointer and blocks registration.
Prepared sidecars do not retire active records. Physical
preparation/removal waits for verified preservation, native handoff where needed,
and no consumers. Failed cleanup retains successful closure and supports retry.
Source: lifecycle contract and this journey; owner: OpenCode maintainer; revisit
on consent, session movement, consumer lifetime or native tool changes.
