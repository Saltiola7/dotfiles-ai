# Codex continuation: native capability qualification

Status: capability qualification in progress; mutation adapter not ready.

## Scope and profile

Use `../PROFILE.md`. Risk is critical because the dependent adapter would admit
governed mutations. The operator authorized preparation, review, merge to main,
and deployment of Codex continuation support. This explicitly adds the existing
desktop conversation to the otherwise CLI-only context. It does not redirect
desktop state into managed CLI state or authorize reading private transcripts.

The immediate prerequisite is a passive hook probe in the actual desktop runtime.
It cannot authorize continuation, change a Cycle Record, or establish identity
by itself. Existing OpenCode ownership and failed qualification remain intact.
Do not remove the helper's Codex-unavailable guard on the strength of this probe.

## Domain

A native observation is a sanitized fact received on the documented hook input.
A matching pre/post pair shares hashed session, turn and call identifiers. A pair
is evidence that this tested tool path has callbacks, not proof that every tool
path is covered or that a session is a primary. A storage directory is an
operator-selected, owner-only local diagnostic boundary, separate from transcripts
and continuation authority. The probe owns no lifecycle state.

## Behavior

1. Given a supported hook payload, observation stores only bounded event/tool
   categories, identifier digests, field-presence flags and a local timestamp.
2. Given secrets in command, output, cwd, transcript path or unknown fields, none
   of those values or field names are retained or returned.
3. Given duplicate keys, excessive input, invalid identities, unsafe storage,
   capacity exhaustion or a contended lock, observation produces no record and
   returns without affecting the pending tool. This is explicitly passive.
4. Given unrelated configured hooks, installation preserves them exactly as JSON
   values. An existing hook file is backed up before the additive change.
5. Given no native observations after configuration, readiness remains unavailable.
   Synthetic unit tests must not be presented as native identity evidence.
6. Given a restart requirement, pause for the operator to restart the same
   conversation; do not launch a substitute session or copy native state.

## Interface and contract

`codex-continuation-probe --state DIRECTORY` accepts one JSON hook on stdin.
Supported events are SessionStart, PreToolUse, PostToolUse, Stop, Interrupt and
SessionEnd. Input is bounded to 1 MiB; storage to 256 records of at most 2 KiB.
Opaque session, turn, call and model values are bounded ASCII and stored only as
SHA-256 digests. Unknown tools become `other`; provider and agent fields are
reported only as presence flags. No field implies a provider, primary role or
permission to write. Missing fields stay null or false.

The directory must already exist, belong to the current user, have no group/other
access, and not be a symlink. Use a held directory descriptor, exclusive creation,
0600 records and a nonblocking owner-private lock. Existing records are never
overwritten or automatically pruned. No stdout/stderr contains hook content.
No subprocess, network, transcript read, enrollment or helper mutation is allowed.

Deployment is a bounded probe of a reviewed candidate, not promotion of the
continuation adapter. Keep candidate identity, original hook-file bytes and exact
added entries in private evidence. Remove only the matching probe entries on
rollback; preserve concurrent edits and retained observations. Restart/reload
requirements and native trust prompts are operator actions, never bypassed.

## Qualification and remaining readiness

After restart, exercise native shell, shell through code mode, apply_patch,
long-running exec completion/polling and a read-only MCP call. Inspect pre/post
pairs without retaining their arguments or results. Separately prove denial,
primary/child identity, provider/model binding, actual native approval and
interruption semantics before implementing write admission. A missing capability
reopens the adapter design; it is not solved by trusting environment variables.
The eventual adapter must preserve generation fencing, provider-transition
approval, admission/finish, uncertain-operation recovery and mixed attribution.

Selected authority: `pytest tests/test_codex_continuation_probe.py`, Python
compilation, existing Codex control-plane tests, and actual post-restart callback
observations. Test records are disposable and cannot be imported as native
identity. Review source and tests before configuring the live probe. No rollout
to other desktops, guests or CLI homes is implied.

## Visual Evidence

| Concern | Decision | Owner and change trigger |
|---|---|---|
| Boundary | required: trust flow below | Control-plane owner; authority changes |
| Interaction | required: qualification table below | Control-plane owner; deployment changes |
| State | required: qualification table below | Control-plane owner; readiness changes |
| Data/trust | required: trust flow below | Control-plane owner; retained fields change |
| Schema | not_applicable: independent bounded records; exact fields defined above | Control-plane owner |
| Dependency/deployment | required: qualification table below | Control-plane owner; installation changes |
| Quantitative | not_applicable: no comparative performance claim | Control-plane owner |

| Source | Transformation | Destination and authority |
|---|---|---|
| Native hook input | Bound parsing; discard all content and paths; hash identifiers | Owner-private observations; diagnostic only |
| Unit-test input | Same parser against disposable storage | Fixture evidence; never native authority |
| Observations plus supported native interfaces | Future explicit readiness review | Adapter design; no automatic enrollment |

**Text Equivalent:** Native input and synthetic fixtures use the same sanitizer
but remain distinct evidence. Only private metadata is retained. Observations
feed a later readiness review and never confer lifecycle authority.

| State | Permitted next action | Refused implication |
|---|---|---|
| Candidate tested/reviewed | Add passive hook, preserve backup | Adapter operational |
| Configured but unobserved | Reload/restart same conversation | Synthetic test equals native pass |
| Native callbacks observed | Evaluate missing authority capabilities | All tools covered |
| Capability incomplete | Persist gap, revise design | Bypass helper guard |

**Text Equivalent:** Test and review precede probe installation. The same native
conversation must produce evidence before readiness evaluation. Missing evidence
blocks mutation support while ordinary ungoverned diagnostics remain possible.

Source: [official hooks contract](https://learn.chatgpt.com/docs/hooks), inspected
2026-09-20. In particular, some specialized paths can opt out of hooks; they are
guardrails rather than a complete enforcement boundary.
