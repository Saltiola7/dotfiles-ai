# OpenShell autonomous coding pilot

Status: Initiative Discovery. The five-context map is approved. The first bounded
outcome is credential-free runtime qualification; the completed pilot requires
both authenticated agents, full supported Git workflow and real Mac activation.
Specification readiness, launch feasibility, implementation and deployment are
separate proofs. No runtime or credential action has run during Discovery. Scope interview is
resolved; downstream technical qualification remains outstanding.

## Product intent and decisions

Contain autonomous coding on the selected Apple Silicon Mac without changing the
operator's Codex subscription or OpenCode Vertex Claude route. Both agents must
edit existing Worktrunk checkouts directly. Other checkouts and shared Git state
remain protected through a restricted host interface. A repository-copy or
patch-return workflow does not satisfy this request.

The operator approved five existing contexts, full existing Git workflow,
default denial of unqualified host-executing hooks/features with selected trusted
hooks/signers qualified separately, and source plus opt-in Mac activation.
The operator confirmed parity with existing managed capabilities and unchanged
approval/preservation rules. First real activation uses a dedicated dotfiles-ai
Worktrunk checkout. Fresh separate attended sign-ins use the same existing
provider accounts while preserving normal host grants and sessions.

The initial runtime experiment uses Fedora/Lima and rootless Podman. Native Mac
MicroVM replacement remains a deferred alternative, not pilot rollout. Existing
native launches remain separately selectable and never become automatic fallback.

## Approved ownership and dependencies

All contexts have one home repository: Saltiola7/dotfiles-ai. Context work began
only after the operator approved this complete map.

| Context | Owned contract | Depends on |
|---|---|---|
| dotfiles_ai_distribution | Runtime/image recipes, fixture runner, launch/state/update/rollout ownership | None |
| shell_auth_startup | Dedicated provider bootstrap, refresh and host-login preservation | Distribution |
| codex_control_plane | Codex subscription and native CLI compatibility | Distribution and Shell Auth |
| opencode_control_plane | OpenCode service boundary, Vertex Claude and native permissions | Distribution and Shell Auth |
| dbsctr_v3_lifecycle | Worktrunk identity, restricted host Git and existing lifecycle integration | Distribution |

The primary retains context readiness and serial slice promotion. Helpers may
research bounded questions or write explicitly owned documents; they do not own
independent cycles, approval or lifecycle state.

## Normative artifacts and evidence basis

- [Runtime qualification](../../specs/dotfiles_ai_distribution/features/openshell-pilot.md)
- [Provider handoff](../../specs/shell_auth_startup/features/openshell-provider-handoff.md)
- [Codex adapter](../../specs/codex_control_plane/features/openshell-pilot.md)
- [OpenCode adapter](../../specs/opencode_control_plane/features/openshell-pilot.md)
- [Host Git/lifecycle boundary](../../specs/dbsctr_v3_lifecycle/features/openshell-host-boundary.md)
- [Real Mac activation](../../specs/dotfiles_ai_distribution/features/openshell-pilot-activation.md)

Existing Engineering Profiles remain the stable platform and ownership authority;
each feature records pilot overrides. Distribution's existing PRODUCT.md is the
Product Intent authority. All five context READMEs and CHANGELOGs were reviewed.
README links introduce prospective contracts; no completed implementation cycle
or rollout entry is fabricated in a changelog.

Pinned upstream research reference: NVIDIA/OpenShell v0.1.6, Podman driver,
sandbox runtimes, security controls, provider profiles, Google/Vertex provider,
Codex app-server example, and the open dedicated-login proposal. Source reference:
reviewed dotfiles-ai baseline 69c1d0a. Upstream capability does not establish local
kernel, grant, nested-client, live-mount or host-interface compatibility.

## Delivery slices

| Slice | Owner | Dependencies | Outcome |
|---|---|---|---|
| runtime-qualification | Distribution | None | Synthetic direct-worktree boundary, enforcement, whole-workload pause and failure evidence |
| provider-handoff | Shell Auth | Runtime | Both dedicated provider routes, one refresh owner, independent normal host login |
| host-git-boundary | Lifecycle | Runtime | Closed authenticated operations, existing gates/approvals, full capability and recovery matrix |
| codex-adapter | Codex | Provider and host boundary | Native subscription CLI and complete qualified workflow |
| opencode-adapter | OpenCode | Provider and host boundary | Native Vertex Claude client and complete qualified workflow |
| mac-pilot | Distribution | Both adapters | Real selected checkout activation, rollback and operation proof |

The first slice is an isolated evidence cycle, not a production prototype to merge
as an activated service. Its source delivers bounded fixtures, reviewed recipes
and a runbook. All dependency results must be real and current before a successor
is promoted. One agent or a limited Git subset never completes the joint pilot.

Full-workflow coverage includes inspection, staging, signed commits, existing
phase evidence/commits, fetch/push, draft delivery, Worktrunk operations and the
existing permissions for conflict recovery and retirement. Force/no-hooks bypass,
unapproved history rewrites and general host execution remain excluded.

The host interface must not proxy arbitrary dbsctrctl commands. In particular,
record-evidence can execute a program: the host constructs a fixed qualified
sandbox adapter so project tests stay inside OpenShell while the existing
lifecycle continues to own evidence admission and Gate Commits.

## Risks, assumptions and unresolved evidence

| Item | Disposition |
|---|---|
| Nested Fedora/Lima/Podman kernel enforcement | Runtime slice must prove it; no privileged/unconfined fallback |
| Direct mounts and Git-pointer/alias protection | Must pass synthetic hostile fixtures before real enrollment |
| Whole-workload pause preserves agent session | Runtime mechanism first; each authenticated client repeats proof |
| Codex dedicated subscription handoff | Candidate upstream pieces; combined flow remains unqualified |
| Vertex Claude streaming and refresh | Official provider support exists; actual client compatibility unqualified |
| Host Git execution through hooks/configuration | Critical boundary; transitive execution and selected signer require qualification |
| Native host concurrency | Cooperative locks do not exclude arbitrary trusted host writers; require quiescence, freshness and uncertainty handling |
| Bridge transport and closed schemas | Selected native host-initiated exec, bounded versioned families and host-approved handles; actual lifecycle ownership and per-mode native approval mapping need qualification |
| Direct MicroVM replacement | Deferred; experimental status and shared-directory kernel-compromise limits remain |
| Normal host state and unfinished work | Preserve on every refusal, failed refresh, rollback and retirement |

No Gate Exceptions or accepted security-boundary waivers exist. Allowed network
destinations can still receive data; containment does not prove correctness of
agent work. No new security or performance effectiveness rate is claimed.

## Resolved scope and remaining technical evidence

No scope preference remains open. Existing Git approval rules are preserved,
first real activation targets dedicated dotfiles-ai Worktrunk tasks, and separate
attended sign-ins use the same accounts. Initial real tasks are documentation-only
runbook improvements with portable checks; this qualifies the intended workflow
without pretending Linux workloads can run arbitrary native Mac validation.

The host interface uses native host-initiated exec rather than an inbound Mac
command server. Upstream exec has no atomic generation precondition. The contract
therefore requires exclusive trusted controller ownership, never-reused sandbox
names and closure of mutation admission on disconnect, restart or uncertain
identity. No native generation or user-identity attestation is invented.

Remaining evidence is explicit: actual nested isolation and mounts, whole-workload
pause/resume, native transport ownership/cancellation, provider grant and refresh
semantics, trusted effective approval mapping, exact enabled Git-mode schemas,
signer/configuration closure, source-bound evidence and recovery. Resolve these
through their bounded predecessor results; do not ask the operator to repeat the
settled scope choices. Failure reopens only the affected technical decision.

## Gate applicability and validation

Every slice uses its existing committed Engineering Profile. The initial
RUNTIME.plan.json is artifact-ready input for subsequent Build preflight: all six
kernel gates, Review/Integrate, disposable Deploy, actual Operate and
Maintain/Retire are required. Release is not applicable because no separate
package is published. Later plan files record the same gate obligations for
their owning context; they do not make those slices ready.

All gate results start not_run; there are no exceptions. Deployment into a
disposable worker is distinct from activation of a real checkout. Required live
provider, signing, transport and native-client checks cannot be replaced with
source-only fixtures.

The repository's configured publication/instruction authority is:
- tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers
- tests/test_opencode_control_plane.py
- tests/test_dbsctr_lifecycle.py

Stage only candidate docs before the Git-index publication inventory. Use existing
authorities rather than a new privacy denylist. Validate MANIFEST.json after every
material change. Validate relative links, gate plans, complete import closure and
visual Text Equivalents. No new implementation tests are authored during Discovery.

## Initial Discovery validation checkpoint

The configured publication/instruction command passed 89 tests with one existing
native OpenCode V2 test skipped because no explicit native test binary was
selected. That skip is not native runtime evidence or a pilot Gate Exception.
Relative document links, eleven-gate plan inventories, artifact existence and the
complete changed-document import closure passed structural checks. The manifest
validator initially identified only runtime-qualification as ready. Independent
read-only contract review found no blocker before live qualification.

Those checks established documentation readiness only. They did not establish
runtime, credential, model, deployment or launch-preflight results. The
scope interview is resolved: Git approvals remain unchanged, first activation
uses a dedicated dotfiles-ai Worktrunk checkout, and separate same-account logins
are accepted. Dependent slices still require technical qualification evidence.

## Reopened runtime protection decision

Live synthetic qualification demonstrated direct source editing, but an alternate
case spelling of the Git pointer allowed a writable open despite the exact-name
read-only bind. The experiment stopped before changing pointer contents. Runtime
qualification remains failed; the private Cycle Record owns the evidence and
retention state. This reopens only the pointer-protection mechanism. The approved
five-context map, direct-edit requirement and existing Git approval rules remain
unchanged.

The reopened decision now has a specified next experiment: a host-owned immutable
pointer flag on a fresh synthetic fixture, including attempted guest flag removal
and identity-preserving restoration. The runtime feature defines its exact
receipt, operations and outcome rules. This restores implementation readiness for
bounded requalification; the candidate remains unqualified and does not relax
acceptance criteria or authorize real-checkout activation.
Case-sensitive storage is a separate alternative requiring an explicit checkout
location decision. Provider, agent, host-helper and activation slices remain
dependent on successful runtime qualification.

## Promotion and Build handoff

Runtime-qualification scope: source recipes/fixtures/runner/runbook, actual
credential-free disposable runtime probes, retention and explicit cleanup.
Profile: distribution. Risk: elevated. Modules: Python, Security, Cloud. Intended
delivery: feature branch and draft PR, plus bounded disposable setup/operation.
Real Mac activation remains the final dependent slice, not this launch's authority.

The first receipt must carry every changed cross-context Discovery document,
README/Product Intent update and plan, even when successors remain discovering.
This avoids incomplete same-repository import. Use the existing Initiative
import route; no preliminary documentation PR or source reset is needed.

For initial registration, Build must freshly validate publication, committed
authority and receipt, then prepare an explicit Worktrunk checkout at the approved
remote base. Run real begin preflight before presenting scope, risk, delivery
target and launch digest for exact approval. General pilot intent is not a
substitute for that exact launch check.

When a matching runtime cycle is already registered, resume that cycle and its
existing checkout. A failed qualification probe does not require another cycle,
another registration approval or removal of existing work. Preserve the original
approval, imports, commits and failed evidence. Reconcile the affected design,
behavior, contract and tests before a separately identified bounded experiment.
Historical gate evidence does not establish that a revised candidate passed.
The private Cycle Record is authoritative for actual registration and results.

The next technical proof is the host-owned immutable pointer candidate described
in the runtime feature and runbook. It keeps the approved direct-edit requirement,
Git approval rules, provider scope and resource ceilings. Successful pointer
qualification only permits the remaining runtime matrix to proceed; it does not
qualify agent authentication or activate real checkouts. A changed approval scope
or a genuinely new cycle retains the applicable preflight and approval boundary.

Recommended Build primary: current native Codex session, preserving OpenAI
provider affinity and explicit checkout targeting. No session relocation or
manufactured native identity is needed. Root owns integration; bounded helpers
may own disjoint fixture/review work after registration, never independent slices.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary | required: approved context table; who owns each contract? |
| Interaction | required: promotion sequence above; what precedes registration? |
| State | required: delivery table plus manifest; which slice may advance? |
| Data/trust | required: linked provider and host-boundary ownership tables |
| Schema | not_applicable: manifest and existing lifecycle are canonical; no duplicate runtime schema |
| Dependency/deployment | required: delivery/dependency table; what blocks real activation? |
| Quantitative | not_applicable: no measured comparison exists |

**Text Equivalent:** Distribution first qualifies an isolated runtime. Provider
handoff and host Git integration then enable the two client adapters. Both must
succeed before real Mac activation. Existing owners retain credentials, Git and
lifecycle authority. Publication, committed receipt and real preflight precede
separate exact launch approval. Canonical source: this Initiative and its manifest.
Owner: Discovery primary. Change trigger: scope, authority, dependencies or delivery.
