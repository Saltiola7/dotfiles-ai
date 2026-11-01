# OpenShell provider handoff

## Scope and authority

This prospective feature contract belongs to `shell_auth_startup` under the
[OpenShell pilot Initiative](../../../initiatives/openshell-pilot/README.md).
It covers provider bootstrap, credential ownership, refresh, failure, rotation,
revocation and retirement for both Codex subscription access and OpenCode with
Vertex Claude. It supports INT-002, INT-003, INT-008, INT-009, INT-010, INT-017 and
INT-018. The Initiative owns cross-context readiness and delivery authorization.

Status: the operator approved fresh, separate attended sign-ins to the same
existing Codex and Google accounts while preserving ordinary host grants. That
decision settles the bootstrap approach; grant independence, exclusive refresh
ownership and revocation scope remain unqualified. This documentation task does
not perform a sign-in, read an existing credential store, issue a model request
or change a running service. The first provider-evidence slice is specified below
and depends on the Initiative's qualified runtime and controlled trial launch.
The existing
[Engineering Profile](../PROFILE.md) and native launch behavior remain unchanged.
Risk is elevated because the proposed route creates a new credential boundary.

Distribution owns the runtime and gateway boundary. This context owns the
credential handoff contract. The Codex and OpenCode control planes own their
client compatibility, selected provider routes and isolated session stores.
The gateway is the sole refresh owner after an approved bootstrap handoff.
The operator owns provider consent, gateway administration, policy expansion and
revocation decisions. The workload cannot administer its own provider or policy.

## Requirements and retained constraints

1. The completed pilot must support both required routes: Codex subscription
   access and Vertex Claude through OpenCode. Neither an OpenAI API key nor a
   direct Anthropic API key is an acceptable substitute. Failure of one route
   cannot be reported as a completed two-agent pilot.
2. The approved bootstrap uses a fresh, dedicated authorization for each route
   through an attended provider flow. Reusing the same account does not mean
   reusing its existing host grant, credential file, session store or refresh
   token. Account selection and independent grant semantics must be qualified.
3. Bootstrap operates in a private, dedicated credential context owned by the
   trusted gateway side. No normal host authentication store is imported, copied,
   mounted or mutated. Existing host sessions and provider selection survive
   setup, failure, disable and rollback.
4. Reusable credentials, refresh tokens and ADC material remain outside agent
   workloads. Gateway-side request authorization must preserve the selected
   provider and authorized destination without exposing the reusable grant.
   A workload-visible placeholder, if required by the native provider mechanism,
   must be ineffective outside its authorized gateway binding.
5. Gateway ownership includes serialized refresh and atomic adoption of renewed
   credentials. Native clients must not retain another refresh-capable copy or
   independently refresh the same grant. If the native integration requires
   competing refresh owners, the route remains unavailable.
6. Workloads use separate authentication and session state from normal host
   clients and from each other. The gateway must not expose its credential store,
   administrative endpoint or control socket to workload processes. Separate
   directory names alone do not establish this boundary.
7. Shell startup, configuration rendering and ordinary readiness checks never
   start authentication. No ambient 1Password service-account bearer token, host
   ADC override, provider grant or broad inherited secret environment enters an
   agent workload. The existing guest token-forwarding behavior does not authorize
   forwarding that environment into this new route.
8. Authentication material never appears in command arguments, logs, Git,
   ordinary readiness output or shared evidence. Provider browser/device flows
   may present their required material only through the attended private channel;
   prompts, codes, redirect payloads and account details are not captured in
   diagnostic records.
9. A missing, expired, revoked, mismatched or unqualified provider binding blocks
   the affected launch or request. It never selects another account, provider,
   credential source, API-key route or unsandboxed process. Retained work and
   existing host sessions remain intact.

## Behavior

| Given | When | Required result |
|---|---|---|
| No dedicated grant exists | An agent launch or readiness check occurs | Report authentication pending or unavailable without starting a login or reading normal host credentials. |
| The operator approves the dedicated attended flow | Bootstrap begins | Use only the selected private bootstrap context and intended provider route; normal host grants and session stores remain unchanged. |
| A dedicated authorization completes | Handoff is attempted | Activate only after destination binding, exclusive refresh ownership and workload exclusion are verified; otherwise preserve private failure evidence and leave the route unavailable. |
| A Codex subscription binding is selected | The Codex workload requests inference | Use the qualified subscription route through the gateway; no API-key substitution or client-side reusable grant is introduced. |
| A Vertex Claude binding is selected | OpenCode requests inference | Use the qualified Vertex project/location and Claude route through the gateway; missing entitlement or unsupported streaming fails visibly without direct Anthropic fallback. |
| A granted credential approaches renewal | Requests require refresh | The gateway alone refreshes; concurrent requests cannot create competing refresh ownership or expose renewal material. |
| Refresh fails or revocation is observed | A later request or launch occurs | Deny the affected operation, retain work and report a bounded failure class; no silent reauthentication or credential fallback occurs. |
| A workload requests another destination or provider binding | Authorization is evaluated | Deny it unless separately approved policy and provider bindings authorize that exact route; possessing a placeholder grants no wider authority. |
| Workload code reads files, process environments or diagnostics | It searches for authentication material | Gateway grants, normal host credentials and 1Password bearer tokens remain unavailable. |
| The gateway or credential store becomes unavailable | An agent continues or restarts | Fail closed; do not create another store, start a login, use native host credentials or execute outside the sandbox. |
| A replacement grant is proposed | Rotation is evaluated | Preserve the current qualified binding until the replacement is independently qualified, then switch atomically without dual refresh owners. |
| The operator disables the pilot | Local access is disabled | Prevent new workload use of the binding; do not claim provider revocation or delete retained state. |
| Provider revocation is requested | The provider's supported operation completes | Verify the revoked grant no longer authorizes requests; record any account-wide impact and the limits of verification privately. |

## Abstract interfaces

These are ownership and result contracts, not executable command names or claims
that a working OpenShell adapter already exists. Implementation must select and
qualify upstream-supported interfaces before fixing the concrete CLI or schema.

| Interaction | Permitted input | Result and boundary |
|---|---|---|
| Operator to trusted bootstrap | Explicit route selection and attended provider consent | A dedicated private authorization candidate, or a bounded pending/failure result. No normal host grant is used as input. |
| Bootstrap to gateway | The dedicated candidate through a private, qualified native handoff | One gateway-owned provider binding with exclusive refresh ownership. No reusable credential is returned to the workload or ordinary caller. |
| Workload to gateway | An inference request for its authorized provider binding | Provider-authorized forwarding or denial. Request bodies remain private and are not authentication evidence. |
| Gateway to provider | Destination-bound request authorization and gateway-owned renewal | A provider response or classified authorization failure. Renewable grants never return through the workload response. |
| Operator to readiness inspection | Selection of an existing private binding | Bounded route and readiness classifications. Inspection does not log in, refresh through a second owner or print private account/configuration values. |
| Operator to rotation, disable or retirement | Exact binding selection and operation-specific authorization | Bounded result plus privately retained recovery evidence; no implicit deletion, account-wide revocation or host-session mutation. |

Private native bindings may require account, project, endpoint or storage
identifiers. Their concrete representation remains with the native owner and
later qualification; this document creates no duplicate credential registry.
Public evidence contains only route classes, versioned compatibility results and
bounded success/failure outcomes. Logs must redact provider error bodies before
retention rather than assuming successful responses are the only secret source.

## Failure, recovery and retirement

The new route is additive and default-off. Any missing prerequisite, malformed
provider metadata, credential-store ownership failure, inconsistent refresh
ownership or unsupported native interface produces an unavailable result before
workload authorization. Existing native agent launch remains an explicit operator
choice; it is never automatic recovery from OpenShell failure.

Recovery repairs or reauthorizes only the selected dedicated binding. It does not
copy another store, restore an old refresh token without checking provider
validity, reset normal host login state or silently switch accounts. Refresh-token
rotation may invalidate prior material, so filesystem rollback alone is not
proof that authentication is recoverable.

Local disable, credential removal and provider revocation are distinct operations.
Disable blocks new workload access while retaining private recovery state.
Removal deletes only explicitly selected private material after its retention
decision. Revocation uses the provider's supported operation and requires evidence
that the target grant no longer works. If the provider revokes the whole account's
sessions or cannot distinguish grants, that wider impact must be established and
approved before revocation; grant independence is not assumed.

Rotation must demonstrate a single active refresh owner, no workload exposure,
correct destination binding and safe rejection of obsolete credentials. A failed
replacement leaves the old binding usable only if it remains valid and qualified;
otherwise the route stays unavailable. Retirement preserves work, sessions and
bounded private failure evidence until the operator chooses their disposition.

## Provenance, assumptions and unresolved decisions

Research used NVIDIA OpenShell v0.1.6 official provider documentation and its
corresponding upstream examples as the compatibility reference. The Google/Vertex
provider documents gateway-side ADC bootstrap and refresh. That establishes a
candidate upstream capability, not successful integration with this repository's
Vertex Claude selection, streaming behavior or dedicated attended authorization.

The examined Codex subscription example imports existing host authorization.
That example does not satisfy this contract. A fresh, isolated grant handoff with
gateway-only refresh must be qualified independently; no successful substitution
is claimed. Later qualification must record the exact selected release and source
identity in private evidence and recheck changed upstream behavior.

The approved decision is separate attended authorization to the same existing
accounts, without importing or modifying ordinary host grants. Remaining gaps
are empirical qualification questions rather than a pending sign-in preference:

- The concrete subscription handoff must work without importing normal host
  credentials or retaining competing refresh-capable copies.
- Dedicated Vertex bootstrap must preserve the intended account and project
  while keeping ADC inaccessible to workload processes.
- Both providers' independent-grant, rotation and revocation behavior must be
  established, including any impact on existing native host sessions.
- The qualified runtime must enforce separation between gateway credentials and
  workloads across filesystem, process environment, sockets and retained logs.

These gaps block ordinary provider activation, but they are the defined subject
of the first bounded evidence slice after its runtime dependency passes. They
do not authorize a fallback to API keys or a weaker credential boundary. No
authenticated or model request has been performed to satisfy this specification.

## Acceptance and validation

Source validation uses the existing publication/instruction authority, affected
rendering and contract tests, and review of every secret-bearing handoff. Synthetic
fixtures cover rejected host imports, inherited secret environments, wrong
destinations, unsafe private-store ownership, concurrent refresh, expiration,
revocation, interrupted rotation, redaction and failure without fallback.

Real qualification is separate from source completion. Both required routes must
demonstrate the approved dedicated attended bootstrap, gateway-only refresh,
retained native host sessions, inaccessible credentials, isolated client state
and bounded failure. The following ordered protocol defines the first evidence
slice; ordinary agent use remains blocked while a binding is only a candidate.

### Ordered provider-evidence protocol

1. **Admit the exact trial.** Require the Distribution runtime receipt for the
   selected OpenShell release, image, gateway and workload boundary. Confirm the
   concrete native interfaces support the steps below before opening a sign-in.
   Run all request/refresh/failure fixtures with synthetic, nonfunctional grants
   and no provider traffic. Confirm the host preservation probe reports bounded
   native session health without reading or exporting ordinary host credentials.
   A failed runtime receipt, unknown ownership or unsupported interface stops the
   trial with an unavailable result.
2. **Bootstrap the two dedicated candidates.** Conduct the approved attended
   sign-ins in separate private contexts, using the same existing Codex and Google
   accounts. The operator confirms the account shown by the provider's native
   flow privately; record the confirmation class, never the account identity.
   Hand off each candidate to its sole gateway refresh owner. Verify workload
   denial of the gateway store, process secrets, administration and control
   sockets before sending any real inference request. Check ordinary host session
   health again. A login that invalidates ordinary host use fails this contract.
3. **Exercise one synthetic inference request per route.** Use a fixed synthetic
   prompt with no repository content, tools, attachments, memory or external
   retrieval. Codex must use subscription access; OpenCode must use the existing
   Google account's intended Vertex Claude route and demonstrate streamed response
   completion. Confirm the destination and credential-binding class from private
   gateway evidence. A successful answer alone does not establish those facts.
4. **Exercise actual gateway renewal.** Use the provider's supported renewal
   operation, or wait for a real renewal boundary within the controlled trial.
   Do not alter host clocks, rewrite real token expiry fields or manufacture a
   competing refresh client. Verify one gateway owner adopts renewed material and
   then use the second bounded synthetic request for each route. Validate ordinary
   host session health again. A mock expiry test or successful initial login is
   not actual refresh evidence; if renewal cannot be observed, record unavailable
   and retain that route as unqualified.
5. **Restart only the dedicated gateway.** Preserve its private binding state,
   stop and restart the exact trial gateway through its qualified owner, and
   verify workload calls fail closed while it is unavailable. Startup must neither
   import host credentials nor trigger another login. Verify exclusive refresh
   ownership and the unchanged provider binding after restart, then use the third
   and final synthetic request for each route. Normal host clients and unrelated
   services remain untouched. Capture bounded before/after native session health.
6. **Exercise denial and revocation safely.** First run the negative grant fixture
   against the same qualified authorization path with a synthetic rejected grant;
   prove the workload receives denial and cannot fall back. Real provider revoke
   is permitted only when independently established native semantics target the
   dedicated pilot grant alone and the exact narrow operation is authorized in
   the trial. Prove denial through supported non-inference authorization/renewal
   inspection and confirm ordinary host session health. If grant scope is unknown,
   account-wide, or no safe verification interface exists, do not revoke; mark
   actual provider revocation unavailable and retain the negative fixture result
   separately. Dedicated sign-in approval is never broad revocation approval.
7. **Close the evidence trial.** Disable candidate workload access, preserve work
   and private receipts, and classify each matrix row independently for each
   provider. No secret deletion, ordinary host logout, automatic replacement grant
   or promotion follows from completing the experiment. A later approved rotation
   repeats ownership and preservation checks; it cannot reuse an obsolete receipt.

### Request and resource bounds

The evidence trial permits at most three inference requests per required route:
initial handoff, after real refresh, and after gateway restart. Each uses at most
512 input tokens and 128 output tokens, no tools and no autonomous follow-up.
These are experiment caps, not measured costs or provider capabilities. A route
whose qualified native interface cannot enforce the bounds remains unavailable
for real inference until a revised bounded protocol is selected. Disable automatic
retries and stop after the first unexpected provider or authorization failure;
do not spend the remaining allowance trying alternate accounts or models.

Codex uses the existing subscription allowance. Vertex uses the existing account
and project and may incur their normal inference charges; this specification does
not claim a free trial or a currency estimate. No API key, new billing account,
project, quota increase or model purchase is introduced. Each route permits one
initial attended authorization, one supported renewal attempt and one owned
gateway restart during this evidence run. Failed or timed-out authorization is
retained as failed/pending, not automatically retried. The later controlled trial
must declare its bounded wall-clock window; expiry outside that window yields
unavailable refresh evidence rather than an indefinite watcher or extra model call.

### Deterministic evidence matrix

Evaluate every row separately for Codex subscription and OpenCode Vertex Claude.
Use `passed` only for the stated observation, `failed` for a contradictory result,
and `unavailable` for absent prerequisites or unobserved behavior. Preserve the
exact release, source and qualified interface identity privately. Shared results
contain route and check classifications only; no account, endpoint, project,
credential, request body, response body, path or session identity is published.

| Check | Pass condition | Failure or unavailable condition |
|---|---|---|
| Runtime admission | Exact current runtime receipt establishes workload/gateway isolation. | Missing or stale receipt is unavailable; observed boundary escape fails. |
| Attended separate bootstrap | Private account confirmation matches the intended existing account; candidate uses a distinct dedicated store and ordinary host sessions remain healthy. | Host import, wrong account, host-session invalidation or unattended login fails; unsupported dedicated flow is unavailable. |
| Grant ownership | Gateway alone retains refresh-capable material; workload and client cannot read it or administer the binding. | Additional refresh owner, exposed grant or workload control access fails; unobservable ownership is unavailable. |
| Route and streaming | One bounded synthetic request completes through the exact required route; Vertex response completes through its streaming path. | Provider substitution, excess requests or route mismatch fails; unsupported streaming or unenforceable caps is unavailable. |
| Actual refresh | One gateway renewal is observed, the post-renewal bounded request succeeds, and ordinary host sessions remain healthy. | Competing refresh, host invalidation or renewal failure fails; no actual renewal evidence is unavailable. |
| Gateway restart | Calls deny during outage; exact owned restart restores the existing private binding without login/import, and the final bounded request succeeds. | Fallback, lost ownership, host mutation or unexpected login fails; unsupported restart observation is unavailable. |
| Negative grant fixture | Synthetic rejection traverses the qualified authorization path and denies use without fallback or secret output. | Authorization despite rejection, fallback or exposed material fails; a fixture that bypasses the real decision path is unavailable. |
| Actual narrow revocation | Independently proven grant-scoped, authorized revoke causes denial through a supported non-inference check while host sessions stay healthy. | Account-wide effect or continued authorization fails; unknown revoke scope or unsafe verification is unavailable and no revoke is attempted. |
| Privacy and host preservation | All trial stages retain workload exclusion, bounded secret-free diagnostics and ordinary host session health. | Secret output, ordinary host grant mutation or session invalidation fails; insufficient observation is unavailable. |

### Completion and promotion

The first evidence slice is ready to execute once its exact runtime dependency
passes and the controlled trial binds the concrete supported interfaces and
wall-clock window. The approved separate-login decision needs no repeated
preference question. The slice may finish with an honest failed or unavailable
finding; finishing an investigation does not make a provider ready.

Source promotion requires the existing affected gates and publication review.
Provider activation additionally requires every non-revocation matrix row to
pass for both routes, current runtime evidence, isolated client/session state,
bounded operational recovery and the Initiative's joint readiness review. Actual
narrow revocation must pass or remain explicitly unavailable under a separately
approved Gate Exception describing retention, local disable, owner and review
condition. The negative fixture cannot silently replace that proof. No exception
is created by this document. A failure in credential isolation, refresh ownership,
route preservation or ordinary host-grant preservation blocks promotion rather
than being treated as a narrower successful pilot.

Negative probes must show that a workload cannot read the gateway grant, obtain
the normal host grant, reuse a placeholder outside its binding, administer policy,
or continue inference through another credential source after revocation. No
credential values enter the acceptance output. Mock success, configuration
rendering and generic upstream support cannot replace those runtime results.

The Initiative owns the combined Gate Ledger and exact applicability plan.
Provider source completion and runtime qualification remain distinct; the
existing Engineering Profile is not broadened by this proposal.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | required: ownership table below; who may bootstrap, retain, refresh and use a provider grant? |
| Interaction | required: abstract-interface table and ordered provider-evidence protocol above; which handoffs may carry private authorization material, and in what order are bootstrap, renewal, restart and safe denial qualified? |
| State | required: transition table below; when may a provider route authorize requests, and what happens on failure? |
| Data/trust | required: ownership table and abstract-interface table; can reusable credentials or broad host authority enter a workload? |
| Schema | not_applicable: this feature creates no persistent credential schema; native provider ownership and concrete qualification precede any interface schema. |
| Dependency/deployment | required: dependency table below; which runtime and control-plane boundaries must be qualified together? |
| Quantitative | not_applicable: request/resource bounds are declared experiment limits, not measured costs, performance, reliability or comparative evidence; no chart would add evidence. |

### Ownership and trust boundary

| Actor or surface | Authorized responsibility | Excluded authority |
|---|---|---|
| Operator | Approve attended bootstrap, exact account selection, policy changes and retirement | Approval is not inferred from a workload request or elapsed time. |
| Trusted bootstrap | Obtain a dedicated authorization through the approved private flow and hand it to the gateway | Importing normal host grants or retaining a competing refresh-capable copy after handoff. |
| Gateway | Hold the dedicated grant, bind destinations, authorize requests and perform all refresh | Exposing reusable grants or administrative access to workloads. |
| Agent workload | Use its authorized inference route and isolated client/session state | Provider administration, credential-store access, host token inheritance or independent refresh. |
| Existing native host clients | Continue using their existing independent state and explicit native launches | Becoming an automatic fallback or supplying credentials to the new route. |

**Text Equivalent:** The operator controls authorization and policy. Trusted
bootstrap obtains only the approved dedicated grant. The gateway becomes its sole
refresh owner and authorizes only destination-bound requests. Workloads receive no
reusable credential or administration authority. Existing native clients retain
their independent state and cannot supply a fallback grant. Canonical source:
requirements and abstract interfaces in this file. Owner: Shell Auth maintainer.
Change trigger: credential source, handoff, refresh owner or exposed surface changes.

### Provider route transitions

| Current state | Event and guard | Next state and effect |
|---|---|---|
| Disabled | Operator selects the approved pilot route | Authentication pending; no automatic sign-in. |
| Authentication pending | Operator completes the approved dedicated attended bootstrap | Candidate; ordinary requests remain blocked; only the bounded qualification protocol may issue its declared synthetic requests. |
| Candidate | Binding, refresh ownership and isolation qualification pass | Ready; authorize only the selected route. |
| Ready | Gateway renewal succeeds with unchanged qualified ownership and binding | Ready; adopt renewed material atomically. |
| Candidate or Ready | Qualification, refresh, binding or store validation fails | Unavailable; deny affected requests and retain work. |
| Ready or Unavailable | Operator disables local use | Disabled; retained credentials are not claimed revoked. |
| Unavailable or Disabled | Approved reauthorization produces a new candidate | Candidate; repeat qualification rather than restoring readiness by assertion. |
| Any retained grant state | Approved provider revocation is confirmed | Revoked; deny use and retain only approved private recovery evidence. |

**Text Equivalent:** Readiness requires dedicated authorization plus actual binding,
refresh and isolation qualification. The gateway may renew a ready binding without
changing its owner. Failure makes the route unavailable. Disable blocks local use
without claiming revocation. Reauthorization returns to candidate status. Confirmed
revocation blocks use regardless of prior readiness. These are conceptual contract
states, not a new runtime database. Canonical source: behavior and failure contracts
in this file. Owner: Shell Auth maintainer. Change trigger: readiness guard,
renewal, recovery, disable or revocation behavior changes.

### Qualification dependencies

| Owner | Required contribution | Dependent surface |
|---|---|---|
| Distribution | Qualified runtime, private gateway boundary and workload isolation | Both provider bindings and their private storage. |
| Shell Auth | Approved bootstrap, sole refresh ownership, failure and retirement contract | Codex subscription and OpenCode Vertex authorization. |
| Codex control plane | Qualified native subscription client behavior and separate session state | Completed Codex pilot route. |
| OpenCode control plane | Qualified Vertex Claude routing, streaming and separate service/session state | Completed OpenCode pilot route. |
| Initiative primary | Combined evidence and unresolved-decision review | Joint pilot readiness; one working route is insufficient. |

**Text Equivalent:** Distribution establishes the runtime boundary. Shell Auth
qualifies grants and refresh within that boundary. Each control plane qualifies
its own native client and isolated state. The Initiative requires both routes
before joint readiness. Canonical source: Initiative context map and this feature's
scope. Owner: Discovery primary with the affected context maintainers. Change
trigger: runtime topology, ownership, provider support or delivery dependency change.

**Interaction Text Equivalent:** Operator consent starts private bootstrap; the
dedicated candidate moves to the gateway through a qualified native handoff.
Workload inference requests use only their authorized binding. The gateway alone
authorizes and renews with the provider. Qualification orders runtime admission,
separate attended bootstrap, one initial synthetic request, actual renewal and
its request, then an owned gateway restart and its request. Synthetic denial is
always exercised; actual revoke requires proven narrow scope and exact consent.
Unknown revoke scope produces unavailable evidence without a revoke attempt.
Readiness inspection returns bounded classifications; rotation and retirement
remain exact operator-selected actions. Canonical source: abstract-interface
table and ordered qualification protocol. Owner: Shell Auth maintainer. Change
trigger: any handoff input, result, ordering, trial bound or credential-visibility
change.
