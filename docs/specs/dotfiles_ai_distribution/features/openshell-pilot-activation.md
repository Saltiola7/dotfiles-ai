# OpenShell pilot activation on the selected Mac

Status: normative target; dependent runtime, provider, host-interface and agent
qualification must pass before this slice becomes ready. Owner: distribution
maintainers. Engineering Profile: [../PROFILE.md](../PROFILE.md). Product Intent:
[../PRODUCT.md](../PRODUCT.md). Initiative:
[OpenShell pilot](../../../initiatives/openshell-pilot/README.md).

Current-cycle risk is critical because untrusted agent work can request bounded
host mutations and use authenticated providers. Applicable modules remain Python,
Security and Cloud. Delivery intent includes reviewed source and explicit opt-in
activation on the selected Apple Silicon Mac. No credential access, installation
or activation is authorized merely by persisting this specification.

## Outcome and prerequisites

Activate both Codex CLI with the operator's existing subscription account and
OpenCode with the operator's existing Vertex Claude account/project route, using
separate attended sign-ins and isolated provider state. Validate the agents
sequentially first, with one active workload. Both must directly edit registered
Worktrunk source files, run tests inside OpenShell, and complete the full supported
managed Git workflow through the qualified host interface.

The first real repository is dotfiles-ai. Use a clean dedicated native Worktrunk
linked checkout; each independent writer/cycle retains its own checkout under
existing ownership rules. Existing work, primary checkouts and unrelated linked
checkouts are not enrollment candidates by implication. A dirty or ineligible
candidate refuses activation; never clean, reset, stash, replace or remove its
contents automatically. The second agent receives fresh enrollment only after
the first workload and its outstanding operations have reached a known state.

The exact activation selection must bind all of the following before start:

| Prerequisite | Required proof |
|---|---|
| Source and installed adapters | Reviewed immutable source revision, coherent installed generation and passing publication/instruction checks |
| Worker and runtime | Qualified Lima/Fedora/Podman/OpenShell versions and component digests, architecture, kernel controls and current storage identity |
| Agent images | Qualified Codex and OpenCode executable/image digests and compatible configuration; no moving image selection |
| Policy | Exact operator-owned filesystem, network and provider-binding generation; telemetry disabled and automatic access approval disabled |
| Provider routes | Separate attended same-account grants, one refresh owner, current access and refresh evidence, normal host login preserved |
| Host interface | Qualified transport, closed operation schemas, native caller permissions, request/replay handling and revocation |
| Signing and Git features | Exact qualified native identity/profile, signer and trusted hook/configuration closure; no workload-writable execution dependency |
| Checkout enrollment | Native repository/common-directory/administrative identity, selected branch and HEAD, clean initial state, applicable cycle and approved operation scope |
| Resources and concurrency | Explicit private worker CPU, memory, disk and process limits; one active workload for initial validation; adequate retained-state capacity |
| Recovery | Bounded operation journal/status and data-preserving stop, revocation and rollback procedures |

**Text Equivalent:** Activation requires one coherent reviewed generation of
runtime, images, policy, provider routes and host interface, bound to the exact
native checkout and signer. Private resource limits and recovery capacity are
selected explicitly. Missing, stale or conflicting evidence refuses start.
Canonical source: this prerequisite contract and the dependent feature contracts.
Owner: distribution maintainers. Change trigger: selected component, authority,
identity, policy or storage change.

Reuse [runtime qualification](openshell-pilot.md),
[provider handoff](../../shell_auth_startup/features/openshell-provider-handoff.md),
[Codex qualification](../../codex_control_plane/features/openshell-pilot.md),
[OpenCode qualification](../../opencode_control_plane/features/openshell-pilot.md)
and [host Git/lifecycle authority](../../dbsctr_v3_lifecycle/features/openshell-host-boundary.md).
Activation does not relax a dependent refusal or turn an unavailable capability
into an accepted exception. Full workflow preserves current Git approval,
protected-base, evidence, signing and preservation rules; it does not authorize
arbitrary Git commands, history rewrites or a new host execution channel.

## Native operation contracts

The following describe required behavior, not newly established CLI names or
flags. Implement them through qualified native interfaces and existing owners.
The operator's machine-local selection contains private runtime, checkout and
account bindings. Discovery and status reporting inspect capability metadata
without reading provider secrets or publishing private selectors.

| Operation | Behavior | Mutation boundary |
|---|---|---|
| Inspect | Report installed generations, prerequisite freshness, workload state, bounded operation status and blockers | No login, provider-token read, model call, process start or configuration repair |
| Dry-run | Resolve and display exact enrollment, effective permission differences, selected resources, retained state and installation targets | No file apply, grant creation, runtime start, Git mutation or implicit consent |
| Start | Revalidate the approved exact selection, reserve native checkout ownership, attach qualified providers and activate one workload | Only the selected enrollment; drift returns to review rather than widening scope |
| Pause/resume | Suspend every workload descendant while gateway stays available; resume the same qualified native session | No replacement session, provider substitution or new checkout enrollment |
| Stop | Deny new host requests, settle or classify in-flight operations, then stop the selected workload and preserve source/session/evidence state | No repository reset, provider-grant deletion, VM destruction or automatic native fallback |
| Revoke | Reject new enrollment requests immediately, quiesce the workload, detach workload-facing provider access and invalidate its generation-scoped authority | Report incomplete containment if quiescence or detachment cannot be confirmed; retain private grants and data for separately authorized disposition |
| Restore native use | Verify stopped/revoked state, trusted Git identity, retained changes and known operation outcomes before explicit native launch | No hidden continuation, automatic data apply or fabricated session identity |

**Text Equivalent:** Inspection and dry-run are nonmutating. Start acts only on
the reviewed selection after fresh validation. Pause/resume retains the native
session. Stop and revocation first close new host requests and resolve uncertain
operations, then contain the workload while retaining work and credentials.
Restoring native use is explicit and requires trusted checkout identity.
Canonical source: this native-operation contract. Owner: distribution
maintainers with existing host-interface and provider owners. Change trigger:
operation semantics, sequencing or authority change.

Revocation does not undo a completed Git or remote operation. A request whose
outcome is uncertain remains quarantined for native status reconciliation; do
not replay it blindly. Provider grant removal, revocation of the underlying
account authorization, private-state deletion and VM destruction each retain
their separate explicit approval and preservation requirements.

## Self-hosting and host execution boundary

Agents may edit dotfiles-ai source but cannot deploy their own changes to the
Mac while running. Source edits do not change the host helper, signer, hook,
policy or runtime generation used by that enrollment. Trusted host components
must come from the approved immutable installed generation, outside the writable
checkout. Do not load Python modules, shell helpers, plugins or configuration
from agent-edited source into a privileged host process.

Project tests, installation-script previews and any code derived from modified
source execute inside the sandbox. A qualified host hook that transitively runs
an agent-edited script is not safe merely because the hook file is unchanged.
Required host-executing features need their full execution dependencies qualified;
otherwise the operation refuses. Existing mandatory checks remain required.

After agent work, stop and revoke its enrollment, reconcile operation outcomes,
review the exact resulting commit and effective configuration, and run existing
affected gates. Applying changed dotfiles content to the Mac is a later explicit
targeted deployment with its own reviewed source/target selection. No writes to
the primary branch or direct protected-base delivery are introduced. Do not
restart unrelated services or apply the entire source tree as a convenience.

## Behaviors and joint success evidence

1. **Clean enrollment.** Given the selected dedicated dotfiles-ai checkout,
   when native identity, cleanliness, branch/HEAD, generation and reservation
   checks pass, then start enrolls only that checkout. Given dirty files, a busy
   writer, aliasing, stale evidence or changed identity, start refuses and retains
   every file and existing process without repair-by-deletion.
2. **Two sequential agent routes.** Given qualified separate same-account
   sign-ins, when each agent completes its initial validation in turn, then Codex
   uses its subscription and OpenCode uses Vertex Claude. Both prove streaming,
   refresh, restart and pause/resume behavior through their native clients.
   Normal host logins and unrelated sessions remain usable. API-key substitution,
   another provider, or success from only one agent cannot complete the pilot.
3. **Direct coding.** Given an approved bounded coding task, when either agent
   edits and tests source, then the host sees the exact selected-worktree changes
   and tests execute in the enrolled workload. The agent cannot modify sibling
   checkouts, shared Git metadata, installed host components or host configuration.
4. **Full managed delivery.** Given current caller permissions and completed
   lifecycle prerequisites, when the agent requests its supported Git workflow,
   then the existing owners perform evidence admission, signed Gate Commits,
   fetch/push and draft Final Push with exact destination/account checks. Signature
   verification uses the intended host signer. Existing approval-required actions
   still await their authority; denied operations remain denied.
5. **No transitive host escape.** Given modified project scripts, Git attributes,
   hooks, filters or configuration, when an operation would execute their content
   on the host, then the qualified boundary refuses or runs the applicable check
   inside OpenShell. No generic shell, executable, environment or alternate-target
   selector crosses from workload to host execution.
6. **Negative controls.** Given either enrolled agent, when it attempts unrelated
   filesystem access, Git-pointer replacement, unapproved egress, direct networking
   without proxy variables, credential extraction, host administration or broader
   approval, then access is denied and protected state remains unchanged.
7. **Stop and failure.** Given a lost gateway, unavailable signer, denied request,
   failed refresh, storage failure or uncertain mutation, when recovery begins,
   then new work stops, private operation state and source edits are retained, and
   the exact blocker is reported. No unsigned retry, alternate credential, native
   fallback, reset or duplicate remote operation occurs.
8. **Post-work deployment.** Given agent-generated dotfiles changes, when the
   coding task ends, then only review and validation may proceed automatically
   within existing authority. Host apply requires stopped/revoked enrollment and
   a separately reviewed targeted deployment; a signed commit is not apply consent.

The complete capability matrix in the host-boundary contract must have current
passing evidence for both agents. Approval-required paths are exercised through
their real approval boundary or safely controlled qualification fixtures as
appropriate; tests must not perform destructive production actions solely to
claim coverage. A skipped or unqualified required capability is a blocker, not
an accepted completion. Worktrunk creation, conflict recovery and retirement
continue to use their existing owners and preservation checks.

## Rollback, operations and privacy

Default remains disabled. Activation records one private exact-target selection;
no global shell alias, provider default or automatic agent routing changes.
Additional concurrent workloads require explicit private resource selection and
qualified independent checkout/enrollment behavior. They are not enabled by the
first sequential result. Cooperative host locks do not exclude arbitrary trusted
host writers; quiescence and drift detection remain required.

Rollback disables new enrollment, preserves outstanding operation status, stops
the selected workload and retains dirty source, commits, private sessions and
evidence. It may restore only the reviewed compatible managed generation and
configuration targets. Uncertain state is retained for recovery, not overwritten.
Returning to native agent use is a separate explicit selection after identity and
process checks; failure never chooses that path automatically.

Operational evidence stays private and bounded. Public records contain sanitized
generation/version and pass/fail information, not machine paths, account/project
selectors, provider tokens, native transcripts or raw operation payloads. Do not
read provider-secret stores to populate a status page. Use the qualified provider
owner's content-free readiness and refresh outcomes.

## Gate Ledger

| Gate | Applicability | Initial result | Required evidence or reason |
|---|---|---|---|
| Domain | required | not_run | Enrollment, installed authority and resource ownership |
| Behavior | required | not_run | Joint journeys and negative controls above |
| Spec | required | not_run | Native-operation and exact-target activation contracts |
| Contract | required | not_run | Freshness, identity, approval, generation and refusal validation |
| Test Driven Implementation | required | not_run | Meaningful activation, rollback and dependent-interface regressions |
| Refactor | required | not_run | Reuse existing lifecycle, signing, provider and Worktrunk owners |
| Review/Integrate | required | not_run | Independent boundary review, publication checks and full capability coverage |
| Release | not_applicable | not_run | No separate versioned package is published by this activation slice |
| Deploy | required | not_run | Exact reviewed selected-Mac activation and configuration evidence |
| Operate | required | not_run | Both real provider/client journeys, signed delivery, denials and recovery |
| Maintain/Retire | required | not_run | Conservative update, revocation, retention and separately approved retirement |

No Gate Exceptions are approved. Existing Engineering Profile authorities apply:
rendered configuration, shell/checksum validation, affected pytest,
publication/instruction checks and actual native runtime smokes. Dependency
readiness and source tests cannot substitute for the real two-agent operation
evidence. Intended delivery is the existing reviewed branch/PR route plus opt-in
Mac activation; actual push and deployment outcomes belong to the Cycle Record
and completion report.


## First live task boundary

The first real task in each dedicated dotfiles-ai checkout is a documentation-only
improvement to the pilot runbook based on observed qualification evidence. It
exercises direct edits, portable validation, signed Gate Commits and draft
delivery without modifying live installers, host launchers or native application
code. The two agents own distinct useful documentation changes or separate
qualified task cycles; do not manufacture conflicting duplicate work.

Choose applicable portable checks from the existing repository authority. Tests
requiring macOS APIs, signing or host services remain explicit capability gaps
for workload execution. They do not run on Mac through a generic test bridge.
Existing hosted CI remains separate delivery authority. Required native validation
for a later native-code task requires its own qualified route or explicit native
workflow selection; initial documentation-only success does not claim arbitrary
macOS development support.

## Visual Evidence

| Concern | Decision | Review question |
|---|---|---|
| Boundary | required: prerequisite and native-operation tables | Which exact authority may act on the host and checkout? |
| Interaction | required: native-operation table and post-work deployment sequence | When may mutation, stopping, review and host apply occur? |
| State | required: native-operation table | How do started, paused, stopped and revoked workloads differ? |
| Data/trust | required: prerequisite and native-operation tables | Which credentials, source bytes and requests may cross boundaries? |
| Schema | not_applicable: activation consumes qualified existing private contracts | No new public persistent schema is introduced here |
| Dependency/deployment | required: prerequisite table | Which exact dependent generations must pass before real activation? |
| Quantitative | not_applicable: no performance or cost claim is made | Private resource limits are selections, not measured benefits |

The tables and adjacent Text Equivalents are canonical editable visual evidence.
The post-work sequence is: contain the workload, reconcile outcomes, review the
exact source, validate, then separately approve and perform targeted host apply.
Owner: distribution maintainers. Change trigger: deployment, state or trust
boundary change.
