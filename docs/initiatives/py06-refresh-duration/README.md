# PY-06 Refresh Duration Delivery

This single-context delivery carries the existing PY-06 Discovery documents into
one clean implementation checkout through the native verified import route. It
does not add another context, independent work lane or runtime requirement.

## Context And Authority

`dotfiles_ai_distribution` in `Saltiola7/dotfiles-ai` owns this slice. There are no
context or slice dependencies. The existing
[refresh specification](../../specs/dotfiles_ai_distribution/features/history-projection-refresh-schedule.md),
[Engineering Profile](../../specs/dotfiles_ai_distribution/PROFILE.md),
[Product Intent](../../specs/dotfiles_ai_distribution/PRODUCT.md) and
[gate plan](../../specs/dotfiles_ai_distribution/PY-06.plan.json) remain authoritative.
The manifest maps every material statement to that specification or this handoff.

## Selected Scope

- INT-001: Correct newly completed durations to whole elapsed seconds, rounded down.
- INT-002: Measure the specified monotonic execution interval independently of wall time.
- INT-003: Retain Unix-millisecond timestamps, version-1 fields, emitted order and CLI behavior.
- INT-004: Preserve existing readable summaries until the next ordinary acquired run replaces them; do not guess historical units or introduce migration.
- INT-005: Preserve failure classes, counters, locking, private state and lifecycle snapshot ownership.
- INT-006: Prove rounding, wall-clock changes, failures, timeout cleanup, running nulls, legacy preservation and overlap through deterministic existing test seams.
- INT-007: Retain the elevated risk classification and preview wrapper/loader coupling; preserve enablement and do not interrupt an active refresh for activation.
- INT-008: Carry all applicable gates into one draft-PR delivery and scoped managed deployment/operation evidence after those gates; rollback preserves summaries and projections.
- INT-009: Keep other audit findings, dependency/tool migrations, unrelated validator changes and a forced real refresh outside this slice.

## Build Handoff

The primary owns registration, integration and delivery. Bounded helpers may
research or review; they do not register independent cycles, commit, publish or
deploy. Implementation ownership is the existing managed wrapper and
`tests/test_history_projection_refresh.py`, with the existing specification and
completion changelog updated as required.

Run the repository's existing publication/instruction authority over the exact
staged candidate artifacts before receipt and preflight. Use the committed
manifest and plan identities in a clean-base checkout, obtain launch-specific
approval after successful preflight, and register only that unchanged launch.
No implementation, gate pass, deployment or merge is established by this document.
All kernel, review, deployment, operation and maintenance gates apply; release is
inapplicable because this slice publishes no versioned artifact or hosted service.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | not_applicable: the existing feature's ownership flow defines the single context; no boundary is added here |
| Interaction | required: launch handoff table below |
| State | required: launch handoff table below |
| Data/trust | not_applicable: only public committed documentation is imported; runtime trust boundaries remain in the feature |
| Schema | not_applicable: no runtime schema change; native manifest schema is reused |
| Dependency/deployment | not_applicable: no new dependency or topology; wrapper/loader coupling is specified in the feature |
| Quantitative | not_applicable: no measured comparison or forecast |

| Handoff state | Required action | Result |
|---|---|---|
| Committed Discovery | Publication checks, manifest check and fresh receipt | Exact public artifact closure identified |
| Clean-base Build checkout | Digest-bound native preflight | Launch feasibility established without registration |
| Preflight passed | Explicit approval for the displayed launch digest | Exact registration may proceed |
| Registered cycle | Existing kernel and completion gates | Implementation and delivery evidence retained |

**Text Equivalent:** Committed documentation is checked before receipt. A clean
Build checkout performs preflight without registering; explicit approval then
permits only that exact launch, followed by the normal gates. Source: Build
Handoff. Owner: distribution maintainers. Update trigger: registration or delivery
contract changes.
