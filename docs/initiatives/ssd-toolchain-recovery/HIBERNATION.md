# Hibernation — qualification resumed, activation blocked

Latest decision INT-034 resumes qualification after exact-session recovery,
superseding blanket deferral in INT-017/020. Python updates are separately paused
under INT-032. Activation requires the contracts below; repair/fork scope and
implementation ownership must be resolved before Build registration.

Home: shell_auth_startup. Existing PROFILE.md remains authoritative. Owner: primary
maintainer. Review trigger: completion report for all non-deferred workstreams,
or earlier explicit operator request. No expiry date is invented.

## Retained requirements for resumption

- OpenCode only; at least fifteen minutes idle and unfocused.
- Keep focused, working and blocked sessions alive.
- Restore exact native conversation, cwd and launch options; no most-recent guess.
- Preserve registry ordering and detect real process exit; qualify crash/interruption
  cases before deployment.
- Draft text and exact scroll-position loss remain accepted limitations.
- Prefer existing integration and official Herdr support; repair/fork scope is
  undecided until resumed, not implicitly authorized.

Dependencies for later activation: signed Herdr Host recovery, final native-launch
and update behavior, and isolated eligibility/exact-session tests. Recheck the
candidate release and original known gaps at resumption; historical review is not
qualification of a changed version.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: OpenCode-only scope explicit |
| Interaction | not_applicable: no implementation or activation now |
| State | required: transition table below |
| Data/trust | not_applicable: no state transfer in this deferral |
| Schema | not_applicable: no registry design selected |
| Dependency/deployment | not_applicable: prose names future prerequisites |
| Quantitative | not_applicable: fifteen minutes is a requirement, not a measurement |

| Current state | Trigger | Next state |
|---|---|---|
| Deferred | Explicit request to resume | Discovery; requalify candidate and implementation scope |
| Discovery | Recovery or sleep/wake evidence missing | Activation blocked; preserve live sessions |
| Discovery | Scope, dependencies and qualification resolved | Fresh Build readiness and registration preflight |

**Text Equivalent:** qualification resumed; implementation requires fresh
readiness and registration, activation requires exact recovery evidence.
Canonical source: this decision.
Owner: primary maintainer; update trigger: operator resumption or changed requirements.
