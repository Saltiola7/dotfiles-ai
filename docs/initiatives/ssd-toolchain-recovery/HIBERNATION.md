# Hibernation — explicitly deferred

Operator decision: pause hibernation and surface it after the rest of this recovery,
upgrade and migration work is done. It is not a prerequisite for declaring the
other workstreams complete. No plugin installation, fork or repair is currently
authorized by this deferred slice. Do not silently drop it from the final report.

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
| Deferred | Other work complete | Surfaced to operator with current gaps |
| Deferred/surfaced | Explicit request to resume | Discovery; requalify candidate and implementation scope |

**Text Equivalent:** no hibernation implementation now; revisit explicitly after
the rest completes, then requalify before Build. Canonical source: this decision.
Owner: primary maintainer; update trigger: operator resumption or changed requirements.
