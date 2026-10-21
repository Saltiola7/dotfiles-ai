# Forgejo lifecycle support

> **Explicit local-only scope amendment, 2026-10-21:** The operator approved
> implementing local private-cycle registration first, with reviewed manual
> delivery as a separate explicit Git operation. The normative contract for that
> bounded, critical-risk slice is [forgejo-local-registration.md](forgejo-local-registration.md).
> It permits controlled read-only Git fetches during registration and local
> completion without network activity. It enables no Forgejo draft, push, merge,
> release, deployment or automatic integration operation. Existing GitHub
> behavior is unchanged. The complete remote-automation outcome and its unresolved
> principal, producer, server-safety and hosting contracts remain blocked below.
>
> Statements below that withhold a reduced release or require full safety before
> implementation continue to govern the complete remote-automation scope; the
> explicit exception above governs only the linked local-only slice. The proposed
> remote interfaces below are retained design history, not enabled capabilities.
> In particular, schema 6 is now specified by the linked slice for local-only
> records; a future remote record contract must be reconciled and versioned before
> activation. Existing failed qualification evidence is preserved, not promoted.

**Proposed Discovery specification; automatic-integration readiness blocked.** This
feature extends the existing `dbsctr_v3_lifecycle` context. The accountable owner
is the dotfiles maintainer. The Engineering Profile remains
[../PROFILE.md](../PROFILE.md); the affected modules are Python and Security.

The complete scope is **critical risk** because automatic integration crosses an
authorization boundary and changes protected repository history. Registration and
draft delivery alone form an elevated-risk subset; this does not lower the
complete cycle's risk. The delivery intent is a reviewed support pull request,
merge, and managed installation on the operator's current computer. Discovery
does not authorize implementation, credential creation, repository mutation,
merge, installation, or a lifecycle registration.

## Problem, desired outcome, and scope

Current registration and draft delivery identify repositories through GitHub
origins and an explicitly selected GitHub account. A private Forgejo repository
cannot use those paths. A project exception would leave this provider limitation
in place. The desired outcome is reusable Forgejo support in the existing DBSCTR
helper and skills, while preserving existing GitHub behavior and safety.

The support covers provider-aware repository registration, Initiative authority,
explicit credential enrollment and resolution, feature-branch delivery, verified
draft pull requests, and automatic integration under the existing DBSCTR
approval, policy, validation, and preservation contracts. The first runtime
qualification is limited to one existing private Forgejo instance and one
operator-selected consumer. This qualification is not a claim that arbitrary
Forgejo deployments, versions, authentication methods, or other forges work.

The support change itself must reach a reviewed pull request and merge before
the updated managed DBSCTR distribution is installed on the current computer.
No consumer application deployment automation, remote DBSCTR installation,
Forgejo server upgrade, runner installation, existing repository migration,
credential migration, or unrelated provider support is included. The consumer
continues to own its source, CI policy, required checks, and deployment process.
Forgejo pipeline, autonomous claim and workflow-feedback parity are excluded.
Existing governed local telemetry may record sanitized operation results; it is
not remote publication or delivery authority. This remains one bounded context.

The operator additionally approved fixture-only server-side guard qualification.
This permits the isolated candidate described below, not DBSCTR product
implementation or production server protection. Preserve generated built-in hooks,
global configuration, service configuration and the server binary. No shared hook
manager, consumer change or managed DBSCTR installation is included. Durable
production hosting changes remain owned by the Git-hosting context and require
their own delivery authority.

## Facts, settled decisions, and activation prerequisites

### Source-backed facts

- The current helper parses GitHub-only origin identities through
  `github_repository_from_url` and `git_repository_slug`. Initiative manifest
  schema 1 uses bare `owner/repository` identities. New Cycle Records currently
  use schema 5 and retain `delivery.github` account/repository metadata.
- Existing launch preflight binds source artifacts, target/base, checkout, plan,
  repository, and delivery/account inputs to a launch digest, and checks them
  again before registration. Final Push checks the recorded remote destination.
- GitHub draft delivery resolves the recorded account just in time and performs
  feature-branch delivery without changing the global active account. Those
  behaviors are compatibility requirements.
- The first Forgejo instance's provisioning source pins native Forgejo
  **15.0.10 LTS**, and its authenticated web interface reports **15.0.10**.
  Authenticated API reads report **15.0.10+gitea-1.22.0** and verify the selected
  account/repository relationship. Anonymous version/settings requests returned
  HTTP 403. Version and successful reads do not establish merge safety.
- A read-only checksum inspection of the deployed native binary through the
  existing pinned SSH trust matched the previously pinned official ARM64
  v15.0.10 release SHA-256:
  `be06bb887bef8a7901c6bdcea36023e55429ef7582a2797711b878a3af602e69`.
  This binds the inspected binary to the release under source analysis; the
  match alone does not qualify merge safety.
- A read-only discovery credential is enrolled in native macOS Keychain and its
  exact account/repository lookup has been verified without exposing its value.
  It grants repository, account and API metadata reads, with no write/admin
  scopes; a read-only administrator-API negative check returned HTTP 403.
  The current computer has no `fj` or `tea` client. The selected implementation route is
  direct Forgejo REST through the existing Python standard library, with no new
  dependency. Initial private credentials use the current computer's native
  macOS Keychain and existing `osxkeychain` helper.
- A read-only Git remote inspection over existing SSH succeeded from the current
  computer. It does not prove owner API authentication, HTTPS Git authentication,
  write permission, or automatic-merge safety.
- The operator selected **DBSCTR gates and the project test suite** as required
  validation before consumer merges. The consumer currently contains a README
  and has no declared suite or CI. Hosted CI is not required by this decision,
  but a committed project-selected validation authority and real suite are
  activation prerequisites. An empty check set cannot satisfy them.
- Authenticated inspection finds no branch-protection rules for the first
  consumer and an unprotected default branch. Its current commit-status response
  has an empty state, null status list and reported total zero. These are absent
  validation evidence, not successful tests. The enrolled discovery account is
  an instance administrator; it is not a qualified ordinary merge actor.
- The inspected API schema exposes a native expected-head merge guard and no
  expected-base field. Head guarding alone cannot close the target-base race.

Private deployment names, account names, repository identities, endpoint
bindings, machine paths, credentials, and raw API responses are intentionally
absent from this public specification. First-host observations belong only to
the repository's governed local evidence boundary.

### Isolated qualification observations and outcome

The historical native-only run retained **five synthetic PRs and three ordinary
non-administrator merges**: the baseline, one competing-merge winner, and the
fresh expected-head control. The actor was independently verified as restricted
and non-administrative. Fixture credential/role binding, branch policy and denied
administrator/consumer access were observed; final policy was unchanged and no
write outcome remained unresolved. These are fixture-only results, not production
credential enrollment, a real consumer test suite or a trusted producer contract.

| Case | Bounded native observation | What the observation establishes |
|---|---|---|
| Draft fixture | With two successful synthetic required contexts and official approval, merge returned HTTP 405 and the protected base was unchanged. Native draft state was true and `mergeable=false`. | This draft fixture was refused. No error-reason category was retained, so do not attribute the response exclusively to a particular server guard. |
| Controlled draft promotion | Removing the recorded WIP title prefix produced native `draft=false`. | The observed sequential promotion worked; concurrent title-preservation and generic draft configuration are not proven. |
| Missing required checks | With fresh official approval, merge returned HTTP 405 with a status/check reason. | Missing synthetic required evidence did not authorize that merge. |
| Failing required context | One failed and one successful synthetic context produced HTTP 405; the protected base was unchanged. | A failed required context did not authorize that merge. |
| Status pagination | With `limit=1`, the first combined-status page reported `state=success` while the second required context failed. `X-Total-Count` was 2 and the JSON total was page-local at 1. | A successful first page and its JSON total cannot establish complete successful required evidence. |
| Eligible baseline | The ordinary actor merged the fully eligible baseline; the merge's ordered parents were exactly the approved base `A` and head `H`. | The allowed ordinary-merge path worked for that fixed base/head. |
| First stale-head attempt | The first attempt was confounded by an official review that was found dismissed; its exact dismissal timing relative to the request was not established. | Preserve this inconclusive attempt; it earns no expected-head guard credit. |
| Fresh expected-head control | After native head preparation and independent active official-review readback, the old expected head returned HTTP 409 with a head-related reason and unchanged base. The matching head returned HTTP 200 and merged with ordered parents `(A, H)`. | The fresh control exercised expected-head rejection and its matching-head positive path. It does not close the base race. |
| Competing merges | Two PRs shared base `A`; each head had sole parent `A`, green synthetic required contexts and exact approval. Request intervals overlapped. Responses were HTTP 409 and HTTP 200; only one merged, with exact parents `(A, H)`. | No stale-base counterexample was observed. The conflict reason and the internal critical-interval schedule were not established; this is not proof of an outdated-branch guard or atomicity. |

The native-only qualification outcome remains **UNQUALIFIED**. Neither a stale-base counterexample
nor an independent atomic guarantee was established. No deterministic schedule
spanned the initial protection check and native base fetch, and overlapping
requests cannot prove that internal ordering. The evidence cycle's qualification
acceptance gate is failed because the required guarantee remains unqualified;
this is not a claim of an observed unsafe merge or a passing safety qualification.

No production provider implementation, managed installation, consumer write,
scope waiver or weakened safeguard followed from the run. The fixture resources
and evidence remain retained pending separately authorized cleanup. Production
selected-principal proof and producer/attestation interfaces remain unresolved.

### Completed fixture-guard qualification

The expanded guard run qualified a **bounded synthetic exact-object predicate
and native ref compare-and-swap** for the single fixed fixture repository's
ordinary REST merge path, under trusted operating-system, installed-guard and
immutable-grant assumptions. It does not change the historical native-only
unqualified result or establish production integration readiness.

| Case | Observed result | Qualified limit |
|---|---|---|
| Guard admission negative | An ordinary REST merge without a grant returned HTTP 409 with custom-guard authority denial; the base was unchanged. | Missing trusted fixture authority was refused on the exercised path. |
| Exact-grant positive | The same narrow path with an exact grant returned HTTP 200. Native raw merge parents were `[A, H]` and raw tree was `T`. | The ordinary REST path admitted the granted repository/ref/base/head/tree predicate. |
| Deterministic live overlap | The first hook validated `(A, H, T)` and reached the post-validation barrier before exit. Before release, a second fully authorized ordinary PR returned HTTP 200 and advanced `A` to `B`, with raw parents `[A, C]` and tree `T_C`. After release the first hook admitted its predicate, but native REST returned HTTP 409; ref `B` remained and the first PR was unmerged. | Actual barrier ordering and native outcomes establish stale-ref exclusion after successful guard validation for this fixture path, rather than infer it from overlapping request times. |
| Harness and installation | All 31 local bare-repository cases passed; the same 31 cases passed on deployed Git 2.56/Python 3.14, including the symbolic-ref alias negative. The installed guard identity was independently reviewed; generated hooks were unchanged and no service/global configuration changed. | These results bind the exercised guard and native runtime; they do not prove all production writers or absent/non-executable-hook health. |

Across both stages, **eight fixture PRs and five ordinary non-administrator
merges** are retained: the prior three merges plus the two successful guarded
merges. All resources and evidence remain retained. No consumer write, DBSCTR
product implementation or managed product installation occurred.

The selected v15 full-commit API representation's nested `tree.sha` reported the
head commit ID rather than raw tree `T`; see
[native commit conversion](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/convert/git_commit.go#L174).
Grant verification therefore uses raw Git object IDs and raw parent/tree headers,
not that API tree field. The native comparison is also source-bound to
[Git 2.56 receive-pack ref transactions](https://github.com/git/git/blob/v2.56.0/builtin/receive-pack.c#L1635)
and [locked old-value comparison](https://github.com/git/git/blob/v2.56.0/refs/files-backend.c#L2819).

This qualification assumes that the trusted filesystem, exact executable guard,
immutable synthetic grants and supported dispatcher remain intact. Production
principal/producer interfaces, admission-grant expiry/revocation semantics,
installation health and durable hosting ownership remain unresolved. It is not
a qualification of all writer paths, automatic merge orchestration, atomic
wall-clock revocation through commit, or a production attestation service.

### Settled rollout decisions and remaining Build proofs

| Concern | Decision and required proof |
|---|---|
| Private credential source | Use native macOS Keychain through `osxkeychain`, scoped to the exact HTTPS origin, account and repository path. Enrollment uses a private native interface with hidden CLI credential entry; no GUI is required. Build must prove exact lookup/account isolation and permission-negative behavior; no arbitrary secret command or alternate store is authorized. |
| Consumer required checks | Require committed project-selected DBSCTR gate and test-suite authority with exact head/base evidence. The consumer owner must declare a real suite and trusted producer/definition identities before activation. Do not invent ceremonial tests, demand hosted CI, or change the consumer during this Discovery. Missing/empty evidence remains blocked. |
| Runtime capability and permissions | Bounded fixture observations on 15.0.10+gitea-1.22.0 cover ordinary actor/role binding, negative access, sequential draft promotion, draft-fixture refusal, missing/failing required evidence, pagination and expected-head control. Native-only current-base safety remains unqualified. The additional exact-object guard plus Git 2.56 ref comparison is qualified only for the exercised synthetic REST path. Production principal/producer proof, HTTPS Git account binding, concurrent title safety, loaded guard health and hosting interfaces still block implementation readiness. Other versions remain unsupported until qualified. |

**Material readiness blocker:** The qualified fixture guard has no production
authority, loaded-health or durable hosting interface yet. Native-only v15 policy
still cannot supply the required guarantee: its outdated-branch protection
consults persisted `CommitsBehind`, which is updated asynchronously after base
pushes; its presence alone does not prove an atomic current-base guarantee.
Protection-policy inspection also requires repository-administrator permission,
and native administrative merge behavior can bypass protection depending on
instance/repository administrator status and `apply_to_admins`. Ordinary selected
account use must establish the effective enforced path without an admin bypass.

Before declaring the complete automatic-integration scope implementation-ready,
name and qualify an adequate guarded server interface/policy or obtain an
explicit user deferral of automatic integration. A client reread, local lock,
head guard, status report, or manually supplied JSON does not close the race.
Fast-forward-only merging is not an implicit alternative to the existing
merge-commit contract. Qualification combines source/semantic proof and controlled
tests; passing a timing stress test alone cannot prove atomicity. No deferral or
safeguard waiver is granted here.

The selected Python REST route has the bounded fixture results above. Those
observations do not establish authenticated HTTPS Git account binding, production
operation eligibility or the missing atomic current-base guarantee.

The operator requires automatic merge in the delivered outcome and selected
native safety qualification **before implementation**. Registration and draft
delivery are not an implicitly approved reduced release. Discovery therefore
retains the current-base safeguard as a material readiness blocker; it cannot
move that unresolved guarantee into a post-implementation activation checklist.

## Domain and ownership

| Term | Meaning and owner |
|---|---|
| Forge identity | Provider plus normalized HTTPS origin, including any non-default API port, and canonical `owner/repository`; lifecycle-owned identity contract, with instance bindings private. |
| Explicit account | Non-secret identifier selecting one account's private credential source; never inferred from an active CLI login, browser session, Git author, or repository owner. |
| Credential source | Native macOS Keychain through `osxkeychain` for the first rollout, resolving an exact origin/account/repository credential just in time. It owns secret storage and revocation; DBSCTR owns selection and use. |
| Qualified capability | An operation and its safety properties verified for the selected instance/version/account, with fresh enough evidence for its use; not a generic Forgejo claim. |
| Draft representation | The instance's configured draft-title prefix and native draft response, interpreted together and verified after create or reuse. |
| Integration authority | Existing exact-repository delivery policy or exact approved recommendation/checkpoint, together with trusted affected-check evidence and native server protection. |
| Qualification consumer | The single private repository selected for initial runtime proof; it grants no authority over other repositories or its deployment. |
| Fixture guard | An independent executable in the fixture repository's supported `pre-receive.d` chain; it adds an exact-object assertion without replacing generated native protection. |
| Synthetic grant | An immutable operator-controlled fixture record binding native repository/actor/PR database IDs, protected ref, approved base `A`, head `H`, tested tree `T`, `synthetic:true` and admission expiry. Trusted fixture configuration binds the repository ID to full forge identity and repository path. This is not a production producer or consent interface. |
| Guard installation identity | Captured dispatcher/guard bytes, executable state and ownership used to bind fixture evidence and exact restoration. |

DBSCTR owns lifecycle state, provider adaptation, identity checks, gate evidence,
and exact delivery decisions. Forgejo owns authentication, repository permissions,
PR state, merge execution, and branch protection. The external credential source
owns stored secrets. The consumer owner supplies required-check definitions and
producer trust. Bounded helpers may inspect and report; the primary retains
approval, gate, registration, integration, and deployment authority.
For expanded qualification, the trusted filesystem operator owns guard/grant
material independently of the ordinary API merge actor. Git's native ref-update
comparison owns final concurrent-update exclusion. Neither owner is replaced by
API permission metadata. No durable shared server manager is introduced.

## Behavior

| Given | When | Then |
|---|---|---|
| A selected Forgejo repository and explicit private provider/account configuration | Registration preflight runs | Resolve full provider/host/repository identity, validate fetch/push destinations and supported capability, and present the exact bound plan without creating a cycle. |
| Two repositories have the same `owner/repository` on different hosts or providers | Authority is compared | Treat them as different repositories; neither receipt, approval, lock nor credential selection matches by slug alone. |
| A legacy GitHub manifest or Cycle Record | The updated helper reads it | Preserve its original GitHub semantics and digest behavior without implicit migration or new automation authority. |
| No selected credential exists, enrollment is incomplete, or the account is wrong | An authenticated operation is requested | Block with a bounded non-secret diagnostic; do not select an ambient identity or repeat alternate-account attempts. |
| A valid approved launch | Provider, host, account, remote, base, plan or source changes before registration | Reject the stale launch and require fresh preflight and approval. |
| A feature branch is ready for draft delivery | Final Push runs | Revalidate recorded identity and gate evidence, push only the feature branch, then create or reuse exactly one matching open draft PR and verify its response. |
| Historical closed/merged PRs and multiple lookup pages exist | Matching PRs are enumerated | Read every page within declared bounds, ignore historical terminal PRs for open selection, and block incomplete or ambiguous results. |
| Draft prefixes are instance-configurable | A draft PR is created or reused | Use the qualified configured representation and verify returned draft/title, repository, head, base, state and URL; never infer draft from a guessed prefix. |
| An exact-repository automatic-integration policy or checkpoint covers a PR | Merge eligibility is evaluated | Apply the existing strict intent, approval, affected-check, base-freshness, merge, and preservation contracts before requesting a merge. |
| Required checks are missing, empty, untrusted or non-successful | Merge eligibility is evaluated | Remain blocked; no degraded validation, administrator bypass, or relabeling as success. |
| Expected-head protection exists but current-base safety is unproven | A merge is considered | Block until an independently qualified allowed server policy guarantees current-base validation across the request. |
| A response is lost after PR creation or merge submission | The operation is retried | Query the exact remote state first; verify the outcome or retain an uncertain blocker rather than issue a duplicate mutation. |
| The support PR is merged and managed installation is approved | Delivery completes | Install only the merged support revision on the current computer, verify loaded behavior, and record actual installation evidence. Consumer deployment is unchanged. |
| An exact unexpired synthetic grant and matching protected-ref update | The fixture guard inspects the full receive batch | Accept only incoming old `A`, raw merge parents exactly `[A, H]` and raw tree exactly `T`; native protection still applies. |
| Missing, ambiguous, expired, malformed or mismatched grant/object/ref data | The fixture guard runs | Reject the batch without changing the target; no permissive override or API-actor grant replacement. |
| Guard validation completed for old base `A` | A controlled pause permits another ordinary PR to advance the target to `B` before the guard returns | After resumption, native ref comparison must reject the stale update; observed overlap alone earns no credit. |
| The guard or dispatcher is missing, non-executable or unexpectedly changed | Qualification health/coverage is checked | Keep qualification blocked until every supported write path and exact loaded installation are established; no closure is inferred from a successful guarded request. |

## Interfaces and compatibility contracts

### Provider and repository identity

The proposed repository identity is `{provider, origin, repository}`. `provider`
distinguishes `github` and `forgejo`; it is never guessed from branding or a
non-GitHub origin. `origin` is a normalized HTTPS origin including any non-default
API port, with no trailing slash or path. `repository` is a validated canonical
owner/repository.
The selected account and credential-source identity are private delivery inputs,
not public Initiative manifest fields or part of reusable public examples.

Origin normalization must be deterministic: require HTTPS, validate the hostname
and optional port, lowercase DNS names, omit the default HTTPS port, and reject
embedded credentials, paths, query/fragment data, control characters, malformed
authorities, and unsupported endpoint forms. Do not broaden existing GitHub
acceptance while adding Forgejo. Repository comparison follows the qualified
provider's canonical rules; do not inherit GitHub case assumptions without
evidence. Unsupported subpath deployments and transport mappings fail explicitly
rather than being silently rewritten.

Origin, upstream fetch URL, every effective push destination, API repository,
returned clone identity, and selected PR must resolve to the same approved forge
identity. A different SSH transport port is not the API port. Explicit private
mapping is required where canonical API and Git transports differ. A redirect,
URL rewrite, rename, transfer, default change, or host change cannot silently
retarget an existing approval or credential.

The initial selected Git path is canonical HTTPS with explicitly selected
account credentials, extending existing GitHub account isolation. This requires
runtime qualification. Existing SSH clone access or a temporary probe identity
does not prove this path works. SSH origins may establish repository identity
only through validated explicit API/transport mapping; authenticated operations
for this rollout use canonical HTTPS. Ambient SSH agents and credential helpers
are not fallback authority. A later authenticated SSH adapter needs separately
specified and qualified account/key and host-trust binding.

### Proposed CLI contract

These options are **proposed interfaces, not installed runtime capabilities**.
Preserve current `--github-account` and `--github-repository` options and their
GitHub-only behavior unchanged. Add the following Forgejo registration family:

| Option | Contract |
|---|---|
| `--forge-provider forgejo` | Explicit provider selection; no automatic inference from a non-GitHub host. |
| `--forge-origin HTTPS_ORIGIN` | Required canonical HTTPS origin, validated as above. |
| `--forge-account ACCOUNT` | Required non-secret explicit account selecting the native private credential. |
| `--forge-repository OWNER/REPOSITORY` | Required canonical repository; verify it against the selected origin, account and Git endpoints. No implicit derivation in the first Forgejo interface. |

Reject mixing the Forgejo and GitHub flag families, missing required selections,
unknown providers, and ambiguous identities before network mutation. The same
selection must drive preflight, registration and Final Push. Final Push consumes
the recorded selection; it cannot silently switch account or credential source.

### Lifecycle records, Initiative authority, and digests

The following **proposed versioned interfaces are not implemented**. They extend
the existing owners rather than introducing another state engine:

| Owner/version | Proposed provider-bearing interface |
|---|---|
| Forgejo Cycle Record schema 6 | Keep existing lifecycle fields and add `delivery.forge` with exact fields `{provider, origin, repository, account, credential_source}`. `provider` is `forgejo`; `credential_source` is `osxkeychain` for this rollout. Do not also write `delivery.github`. New reads/mutations validate the entire provider object. |
| Existing GitHub Cycle Record schema 5 | Keep its serialized `delivery.github` shape and behavior unchanged. Historical supported records remain readable without rewriting. |
| Initiative manifest schema 2 | Replace `coordinator_repository` and each context's `repository` string with typed `{provider, origin, repository}` identity. Retain existing statement/slice/dependency/artifact rules. Accounts and credentials are absent. |
| Initiative receipt schema 2 | Carry typed coordinator/target repository identities, preserving committed manifest/artifact provenance and requirement/dependency coverage. |
| Exact-repository delivery policy schema 2 | Extend the existing one-table delivery owner with typed `forge` repository identity plus private `account` and `credential_source` selection. Preserve existing enablement, exact targets, role, mapping, checkpoint and preservation restrictions. Forgejo administrator bypass is unavailable. |
| Affected mapping schema 2 | Preserve closure/path/definition rules, make `provider_repository` typed, and replace the GitHub-only `github_app_id` field with explicit provider-tagged producer authority. Check evidence gains the corresponding versioned producer/definition and local-or-native execution binding; arbitrary context names or self-asserted producer strings cannot establish trust. |

The complete producer/evidence adaptation must reconcile the GitHub-specific
fields in [workflow-integration-ci.md](workflow-integration-ci.md). A local
DBSCTR/test execution needs an owned evidence envelope bound to the exact trusted
authority, definition and head/base/tested object. Native evidence needs qualified
native producer/run identities. Neither representation supplies native current-base
protection by itself. Discovery owns the remaining concrete producer field shapes
and execution-attestation contract, which must be frozen after capability
qualification and before implementation readiness. These are unresolved normative
interfaces, not implementation choices delegated to Build. Inability to preserve
the canonical trust contract keeps readiness blocked instead of inventing weaker
evidence.

Old helpers supporting at most Cycle Record schema 5 must reject schema 6 before
mutation. Old manifest/policy/mapping readers must likewise reject the proposed
new versions. Capability detection is required before importing provider-bearing
authority into an installed helper that cannot understand it. Existing GitHub
policy/mapping schema 1 remains valid and unchanged. A repository has one active
policy authority; explicit migration cannot leave both old and new authorities
enabled or grant automation implicitly.

Legacy bare manifest repository strings mean GitHub on `github.com` only. Keep
their original canonicalization and digest semantics, and read historical
records without rewriting them. No origin-dependent default can reinterpret old
authority as Forgejo. Any explicit migration retains original authority and is
not automatic enrollment or integration consent.

Repository equality, registration occupancy, delivery locks, Initiative context
homes/receipts, expected-repository comparison, resume checks, recommendations,
check evidence, and PR links must use the full identity. Provider-neutral command
inputs must preserve existing GitHub flags/behavior through an explicit
compatibility path; ambiguous mixed legacy/new inputs fail before network use.
Delivery lock identity binds provider, origin, repository and target ref, not the
credential account; two accounts delivering to the same target contend on one
lock.

Launch digests bind the provider identity, private account and credential-source
identifier, exact upstream/fetch/push destinations, target/base, source receipt,
artifact closure, applicability plan, and cycle arguments. Credentials themselves
never enter a digest or record. Registration rechecks these identities after
approval; Final Push rechecks the recorded destination and selected account.
Changing account or store selection requires fresh authority, not silent fallback.

### Fixture-only pre-receive guard contract

This is the exercised fixture contract; the bounded results and their limits are
recorded above. It is not a production trust interface. Use one independent executable in the supported
`pre-receive.d` chain of the retained fixture repository. Do not replace, reorder,
disable or edit generated built-in hooks. Do not change global hook settings,
the service, server binary or other repositories. Capture the original chain and
the installed candidate's bytes, ownership and executable state before execution;
preserve exact recovery material and resources pending separately authorized
cleanup. A required wider change reopens scope rather than becoming an implicit
prerequisite.

The fixture's synthetic grant has exact physical fields
`{schema_version:1, repository_id, ref, base, head, tested_tree, actor_id, pull_request_id, synthetic:true, expires_at}`.
Repository, actor and PR IDs are validated native database IDs; the PR ID is not
its visible repository-local PR number. Ref is the exact protected branch; object
identifiers are full validated native object IDs; expiry is integer UTC epoch
seconds. Trusted fixture configuration binds `repository_id` to independently
captured full typed forge identity and repository path. It also defines the
permitted ordinary actor and fixture target. This physical fixture schema does
not freeze the unresolved production serialized identity/producer interface. The
operator-owned grant is immutable for its test and unavailable for alteration or
replacement by the API actor or repository content. Reject unknown versions,
unknown/duplicate fields, invalid or ambiguous selection, wrong repository/ref,
missing data and expired grants. Synthetic grants establish only fixture inputs;
they neither qualify production producer trust nor waive existing review, status,
permission or consent requirements.

For a protected update, require Forgejo's native inherited `GITEA_REPO_ID`,
`GITEA_PUSHER_ID` and `GITEA_PR_ID` to match the configured/granted repository,
ordinary actor and PR database IDs, and require
`GITEA_PUSH_TRIGGER=pr-merge-to-base`. Missing, malformed or mismatched native
bindings reject the update. This scope is the native REST merge-to-base path;
the environment binding does not establish a general production principal-proof
interface or authorize another writer path.

Parse the complete incoming update batch before a decision. Reject malformed
input and every incoming symbolic ref, including feature-only batches, before
any unprotected-only early return. Reject duplicate protected-ref updates,
protected-ref creation or deletion, and any companion update in a batch containing
the protected ref.
For a protected update require incoming old ID `A`, a raw new commit with exactly
two ordered parent headers `[A, H]`, and raw tree ID `T`, all matching the same
unexpired grant. Additionally require `A` to be an ancestor of `H` without
replacement semantics and `T` to equal the raw tree of `H`. This is the narrow
up-to-date, no-fast-forward merge path. No alternate merge strategy, extra parent, substituted tree,
wildcard ref or allow-override path is accepted. Other fixture refs remain subject
to their approved scope and generated native hooks; a mixed batch cannot hide a
protected update from inspection.

Inspect actual raw objects, preserving Git's receive quarantine access while
disabling object replacement and any ancestry substitution. Do not execute
repository-supplied programs, load policy from candidate content, or run arbitrary
configured commands. Bound input/object reads and execution; missing objects,
read errors, timeout or internal errors reject the protected update. Diagnostics
are bounded and non-secret. Trusted grant/guard files are distinct from API
credentials and writable repository content.

After validation, native ref compare-and-swap must still reject an update if
another writer advanced `A` before commit. The hook is not a replacement for that
atomic comparison. Qualification must establish actual supported dispatcher
execution and coverage of all supported protected-ref writer paths; a path that
bypasses receive validation is unsupported until guarded. Missing/non-executable
hook dispatch and installation-health binding remain explicit unresolved risks,
not properties established by this document.

For deterministic overlap, a fixture-only bounded test barrier pauses **after**
all guard assertions pass and **before** the hook returns. While it is paused,
another fully authorized ordinary fixture PR advances `A` to `B`. Resume the first
hook and require native stale-ref rejection, unchanged `B`, and no stale merge
recorded as successful. This barrier tests the final native comparison; it does
not claim to instrument the earlier native protection-check/base-fetch interval.
If the schedule or independent equivalent guarantee cannot be established, retain
an unqualified outcome. Recheck admission expiry after the qualification barrier
and before returning acceptance. The immutable selected grant authorizes that
in-flight native compare-and-swap; this does not claim atomic wall-clock expiry
or approval-revocation enforcement through the eventual ref commit. No timing-only
pass is permitted.

### Authentication and transport

Use direct REST through the existing Python standard library with no new
dependency. Reuse existing lifecycle/state/evidence mechanisms instead of adding
a second CLI, state engine, registry, policy authority, or service. Resolve the
selected credential through native macOS Keychain using the existing
`osxkeychain` helper with exact HTTPS origin, account and repository path. Do not
run arbitrary configured secret commands or fall back to another store. Require
path-scoped selection, reject ambiguous/broader credentials, and verify the
returned account before authenticated operations. Operator enrollment occurs
through private native interfaces with hidden CLI credential entry; no GUI is
required. Tokens and passwords never enter arguments, shell history or chat.

For the selected native personal access token type, the versioned source defines
exactly 40 lowercase hexadecimal characters. Other credential types are not
silently accepted as that type. A credential helper may return only missing
fields, omitting an account already supplied in its exact lookup query. Neither
that supplied username nor a helper echo independently proves the authenticated
principal. Credential enrollment and compatibility qualification are separate:
saving a verified read-only credential grants no merge capability.

Repository-restricted v15 PATs admit
[repository/issue scope families only](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/authz/access_token.go#L70).
[`write:repository` includes repository read access](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/models/auth/access_token_scope.go#L121);
adding `read:user` or `read:misc` is invalid for that token type. A repository-only
PAT receives HTTP 403 from `/api/v1/user`, whose
[route requires `read:user`](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/routers/api/v1/api.go#L634); this is an expected
scope boundary, not proof of the wrong account and not permission to broaden the
token. The concrete production principal-proof interface is therefore reopened.
Selected-account verification remains mandatory before production authenticated
operations; freeze a source-supported proof contract before implementation rather
than require an impossible identity endpoint or relax identity binding.

Do not treat `creator.is_admin=false` in a status response as proof that its
creator is not an administrator. The
[status converter supplies no viewer](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/convert/status.go#L27),
and [user conversion sets administrative identity only for an authenticated viewer](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/convert/user.go#L77).
Preserved `creator.id`, `creator.login` and `creator.restricted` may identify a
synthetic status creator, but role proof
requires an independently authenticated native read for that exact principal.
Keychain selection, an empty/default role field, and successful repository access
are individually insufficient production identity proof.

Repository permission metadata is a separate layer from effective token and
branch authority. An owner PAT restricted to an included repository may return
`permissions.admin=true` and `permissions.push=true`: the
[specific-repository reducer preserves that repository's underlying access mode](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/authz/specific_repos_reducer.go#L25),
which [repository conversion exposes as permission metadata](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/convert/repository.go#L38).
The reducer separately sets
[`AllowAdminOverride=false`](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/authz/specific_repos_reducer.go#L64),
and [native permission helpers enforce that restriction for administrator endpoints](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/routers/api/v1/permissions/helpers.go#L12).
Do not infer effective administrator-API access from the metadata admin bit, or
require that bit to be false for an owner repository-limited PAT. Verify exact
token resource/scope restrictions and effective native permissions separately.
Likewise, repository `permissions.push` does not establish permission to push
directly to a protected branch.

Enrollment must include first-login/password-change completion where required,
creation of the least-privilege credential sufficient for the intended operations,
private storage, selected-account verification, revocation, and rotation/recovery
instructions. Do not use server internal secrets, initial administrator passwords,
temporary verification tokens, or a shared all-scope probe account as normal API
credentials. Missing API permissions stay blocked; server administration access
is not a workaround.

Resolve secrets just in time into private process memory. Keep them out of Git,
chat, command arguments, URLs, trace output, exceptions, evidence, and stored
request bodies. Scrub inherited authentication, tracing and Git configuration
overrides that could change account or disclose credentials. Release a credential
only for its exact approved destination; do not follow redirects or permit URL
rewriting. Use normal TLS and hostname verification, bounded request timeouts,
bounded response bodies and explicit JSON/status validation. Proxy behavior must
not inherit an unqualified ambient route. API responses and CI logs are untrusted
data, never commands or authorization.

Permission qualification uses supported authenticated read-only principal/role
and repository checks before authorized production mutations. Do not assume every
credential can call `/api/v1/user`; its required scope and token-resource policy
must match the selected proof interface. HTTP 401/403, malformed responses, insufficient
scope, unsupported capabilities and unknown authentication state produce safe
blockers. Do not expose raw provider errors or retry credentials from another
account. Credential-source replacement and rotation preserve exact-account
selection and require fresh capability verification before resuming mutations.

### Isolated evidence credential procedure

Only inside the separately approved isolated evidence scope, the CLI procedure
may use owner Basic authentication to verify account/role metadata and configure
the fixture. Complete any required first password change before those operations.
Enter that password through hidden CLI input, retain it only in process memory,
and never save it in a file, Keychain entry, argument, log or chat. Its privileged
use is restricted to fixture setup and authorized native reads; it is not the
principal for ordinary merge-guard tests or a production authentication fallback.

The procedure may mint two explicitly identified `write:repository` PATs, each
restricted to the single authorized fixture repository. Before any guard test,
bind each token's actual principal through the permitted synthetic status
response's creator ID/login/restricted fields to independently Basic-verified
account metadata and native read-only role/fixture-permission evidence. Establish
the test actor's non-administrator status through that independent role evidence,
not `creator.is_admin`. Keep the setup principal and ordinary merge actor distinct.
Token scope/resource readback and owner/account binding must match the approved
fixture exactly; unavailable or ambiguous proof blocks the test.

For the ordinary fixture merge actor, require independently authenticated native
account/role evidence establishing non-administrator status, then bind the actual
token creator ID to that account. Read back the exact default branch and expect
`protected=true`, `user_can_push=false` and `user_can_merge=true` under the
approved fixture rule. The isolated run observed fixture role/policy and negative
access controls; this procedure does not generalize those results to production. Native
[branch conversion computes push and merge fields from branch-specific policy](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/convert/convert.go#L58);
`user_can_merge=true` expresses permission and does not prove required checks,
exact-base validation or atomic merge safety. Retain effective administrator-API
negative evidence without mistaking an owner PAT's repository metadata for the
ordinary actor's role. No production account-proof shortcut follows from these
fixture-only observations.

This is a fixture-only qualification procedure, not a production selected-account
proof interface. Do not prescribe credential-challenge writes in production,
generalize fixture status identity to an unverified production principal, or infer
successful execution from the procedure alone. The bounded observations above
record the executed fixture controls and their limits. Production
identity proof remains a material contract decision before interface freeze.

### Forgejo pull-request and check adaptation

The version endpoint returns an AppVer string with possible build metadata; a
standard selected build reports `15.0.10+gitea-1.22.0`. Parse the complete anchored
semantic version and compare its Forgejo core to the qualified version. The Gitea
compatibility suffix is not the Forgejo major. Reject prerelease/development or
unqualified version metadata for mutation eligibility rather than comparing only
a guessed literal. [Version response](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/routers/api/v1/misc/version.go#L25)
and [build metadata](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/Makefile#L83)
are the canonical source for this compatibility boundary.

The adapter maps the documented Forgejo repository, PR, commit/check and merge
interfaces into existing lifecycle contracts. It verifies returned identities,
states, native IDs and object IDs rather than trusting a request's parameters.
All list operations follow documented pagination to completion within explicit
bounds. Reaching a bound, inconsistent pages or unavailable continuation is
incomplete evidence and blocks mutation.
Respect the instance's qualified page limit; a server may clamp the requested
limit, so a shorter page alone does not prove completion. Null status lists and
empty combined states are not success. A combined-status state covers its
returned page, not necessarily all contexts; its JSON total may be page-local.
Use the qualified continuation/count semantics and required-context authority.

PR lookup covers all pages and relevant states so terminal history does not
masquerade as an open match. Selection requires exact repository/head owner,
feature ref, target and open state. Multiple open matches block. Draft creation
uses the instance's qualified prefix/native draft representation; the returned
PR must independently prove expected draft state. Returned URLs must identify
the exact approved host/repository and PR, not merely share a URL prefix.

Checks must retain trusted producer/repository, definition, run/job/attempt,
head/base/tested-object, mapping and toolchain/environment bindings required by
[workflow-integration-ci.md](workflow-integration-ci.md). Forgejo-specific
producer identities require an explicit versioned adaptation; do not substitute
an arbitrary status name for GitHub App/workflow proof. Only actual qualified
success passes. Missing/empty, skipped, neutral, pending, unknown, cancelled,
timed-out, failed or untrusted evidence cannot become a pass. The existing narrow
unrelated-pending rule applies only after explicit classification and opt-in.

### Automatic integration and consent

[workflow-integration-ci.md](workflow-integration-ci.md) remains the canonical
authority for exact-repository policy, ordered review recommendations,
affected-check closure, target/default restrictions, fresh validation, head/base
binding, bounded watch/repair, permitted exceptions and retained work. Its
source-ready contract is not proof that any generic merge path is implemented or
runtime-qualified. Forgejo adaptation must qualify that whole path before
activation rather than replace it with a permissive provider shortcut.

Draft-to-ready promotion is a separate authorized mutation after the exact PR,
head/base, review, required-check and merge-policy preconditions pass. Creation
records the provider-added draft prefix and intended non-draft title. Promotion
removes only that recorded prefix from the exact expected title; it never strips
arbitrary text or overwrites an observed title edited by another actor. Changed title,
head, base or authority requires fresh evaluation. Re-read the PR after the title
edit and require `draft=false`, the intended preserved title and unchanged
repository/head/base before requesting merge. A lost response requires observation
before retry; unexpected state remains blocked. Use a native conditional edit
where supported and test concurrent-edit detection and recovery; do not claim an
atomic title-preservation guarantee from a read-then-write sequence. No manual-ready
fallback is silently substituted for the requested automatic workflow.

Use ordinary merge commits and the native expected-head guard. Query fresh base,
default, permissions and protection immediately before mutation. Because no
expected-base field is established, activation additionally requires independent
qualification of an existing allowed server branch policy that enforces validation
against the current base across the merge request. A pre-request base read alone
does not satisfy this guarantee. If the instance cannot supply it, report
`completed_unmerged` with the blocker and retain the branch/work.

No Forgejo administrator bypass, direct protected-branch push, force push,
protection disabling, branch deletion, history rewrite, or degraded validation is
authorized. User desire for automatic merging is not a digest-bound checkpoint
or exact-repository standing policy. Bind automatic policy or checkpoint to the
approved provider/host/repository, ordered PRs/heads, target/base, mapping, specs
and evidence; material drift requires renewed authority under the canonical
contract. Verify returned merge object, ordered parents, head inclusion and gate
ancestry before recording success. Query uncertain outcomes before retry.

## Failure, recovery, rollback, and maintenance

| Condition | Required result and recovery |
|---|---|
| No credential, wrong account, revoked token, denied API | Block without fallback; enroll or repair the selected private source, then repeat identity/capability checks. |
| Invalid TLS, redirect, rewrite or remote mismatch | Stop before credential release/mutation; correct explicit configuration and obtain fresh bound authority. Never bypass TLS. |
| Unsupported version/draft/check/base protection | Preserve work and report unavailable capability; no ordinary-PR or permissive-merge substitution. |
| Rate limit, bounded transient error or timeout | Respect provider retry guidance within the canonical explicit watch deadline; otherwise retain unavailable/pending state for the next operator action. No daemon or endless loop. |
| Lost create/merge response | Inspect exact PR/ref/object state before another request; ambiguous or unverifiable outcome remains blocked. |
| Head/base/default/protection or policy drift | Invalidate stale recommendation/evidence and re-evaluate; use the canonical renewed-approval rules. |
| Installation failure | Preserve the installed revision and evidence, restore the previous compatible managed distribution through the existing owner, and verify GitHub behavior. Do not change consumer or server state to hide failure. |
| Rollback with new Forgejo records | Preserve records and source refs; old helpers must reject unsupported provider records. Do not rewrite them into legacy GitHub records or claim a binary rollback undoes a remote merge. |

Maintenance covers supported Forgejo capability changes, API/draft/check
compatibility, credential revocation/rotation, negative permission checks,
GitHub regression behavior, and retirement. Retirement disables new operations
for the exact private configuration, revokes its selected credential through the
credential owner, and preserves records, branches and recovery evidence under
existing retention authority. No automatic data deletion or consumer deployment
change is included.

## Validation strategy and applicability recommendation

### Canonical provider research

Versioned upstream source establishes the following design constraints; it does
not establish the selected server's running version, settings, or permissions:

- Draft classification uses configurable title prefixes in
  [Forgejo v15.0.10 draft handling](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/models/issues/pull.go#L788).
  Creation/reuse must verify the returned native representation rather than
  assume a hardcoded prefix.
- Native merge preparation has an
  [expected-head check](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/pull/merge_prepare.go#L46).
  The [merge API sequence](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/routers/api/v1/repo/pull.go#L936)
  does not establish an expected-base request guard.
- [Outdated-branch policy evaluates persisted `CommitsBehind`](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/models/issues/pull.go#L954),
  and [base updates are processed asynchronously](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/pull/pull.go#L281).
  The policy flag alone cannot be treated as atomic current-base proof.
- [Pre-receive protection has administrative bypass conditions](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/routers/private/hook_pre_receive.go#L360).
  The adapter must qualify effective enforcement, not infer it from a protection
  object's presence.
- [Supported native Git hooks](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/modules/git/hook.go#L19)
  execute during the push, after temporary base fetch and merge creation. They
  cannot hold the missing interval between the initial protection check and
  that fetch. The upstream
  [`TestSeamPostReceiveSync` seam](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/routers/private/hook_post_receive.go#L35)
  offers a deterministic test insertion point before post-receive synchronization,
  but is gated to Go test execution and unavailable in the deployed release.
- [Status API pagination](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/routers/api/v1/repo/status.go#L275)
  and [latest-status selection](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/models/git/commit_status.go#L247)
  require complete enumeration and exact status identities; a page-local
  aggregate is insufficient evidence for all required checks.

### Existing authorities and future acceptance

Existing source owners are `dot_local/bin/executable_dbsctrctl`, the DBSCTR
registration/delivery/review skills, `tests/test_dbsctrctl.py`,
`tests/test_initiative_cli_approval.py`, `tests/test_initiative_local_launch.py`,
and the configured distribution/instruction tests. The primary must calculate
the affected closure before Build; this list is routing evidence, not an
unbounded write grant. Coordinate shared integration contracts with their owner;
the private consumer owns its required checks and CI implementation.

Deterministic implementation acceptance must cover cross-host slug collisions,
strict identity and URL parsing, old manifest digest stability, old-record
readability, old-helper rejection, exact-account selection and denial, token
redaction, redirects and rewrites, all-page PR/status enumeration, draft-prefix
variation, ambiguous/open versus terminal PR history, stale launch and final-push
identities, missing/empty checks, forged producer/definition evidence, expected-head
changes, base races, uncertain merge reconciliation, bounded retry, and GitHub
regression behavior. New provider fixtures cannot replace existing GitHub tests.

Runtime acceptance must use explicit private enrollment and exact-repository
authority for the first instance/consumer only. Establish version and capability
through authenticated safe reads, qualify token permissions and account isolation,
verify draft create/reuse and feature-only Git transport, qualify required checks
and native current-base safety, and exercise permission-negative paths. Any
mutating smoke requires its own authorized exact scope and cleanup/preservation
contract. A 403 or a temporary administrator probe is not positive evidence.

Run configured affected `pytest` and Python compilation, affected managed
configuration rendering/contract checks, publication and instruction authorities
declared by `.github/workflows/test.yml`, and `git diff --check`. Include all new
documents in the existing public-content authority's candidate inventory. The
primary owns exact candidate checks and final publication readiness; this feature
document does not claim those checks ran. No tool installation is prescribed.

### Gate Ledger

| Gate | Applicability | Result | Exception |
|---|---|---|---|
| Domain | required: provider identity, account and authority ownership change | pending | none |
| Behavior | required: registration, delivery and integration behavior changes | pending | none |
| Spec | required: provider, record, credential and API interfaces | pending | none |
| Contract | required: identity, consent, credential, check and merge safety | pending | none |
| Test-driven implementation | required: affected Python and compatibility acceptance | pending | none |
| Refactor | required: reuse existing provider/lifecycle owners | pending | none |
| Review/Integrate | required: exact support PR review, strict validation and merge evidence | pending | none |
| Release | not_applicable: no separately versioned package, registry or public release artifact is requested; delivery is merged source plus managed local installation | not_run | none |
| Deploy | required: install the qualification hook on the fixture only; later install the merged managed DBSCTR revision on the current computer only | pending | none |
| Operate | required: loaded local behavior, first-instance qualification and GitHub compatibility evidence | pending | none |
| Maintain/Retire | required: compatibility, credential rotation/revocation and rollback/preservation obligations | pending | none |

The future Build applicability plan must reference the committed
`docs/specs/dbsctr_v3_lifecycle/PROFILE.md` identity and mark `domain`, `behavior`,
`spec`, `contract`, `test_driven_implementation`, `refactor`, `review_integrate`,
`deploy`, `operate` and `maintain_retire` required, with only `release` reasoned
not applicable as above. Risk is `critical`; affected modules are Python and
Security. Build persists the plan privately through the existing lifecycle path,
runs actual preflight, presents exact scope/risk/target/launch digest, and receives
the required launch approval before registering. This recommendation is not a
machine plan, a committed profile identity, a receipt, a passed gate, or launch
approval.

## Visual Evidence

All evidence below is editable, text-first and scoped to this provider extension.
No rendering-dependent diagram is required.

| Concern | Classification and review question |
|---|---|
| Boundary | required: ownership table below; who supplies intent, credentials, policy and remote authorization? |
| Interaction | required: ordered interaction table; what must precede each remote mutation and installation? |
| State | required: guarded state table; when does work block, reopen or finish? |
| Data/trust | required: directional trust table; which data crosses each authority boundary and where can secrets persist? |
| Schema | required: record relationship table; how do identity, receipt, account, evidence and approval join without breaking legacy authority? |
| Dependency/deployment | required: delivery dependency table; what must be merged, qualified and installed, and what stays consumer-owned? |
| Quantitative | not_applicable: no performance, capacity, adoption or benefit estimate is used to justify this scope; no chart is supported. |

### Boundary

| Actor or system | Supplies | Authorized owner of resulting decision |
|---|---|---|
| Operator | Exact scope and explicit checkpoint or repository policy | Operator; DBSCTR validates binding |
| Credential source | Secret for one selected private account/destination | External credential owner |
| Consumer repository | Trusted check definitions, producer identities and source intent | Consumer owner |
| DBSCTR primary | Bound recommendation, verified lifecycle/gate evidence and operation | Primary within existing approval/policy |
| Forgejo | Account permissions, PR/check state, branch protection and merge result | Native server authorization |
| Trusted fixture filesystem operator | Immutable synthetic grant and exact guard installation | Fixture-only operator authority, distinct from API merge actor |
| Native Git ref transaction | Actual ref comparison after receive validation | Final stale-ref exclusion; requires qualification |

**Text Equivalent:** Operator authority, credential storage, consumer validation,
lifecycle decisions and server authorization have distinct owners. No one
substitutes a credential, status name or helper recommendation for another
owner's decision. Source: Domain and Integration contracts above. Owner:
lifecycle maintainer. Change trigger: ownership or authorization changes.

**Text Equivalent (fixture boundary):** The operator controls immutable synthetic
grants and the hook installation; the ordinary API actor requests merges and
cannot rewrite that authority. Generated Forgejo hooks remain active and native
Git must compare the actual ref at update. Source: Fixture-only pre-receive guard
contract above. Owner: lifecycle qualification primary. Change trigger: dispatch,
grant ownership, writer coverage or native transaction changes.

### Interaction

| Order | From and to | Guard before proceeding |
|---|---|---|
| 1 | Operator to private configuration | Select provider identity, explicit account and external source. |
| 2 | DBSCTR to credential source and Forgejo | Resolve exact credential; verify identity, permissions and required capability. |
| 3 | DBSCTR to operator/policy | Bind fresh source, checkout, destinations, plan and base to launch approval. |
| 4 | DBSCTR to Git and Forgejo | Recheck gates/destinations; push feature only; create/reuse and verify draft. |
| 5 | DBSCTR to validation and delivery authority | Bind exact PR/head/base, trusted successful required checks and integration consent. |
| 6 | DBSCTR to Forgejo | Enforce head and independently qualified current-base safety; verify merge outcome. |
| 7 | Merged support revision to current computer | Managed installation and loaded-behavior qualification; consumer deployment is separate. |

**Text Equivalent:** Private configuration and authenticated qualification precede
launch approval. Gate-checked feature delivery precedes strict integration.
Guarded remote merge verification precedes managed local installation of the
support change. Every drift or unknown guard blocks the dependent mutation.
Source: Behavior and interface contracts above. Owner: lifecycle maintainer.
Change trigger: ordering, approval, mutation or installation changes.

**Text Equivalent (fixture interaction):** Validate the candidate in a local bare
harness first, install only the exact fixture hook, read its health and native
policy, then request ordinary REST merges. The hook parses the full update batch
and checks the immutable grant and raw objects. A controlled pause after those
checks allows a competing ordinary PR to advance the base; after resumption Git
must reject the stale ref update. Retain exact results and installation identity.
Source: Fixture-only guard contract and expanded qualification plan. Owner:
lifecycle qualification primary. Change trigger: ordering, barrier, dispatcher or
native comparison changes.

### State

| State | Permitted transition and guard |
|---|---|
| Discovery proposed | Automatic-integration readiness stays blocked on production selected-principal proof and an adequate native current-base mechanism. Resolve the proof interface without weakening selected-account verification, and qualify native current-base safety or reopen its design. Other runtime and consumer prerequisites remain gates. |
| Ready for preflight | Become registered only after actual feasible preflight and exact launch approval. |
| Active work | Become draft-delivered only after lifecycle gates, remote checks and verified draft response. |
| Draft-delivered | Become merged only after strict authorized validation plus native head/current-base safety and verified result. |
| Blocked or outcome uncertain | Preserve work; recover through explicit repair and fresh exact evidence, never guessed success. |
| Completed unmerged | Retain branch/records and report blocker; no automatic weakening or consumer deployment. |
| Support merged | Become locally installed only through approved managed installation and operation evidence. |
| Fixture guard mechanics qualification | Proceed from local harness to fixture installation only after local negatives/positive control pass; qualify the exercised REST predicate/CAS component only with exact dispatch/installation identity and deterministic stale-ref evidence. Other writers and production readiness retain their separate unresolved status. |

**Text Equivalent:** Readiness, launch, draft delivery, merge and installation are
separate guarded transitions. Missing authority blocks; uncertain outcomes require
remote reconciliation. Unmerged completion retains work. Source: Behavior,
failure and Gate Ledger above. Owner: lifecycle maintainer. Change trigger:
state, recovery or completion semantics.

**Text Equivalent (fixture state):** The prior native-only result remains
unqualified. Expanded guard mechanics proceeded through local harness, fixture
deployment and exact REST dispatch/installation observation to deterministic
ref-comparison proof. That bounded component is qualified; other writer coverage,
production health and authority remain unresolved. No component transition enables
DBSCTR product implementation by itself. Source:
Fixture-only guard contract and qualification plan. Owner: lifecycle qualification
primary. Change trigger: readiness, health, proof or failure transitions.

### Data and trust

| Direction | Data allowed to cross | Data retained or rejected |
|---|---|---|
| Public specification to Build | Generic contracts and sanitized source evidence | No private instance, account, consumer or machine identity. |
| Private configuration to resolver | Exact account/source and destination selection | Selection stays in governed local authority. |
| Resolver to request process | One selected secret | Memory only for DBSCTR use; never arguments, Git, chat or evidence. |
| Forgejo to DBSCTR | Bounded validated identity, PR, check and protection evidence | Untrusted fields validated; raw sensitive errors/logs stay private. |
| DBSCTR to local Cycle Record | Bound identity, digests, gate/outcome evidence and non-secret selection | No credential bytes or raw transcript. |
| Trusted operator store to fixture guard | Immutable synthetic repository/ref/base/head/tree/expiry grant | API actor and repository content cannot replace it; no production attestation authority. |
| Receive quarantine to fixture guard, then native ref transaction | Complete batch and raw commit/tree assertions, followed by actual old-ref comparison | No replacement-object ancestry or permissive fallback; exact installation/coverage still requires proof. |

**Text Equivalent:** Public artifacts contain reusable contracts. Private authority
selects a destination-bound credential; request memory uses it, while lifecycle
records retain only governed identity/evidence. Provider output is untrusted and
cannot authorize actions. Source: Authentication and record contracts above.
Owner: lifecycle and credential owners. Change trigger: data flow, retention,
credential handling or trust-boundary changes.

**Text Equivalent (fixture trust):** Operator-owned grant data is trusted only for
this synthetic scope. Incoming updates and raw objects are untrusted, including
quarantined objects; the guard validates their exact identity without replacement
semantics. Git then checks whether the ref still has the approved old value.
Neither a supplied grant nor one successful request proves missing-hook health or
all writer coverage. Source: Fixture-only guard contract. Owner: lifecycle
qualification primary. Change trigger: grant, object access, dispatch, coverage or
atomic comparison changes.

### Schema relationships

| Relationship | Required binding |
|---|---|
| Manifest/context home to receipt | Versioned full repository identity plus existing committed artifact/manifest digest authority. |
| Receipt and private delivery selection to launch | Full identity, exact account/source identifier, destinations, plan, source closure and target/base digest. |
| Registered Cycle Record to draft PR | Same forge identity, account selection, feature/target refs and verified native PR identity. |
| Recommendation/check evidence to merge | Same repository, head/base/tested object, trusted producer/definition, policy and approval. |
| Legacy record to compatibility reader | Original GitHub-only meaning and original digest; no implicit provider upgrade. |

**Text Equivalent:** Existing record owners join through exact provider-aware
repository identity and immutable authority digests. Private account selection
binds launch and operations, while checked PR/head/base evidence binds merge.
Legacy authority stays GitHub-only. Source: Lifecycle records and Integration
contracts above. Owner: lifecycle maintainer. Change trigger: serialized schemas,
identity comparison, digest inputs or compatibility changes.

### Dependency and deployment

| Dependency | Required disposition before dependent action |
|---|---|
| Existing registration/distribution and integration contracts | Reuse and reconcile their owned interfaces before activating provider adaptation. |
| Selected external credential source | Enroll privately and verify selected-account permissions before authenticated use. |
| Consumer check authority and native server protection | Establish trusted successful required checks and current-base safety before automatic integration. |
| Support source PR | Review, validate and verify merge before managed local installation. |
| Current computer's managed distribution | Install the merged revision and verify loaded behavior; no remote installation or consumer deployment is implied. |

**Text Equivalent:** Provider adaptation depends on existing lifecycle owners,
private credentials, consumer validation and server protection. The support change
is reviewed and merged before its managed installation on one computer. Consumer
deployment remains independently owned and outside scope. Source: Scope,
Integration and Gate Ledger above. Owner: lifecycle maintainer, with consumer and
credential owners retaining their boundaries. Change trigger: runtime dependency,
qualification scope or delivery target changes.

## Qualification before implementation

The historical native-only spike produced the **unqualified** outcome above.
The expanded fixture stage qualified the stated exact-object/CAS component.
Neither stage authorized production provider implementation. Their lifecycle,
exact private scope, approval and evidence remain separate from this public
contract. This document is not registration or mutation approval, and private
credentials remain confined to native private interfaces.

### Approved expanded fixture-guard plan

The operator has approved expanded fixture-only server protection qualification.
No further scope approval is implied for global configuration, built-in hooks,
server/service changes, shared management or production activation. The consumer
remains read-only and existing fixture resources remain retained. The independent
guard and synthetic grants described above formed the exercised candidate. The
completed bounded guard/CAS results are recorded above; they do not replace the
prior native-only unqualified result or establish production activation.

1. Run the local bare-repository harness first. Cover an exact positive control;
   old-base/head/parent-order and tested-tree mismatches; extra parents; missing,
   expired, malformed, ambiguous or untrusted grants; invalid/duplicate protected
   updates; protected creation/deletion; absent objects; input/read/internal errors;
   quarantine access and replacement-object resistance. Verify rejection preserves
   refs and objects are inspected as raw data. Do not deploy after a local failure.
2. Exercise deterministic local overlap using the bounded post-validation barrier.
   Advance the target through a competing authorized local receive, then resume
   the old update and require native compare-and-swap rejection. Capture the
   validated tuple, barrier ordering, actual ref outcome and native rejection;
   overlap timestamps alone do not satisfy the case.
3. Capture original fixture hook state, then install only the independent supported
   executable and immutable operator-controlled grant inputs. Preserve generated
   hook bytes and configuration. Read back installation identity and native
   protection, then establish dispatcher behavior, writer-path coverage and the
   limits of missing/non-executable hook health detection. These risks remain open
   until evidenced; successful validation inside one invocation is insufficient.
4. Use ordinary non-administrator fixture REST merges for native positives and
   grant/object negatives. Keep native required checks, independent review and
   permissions intact. No force push or direct protected-base push is a server
   test path. Source/dispatch analysis must account for other supported writers;
   an uncovered writer remains unsupported, not silently qualified.
5. Pause the first ordinary merge after guard validation and before return. Allow
   another fully authorized ordinary PR to advance `A` to `B`, then resume the
   first hook and require native stale-ref rejection with `B` retained. If native
   execution cannot expose that schedule, document the limitation and retain an
   unqualified outcome unless an independently proved equivalent guarantee exists.
6. Retain all fixture resources, original/installed hook identity, immutable grant
   identity and bounded results. Restore only exact authorized fixture state if
   recovery is required; no branch, repository, account or evidence deletion is
   implied. Report pending, qualified, counterexample or unqualified truthfully,
   retaining unresolved production principal/producer interfaces separately.

Fixture hook installation makes **Deploy required** for the expanded evidence
plan, along with Kernel, Review/Integrate, Operate and Maintain/Retire. Release is
not applicable because no package is published. The installation is qualification
infrastructure only: no DBSCTR product implementation or installation is allowed
before required qualification and readiness. Durable production hook installation,
management and recovery remain future Git-hosting ownership, not an extension of
this temporary fixture authority.

The retained qualification requirements are:

1. Establish the actual server/API version, selected account, repository
   permissions, effective branch-protection rule and trusted check-producer
   capabilities through authenticated reads. Inspecting protection may require
   separately scoped repository-administrator read access; do not turn that into
   permission to bypass protections during merge.
2. Obtain an exact scope for one private disposable qualification repository,
   one restricted non-admin fixture account with no repository-creation permission
   and write collaboration on that fixture only, and their test
   branches, PRs, status producers and review actors before creating or merging
   fixtures. The current operator retains fixture administration; the fixture
   merge actor must not be an instance administrator or gain consumer access.
   Preserve the fixture resources until separately authorized cleanup. The
   existing consumer remains read-only. The expanded fixture hook is the only
   approved server guard candidate. No server binary patch,
   upgrade, runner installation, real-consumer merge or branch deletion is
   implicit in this scope.
3. Exercise ordered merge commits with successful DBSCTR/test evidence for one
   exact head and base. Move the base concurrently both before and after native
   merge preparation, and verify that stale-base evidence cannot authorize a
   merge. Include ordinary and relevant administrator/push-capability cases;
   native bypass or stale protection data is a failed qualification.
4. Combine versioned source semantics with controlled native observations.
   Passing timing stress or a client-side lock does not prove atomic enforcement.
   If the necessary schedule or native observation cannot be established, record
   qualification as unavailable rather than passed.
5. Verify safe draft promotion, exact-head refusal, complete status pagination,
   missing/forged producer rejection, negative permissions and uncertain-outcome
   reconciliation. Preserve failures and the exact tested artifact/version set.
6. Return one explicit outcome: the native route satisfies the existing contract,
   a counterexample disproves it, or the capability remains unqualified. Only the
   first outcome permits Discovery to freeze the producer/attestation schema and
   complete implementation readiness. The other outcomes retain automatic merge
   as required and reopen the design; they do not approve a reduced release or a
   weaker guarantee.

The source-permitted candidate to reproduce starts with validated base `A` and
head `H`, with stored divergence zero. After the initial merge check, another
legitimate PR advances the base to `B` while divergence refresh is delayed. The
first PR's separate per-PR lock does not exclude that merge. Native preparation
then fetches `B` and `H`, creating merge parents `(B, H)`; a normal push is a
fast-forward from `B`. A final protection check can still read the stale stored
divergence and successful `H` statuses. This is a source-backed candidate, not a
live reproduction or proof of safety. Its native disposition must include the
non-admin case rather than relying on an administrator bypass.
[Merge lock and reload](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/pull/merge.go#L207),
[base fetch](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/services/pull/temp_repo.go#L139),
and [final hook](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.10/routers/private/hook_pre_receive.go#L416)
define the inspected path.

The deployed release has no qualified deterministic control for that earlier
interval. Native hooks run too late to pause that interval, and the upstream test
seam is unavailable there. The added fixture guard instead asserts exact objects
at pre-receive. Its deterministic post-validation barrier established a competing
base advance followed by native stale-ref rejection, qualifying the bounded
guard/CAS predicate under the stated assumptions. It neither moves the original
hook earlier nor proves the native-only path safe. The historical native-only
result remains unqualified, while production authority, health and hosting
interfaces remain unresolved. No provider implementation is claimed.

No new package release or installed DBSCTR deployment is part of either evidence
stage. The historical native-only stage had Release and Deploy reasoned not
applicable. The expanded hook stage requires fixture Deploy; Release remains not
applicable. Operate covers native observation, and Maintain/Retire covers fixture
preservation, recovery and separately scoped cleanup. The later support
implementation retains the full Gate Ledger above.

## Build handoff

Credential storage and required validation are settled: native macOS Keychain
with exact account/repository selection, and committed project-selected DBSCTR
gates plus a real test suite. Automatic merge remains mandatory. The historical
native-only result remains unqualified; the completed expanded fixture work
qualifies only its synthetic fixed-repository ordinary REST predicate plus native
ref comparison under trusted operating-system/guard/grant assumptions.

The next Discovery task is to settle production selected-principal proof,
producer/attestation authority, admission-grant expiry/revocation, loaded guard
health and durable Git-hosting interfaces. Retain the concurrent draft-title
safety requirement. Do not generalize this result into all-writer coverage,
complete merge automation or permission to implement the DBSCTR product.
Global/shared or durable production changes remain outside the fixture scope.
Only after the remaining contracts and readiness are settled may Discovery freeze
serialized producer/attestation interfaces and the affected source/test closure
with their existing owners,
reconcile profile/readiness with the primary, and validate the exact artifact
inventory under existing publication authority. No implementation-ready claim,
receipt, preflight, registration or product implementation approval is made here.

Future Build must preserve GitHub behavior, carry these contracts through the
existing DBSCTR kernel and strict integration owner, qualify only the selected
private instance/consumer, deliver the support PR through review and merge, and
install only the merged managed support revision on the current computer. Shared
helper, record and integration changes require serialized primary ownership;
independent credential-store and consumer-check work may be researched separately
but cannot launch another lifecycle slice or mutate the consumer by implication.
