# Codex CLI OpenShell pilot adapter

Status: normative adapter target, not live qualification. Owner: Codex CLI
control-plane maintainers. Profile: [PROFILE.md](../PROFILE.md). Initiative:
[OpenShell pilot](../../../initiatives/openshell-pilot/README.md).
Risk: elevated for authentication and runtime compatibility; dependent host
mutation boundary is critical. Existing profile remains current.

## OpenAI subscription compatibility

Codex keeps the current subscription route and provider affinity. A dedicated
attended login and explicit gateway handoff must be qualified without reading or
importing the normal host login cache. The
[provider contract](../../shell_auth_startup/features/openshell-provider-handoff.md)
owns that handoff, single refresh ownership and revocation.

NVIDIA's v0.1.6 Codex example is feasibility evidence, not permission to copy its
host-login import or expose an unauthenticated app-server listener. Qualify
sandbox-local CLI login recognition and opaque credential substitution. Any
placeholder configuration must contain no reusable grant. Host native CODEX_HOME,
updater ownership, existing hooks and sessions remain unchanged. Runtime-local
managed instructions and selected skills use their existing owners.

Native approval/sandbox behavior and history hooks remain supported where
qualified. A nested isolation failure is a capability gap; outer containment
does not authorize disabling native permissions. Current hook attribution may
remain unavailable and cannot be manufactured by the bridge.

## Common boundary

The explicit host launcher selects the agent and existing Worktrunk checkout,
reserves it through the current host owner, and passes only a generation-bound
enrollment. The client runs interactively inside its own OpenShell workload.
Host app-server exposure, Desktop management and a general host service bridge
are not required by this pilot.

This is a separate opt-in trial entrypoint, selected for each new pilot session.
Installing the adapter does not intercept ordinary Codex commands, Desktop
launches, resume paths or automation, and does not enable OpenShell by default.
The [activation contract](../../dotfiles_ai_distribution/features/openshell-pilot-activation.md)
owns selection, refusal and coexistence with ordinary sessions.

Project code, tests and dependency scripts execute inside the sandbox. All host
Git, Worktrunk and lifecycle effects use the
[restricted host contract](../../dbsctr_v3_lifecycle/features/openshell-host-boundary.md).
The client may request supported operations, but cannot invent caller approval,
override parent permissions, change the target, or replace existing lifecycle
authority. No arbitrary host command or generic lifecycle CLI forwarding.

Mount only reviewed instructions/configuration/skills needed by this route.
Preserve native session semantics with separate workload-owned state; do not copy
host sessions, inspect undocumented stores, infer identity from environment, or
claim Desktop compatibility. Native instructions must clearly distinguish local
sandbox execution from typed host-owned operations.

## Behavior

- Given explicit enrollment and qualified runtime/authentication, when this client
  starts, then it uses its intended provider and selected checkout only.
- Given missing identity, expired grant, incompatible configuration or blocked
  network access, when launch or inference fails, then retain work and report the
  capability gap without changing provider, billing route or execution boundary.
- Given a project check, when the client runs it, then execution remains inside
  OpenShell and host lifecycle receives only qualified observed evidence.
- Given a Git/lifecycle request, when the host adapter handles it, then existing
  supported workflow and approval ceilings remain intact.
- Given restart or interrupted host operation, then resume only the same known
  valid native session/workload binding or report recovery unavailable; never
  fabricate successful continuation.
- Given ordinary native launches outside the pilot, then their configuration,
  authentication, services and behavior remain unchanged.

## Acceptance and delivery

Require intended-provider requests including streaming, short-lived-token refresh,
restart, revocation, independent host login, tool use and a representative
edit/test/signed-Gate-Commit/draft-delivery flow. Qualify every supported Git
capability from the host matrix, including denial and recovery cases. One client
passing does not complete the two-client pilot. Model prompts for qualification
are synthetic; private project contents and transcripts are not test evidence.

Use existing rendered configuration, client capability checks, affected pytest
and real selected-runtime smokes. Kernel, Review/Integrate and Maintain/Retire
gates are required; there is no separate package Release. Source-only
Deploy/Operate non-applicability requires the joint activation slice to own actual
qualification. No approved gate exception or live compatibility is claimed here.

This adapter slice remains dependency-gated on runtime, dedicated provider
handoff and the qualified host interface. Resolve native nested-sandbox behavior
and client/version-specific configuration before promotion; do not relax client
protections automatically to make the outer sandbox work.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary | required: ownership table below; which side owns each action? |
| Interaction | required: ordered acceptance journey above; what proves daily workflow? |
| State | not_applicable: native session and shared enrollment states remain authoritative |
| Data/trust | required: ownership table and provider contract; where may secrets and code execute? |
| Schema | not_applicable: no alternate client session or lifecycle schema |
| Dependency/deployment | required: dependency statement and ownership table |
| Quantitative | not_applicable: no measured performance claim |

| Resource | Owner |
|---|---|
| Interactive client, project commands, native session | Selected OpenShell workload |
| Reusable provider material and refresh | Qualified trusted gateway |
| Checkout identity and Git/lifecycle mutations | Existing host owners through restricted interface |
| Runtime/policy/images and enrollment | Distribution plus operator |
| Default host client and sessions | Existing native owner; preserved |

**Text Equivalent:** The agent and project code run in the workload; reusable
provider material remains at the gateway. Host owners retain identity and Git/
lifecycle mutations through the restricted interface. Runtime, provider and host
interface qualification precede adapter promotion. Canonical source: this feature
and its linked contracts. Owner: this control-plane maintainer. Change trigger:
native behavior, authentication, permissions, interface or qualification changes.
