# Forgejo local-only lifecycle registration

**Bounded source interface; managed installation and real-consumer operation
remain unqualified.** This feature belongs to `dbsctr_v3_lifecycle`, owned by the dotfiles
maintainer under [the Engineering Profile](../PROFILE.md). Risk is **critical**;
the affected modules are Python and Security. The support change is delivered
through the existing GitHub feature-branch and reviewed draft-PR path. Its eventual
managed installation is limited to the operator's current computer.

## Approved outcome and scope

The operator explicitly approved local private-cycle registration first. A
Forgejo consumer must be able to obtain a truthful Initiative receipt, approve an
exact launch, execute the existing Development Kernel, and complete local
validation while preserving the exact validated source. Reviewed manual delivery
remains a separate explicit Git operation. Local completion must perform no
network activity and must never imply publication or integration.

The complete [Forgejo support proposal](forgejo-support.md) remains authoritative
for the deferred remote-automation outcome and its unresolved safeguards. This
slice does not enable Forgejo push, draft-PR APIs, automatic merge, release,
deployment, autonomous claims or workflow-feedback publication. It does not
qualify a production API principal, check producer, server guard, hosting contract
or atomic current-base merge guarantee. Preserve the earlier failed qualification
cycle and its evidence without converting them to a pass.

There is no new service, registry, policy engine, credential store, provider CLI
dependency or consumer CI mandate. Existing lifecycle, evidence, approval and
preservation owners remain authoritative. Private consumer configuration and
credentials are not public fixtures or support-PR artifacts.

## Facts and readiness

At Discovery, the installed helper and public base supported GitHub-only
Initiative origin checks, manifest/receipt schema 1 and native Cycle Record
schema 5. The source candidate adds the bounded schema 2/6 path below; its
presence does not establish installed capability. Existing
`local` intent is a legacy delivery mode: its generic Final Push path can push to
an upstream feature branch. It is not the local-only behavior specified here.

This specification fixes the bounded outcome and interfaces below. Publication
checks, committed authority, actual launch preflight, exact launch approval and
registered gate evidence remain separate required proofs. A ready manifest slice
means its specification is settled; it does not claim those proofs have passed.
Missing private credentials or an unqualified controlled Git transport is a safe
runtime blocker, not permission to start a login or broaden credentials.

## Domain and ownership

| Term or owner | Meaning and responsibility |
|---|---|
| Repository Identity | Exact provider, canonical HTTPS origin and canonical owner/repository path; account selection is separate. |
| Local-only Cycle | A native schema 6 cycle whose delivery mode permits local validation and denies remote delivery. |
| Comparison Base | An explicitly fetched base ref and immutable commit used to bind registration; it is not a push destination. |
| Credential Selection | Private exact origin/account/repository lookup through native macOS Keychain; it is not independent API principal proof. |
| Local Completion | Successful required gates plus exact source/evidence validation, retained locally with manual delivery pending. |
| Manual Delivery | A later, separately authorized and reviewed Git operation outside this cycle's delivery machinery. |
| Lifecycle maintainer | Owns helper behavior, versioned schemas, compatibility, managed installation and preservation. |
| Consumer owner | Owns the private repository, profile, validation suite, source, credentials and any later manual delivery decision. |

## Behavior

| Given | When | Then |
|---|---|---|
| A committed ready Forgejo-local Initiative slice and a clean linked task checkout | The primary runs preflight with explicit selection | Validate typed source/target identity, perform the controlled read-only base fetch, and return an exact launch plan without registration or consent. |
| Equal owner/repository strings on different hosts or providers | Identity is compared | Treat them as different repositories for receipt, launch, resume and completion. |
| A valid launch plan | The operator approves its exact digest and registration rechecks it | Register only the matching native local-only cycle, preserving the existing approval provenance rules. |
| Changed source, base, profile, account selection, destinations, checkout or plan | Registration or resume is attempted | Reject stale authority and require the existing fresh-preflight/approval procedure where applicable. |
| A Forgejo local-only checkout compares against its protected base | Registration runs on its distinct task branch | Accept the base only as comparison authority; do not normalize the intent to draft delivery. |
| An exact already registered local-only cycle | The same launch is resumed | Preserve its original approval and identity; do not invent new consent or silently change delivery mode. |
| Required gates and artifact reviews pass with exact recorded commits | `complete-local` runs | Validate exact source and evidence, record immutable completion identity, retain unpublished work, and report manual delivery pending without network activity. |
| Evidence is missing, failed, stale or bound to other source | Completion runs | Refuse completion and preserve the record, source and failures. |
| A local completion is repeated | HEAD, tree and completion identity still match | Return the same local completion without changing its meaning or publishing anything. Changed source refuses the repeat. |
| A local-only cycle | Final Push or a Forgejo non-local delivery intent is requested | Refuse before credential lookup, target locking or network activity. |
| A successfully completed but unpublished local cycle | Removal eligibility is evaluated | Keep removal blocked; local validation is not delivery or preservation proof. |
| Existing supported GitHub records and schema 1 Initiatives | Their existing workflows run | Preserve existing identities, digests, record shapes and delivery behavior, including legacy schema 5 local intent. |
| Missing credentials, endpoint mismatch, redirect or unsafe Git configuration | A controlled fetch is requested | Fail safely without another account, interactive login, credential enrollment or remote write. |
| Zero, ambiguous or malformed native credential matches | Exact metadata selection runs | Refuse before requesting any password data. A unique match permits only a reference-bound single-item read, followed by attribute revalidation. |
| Git has an isolated home | Its dedicated credential child starts | Bind only that child's native lookup home to the current operating-system UID; malformed account-home metadata refuses before lookup. |

## Interfaces and schemas

The source candidate extends the existing owners rather than adding parallel
lifecycle state. These interfaces are not claims about installed capability.

### Typed repository identity

The exact object is `{provider, origin, repository}` with no extra fields.
`provider` is `github` or `forgejo`. The origin is HTTPS with a validated hostname
and optional port, lowercased DNS names and omitted default HTTPS port; credentials,
path, trailing slash, query, fragment, controls and ambiguous authority forms are
rejected. Non-default ports remain identity. A repository has exactly one
validated owner and repository component using the existing bounded portable
name alphabet; empty, dot, dot-dot and encoded path components are rejected.

GitHub identity uses `https://github.com` and preserves the existing provider's
case-insensitive repository equality. Forgejo repository paths compare exactly,
including case, because this slice performs no API canonicalization. It accepts
only configured canonical HTTPS Git endpoints for that identity. No SSH mapping,
subpath deployment, rename/transfer alias or host inference is introduced. Every
configured fetch/push URL of the selected remote must resolve to that same
identity, although no push is enabled. A URL rewrite or redirect cannot retarget
the selection or serve as successful origin proof.

For example, a synthetic identity may be:

```json
{"provider":"forgejo","origin":"https://forge.example.invalid","repository":"example/private-config"}
```

### CLI selection and expected identity

For the new path, `begin` requires `--delivery-intent local` and all four explicit
selectors: `--forge-provider forgejo`, `--forge-origin HTTPS_ORIGIN`,
`--forge-repository OWNER/REPOSITORY`, and `--forge-account ACCOUNT`. The fixed
credential source is `osxkeychain`; there is no arbitrary command or source flag.
Reject mixing Forgejo and GitHub selector families, incomplete selections,
unknown providers and all non-local Forgejo delivery intents before authentication
or network activity. Lower-level `start` cannot bypass these selection and
Initiative approval contracts for a Forgejo cycle.

For schema 2 receipts, the exact target interface is
`--expected-repository-json JSON`, where JSON is the exact typed object above.
It is mutually exclusive with `--expected-repository`. Schema 1 keeps the existing
required `--expected-repository OWNER/REPOSITORY` interface unchanged. Schema 2
manifests may describe both supported identity kinds, but this slice activates
schema 2 registration only for Forgejo local-only targets. GitHub registration
continues through its existing schema 1/5 path; a schema 2 GitHub-target launch
reports unsupported capability rather than silently changing legacy records.

Existing `initiative-check`, `initiative-receipt`, `begin --preflight`,
`--expected-plan-digest`, `--expected-launch-digest`, approval and resume commands
remain their owners. `complete-local [--cycle-id CYCLE_ID]` takes no delivery
destination or account override. Without an ID it consumes the validated active
local-only record. An explicit ID may select only the already completed local-only
record bound to the same native checkout, enabling idempotent reads after pointer
removal; it cannot complete another active cycle or retarget a checkout. It refuses legacy
or remote-delivery records. `final-push` refuses local-only records before its
ordinary delivery machinery; it never silently delegates to completion.

### Schema relationships

| Versioned owner | Exact relationship and compatibility |
|---|---|
| Initiative manifest schema 1 | Existing coordinator/context repository strings and canonical digest algorithm remain unchanged. No inferred Forgejo identity. |
| Initiative manifest schema 2 | Same structural/coverage rules, replacing `coordinator_repository` and each context `repository` with typed Repository Identity objects. Accounts and credentials are absent. Canonical JSON digest includes full typed identities. |
| Initiative receipt schema 2 | Carries typed coordinator and target identities with the existing requirement/dependency coverage and committed manifest/artifact provenance; version is explicit. |
| Native Cycle Record schema 5 | Existing GitHub and historical supported shapes/semantics remain unchanged; no implicit migration. |
| Native Cycle Record schema 6 | Existing native lifecycle fields and evidence ownership, plus the exact local-only delivery object below. It requires `delivery_intent=local`, valid native execution metadata and a schema 2 Initiative receipt/approval. |
| Existing evidence envelopes and gate ledger | Keep existing formats, exact source/gate bindings and approved-exception rules; typed registration is not a replacement trust authority. |
| Local Completion, version 1 | One completion object in the schema 6 record, bound to cycle, repository, comparison base, recorded commits and final source; it confers no remote authority. |

Schema 6 `delivery` has exactly `mode`, `forge`, `upstream`, `remote`, `branch`,
`base_branch`, `base_head` and `lock_id`. `mode` is `local_only`; `forge` has exactly
`provider`, `origin`, `repository`, `account`, `credential_source`, with provider
`forgejo` and credential source `osxkeychain`. `branch` identifies the local task
branch, not a remote delivery request. `base_branch` and `base_head` identify the
explicit comparison base. The existing private Git snapshot binds the selected
remote's fetch and push destinations. `lock_id` binds full typed identity and
native checkout/task branch for local completion serialization; it grants no
remote capability. No `delivery.github`, PR, merge result or published head is
written. Private account selection is not included in public Initiative identity.

The exact `local_completion` object is
`{schema_version:1, cycle_id, repository, base_head, head, tree, recorded_commits, completed_at, manual_delivery}`.
`repository` is typed, `recorded_commits` is the ordered list already validated by
the Cycle Record, all object IDs are valid Git object identities, and timestamp
is UTC. `manual_delivery` is exactly `{status:"pending"}`. The record reaches
`state=completed` only after this object is safely persisted; its `source_sync`
is `{status:"not_applicable", reason:"local_only_completion"}`. Completion output
must say locally validated and manual delivery pending, never pushed or merged.
The existing native record's atomic persistence and pointer removal rules apply.
A crash before pointer removal can be retried only against the same completion.

Readers validate the entire new record before mutation. Old helpers reject
schema 6; no schema downgrade or rewriting of existing records is permitted.
Unknown delivery/completion variants fail safely. Future Forgejo remote records
need a separately settled versioned contract; this slice grants no implicit mode
expansion. Private consumers must verify installed capability before adopting
manifest schema 2 or attempting local-only registration.

## Fetch, approval and completion contracts

The implementation supports macOS and the existing native `osxkeychain`
credential namespace. A get-only Security.framework bridge selects a unique
HTTPS Internet Password item with interaction disabled; it neither invokes an
interactive CLI fallback nor enrolls credentials. The Python executable's
Keychain access must be qualified separately: access granted to another Git
helper does not establish access for this executable. Missing access fails
without a prompt.

First enumerate only attributes and item references for the exact selection.
After one valid match is established, request attributes and password data for
that item reference with a single-item limit, then revalidate its identity before
releasing the credential. Zero, multiple, malformed or changed matches release
no credential. Both reads retain the process-wide and query-level UI denial.
Do not combine password data with an all-items limit: [Apple explicitly rejects
that query for password items](https://developer.apple.com/documentation/security/secitemcopymatching(_:_:)).
The existing data/trust visual table represents both reads inside the same
native lookup boundary; no new source, sink or credential owner is introduced.

The new transport requires Git 2.56 or newer with credential `authtype`
capability support. It supplies only an ephemeral pre-encoded Basic credential
and proactively selects Basic; username/password fallback and negotiation of
other authentication schemes are unavailable. Existing GitHub paths retain their
previous runtime requirements.

 Request the exact HTTPS origin, account and repository path. Resolve the
credential just in time; missing or conflicting selection fails. A supplied or
echoed account and successful fetch are selection/access observations, not proof
of an authenticated API principal, ordinary role or future mutation permission.
Do not require an identity API that this bounded workflow never calls. Production
API principal proof remains unresolved under the complete remote feature.

Controlled Git fetch is restricted to the canonical selected HTTPS endpoint and
explicit base ref, with normal TLS/hostname verification, no redirect or URL
rewrite, no unqualified proxy, no ambient authentication/extra headers/credential
helpers and no inherited tracing/configuration injection. Only the managed exact
Keychain lookup may supply credentials; credential store/erase, enrollment,
interactive prompting and fallback account selection are unavailable. Secrets
stay in private process memory and out of arguments, URLs, Git config, files,
logs, exceptions, evidence and chat. Use a bounded 30-second fetch deadline and
no automatic authentication retries. Failure reports a fixed safe category and
preserves existing authority. Qualify effective Git configuration and destination
binding, not just the command's displayed URL. The transport must not inherit a
repository-configured command, helper, hook or credential-bearing header.

The Git transport keeps its isolated temporary home and XDG directory. Only the
dedicated get-only credential child restores `HOME` from the operating system's
current-UID account record before loading Security.framework, so native Keychain
discovery can find the user's existing login Keychain. Never use inherited
`HOME` or infer the home from the selected Forgejo account. Missing, relative or
malformed account-home metadata refuses before credential lookup. This narrow
native-store binding does not restore Git configuration, XDG state, proxies,
interactive UI or other ambient credentials, and it is not credential enrollment.

Preflight may write only ordinary local fetch objects/tracking-ref state. It
creates no cycle, approval, import commit or remote ref. Bind full typed source
and target identities, selected account/source, exact fetch/push destinations,
base ref/commit, branch/checkout, profile, plan, receipt and changed-document
closure to the launch digest. Registration repeats the controlled fetch and
existing post-consent authority checks. Any changed input invalidates approval.
The task checkout must be clean at that approved base before an allowed Discovery
documentation import; preserve the existing exact-import lineage contract.

`complete-local` requires all required gates passed or an existing explicitly
approved valid Gate Exception, current profile/import/Graphify evidence where
applicable, current README/CHANGELOG reviews, clean task branch, exact recorded
ordered cycle commits and current bound gate evidence. It records HEAD and its
tree after these checks, under the native local serialization lock. It neither
fetches nor requires remote base freshness at completion: its result identifies
the validated source and recorded comparison base, not current remote eligibility.
Remote advancement cannot turn this result into merge permission. Any future
publication reviews its actual source and remote state separately.

Completion Git reads use an isolated environment with transport and lazy fetch
disabled, no system/global configuration, and fsmonitor/hooks disabled. Executable
Git filters in the checkout or initialized submodules refuse completion before
status inspection rather than running arbitrary source-configured programs.
The ordinary legacy delivery path keeps its existing behavior. Schema 6 records
are validated before atomic persistence as well as on read, so malformed mutation
inputs cannot replace a valid record.

Successful local completion retains unpublished work and the ordinary retention
period. The removal check must return an explicit unpublished-local blocker
rather than infer delivery from `state=completed`, a tracking ref or a local
completion object. This slice adds no command to mark manual delivery successful
and no removal bypass. Preserve completed records, uncertain state, failed
evidence and existing worktrees. Downgrade cannot resume a schema 6 cycle through
an older helper; preserve the record and source until a compatible helper is
available. A managed rollback may restore old behavior for old records only.

## Lifecycle and delivery plan

The following table records the approved applicability baseline. The private
Cycle Record owns current execution results and retained failures.

| Gate | Applicability | Result | Exception |
|---|---|---|---|
| Domain | required: typed repository, comparison base and local completion ownership | pending | none |
| Behavior | required: local launch, completion and refusal behavior | pending | none |
| Spec | required: CLI/schema/version and compatibility contracts | pending | none |
| Contract | required: identity, credential selection, approval and zero-write boundary | pending | none |
| Test-driven implementation | required: failing deterministic acceptance before implementation | pending | none |
| Refactor | required: reuse existing owners and remove duplicate validation | pending | none |
| Review/Integrate | required: exact source-candidate review, validation and integration readiness before draft publication; verified remote integration remains a prerequisite to rollout | pending | none |
| Release | not_applicable: no independently versioned package or registry artifact | not_run | none |
| Deploy | not_applicable: source-only cycle installs no unmerged helper; merged installation belongs to the subsequent required rollout | not_run | none |
| Operate | not_applicable: source-only cycle activates no capability; loaded-byte and bounded consumer qualification belong to the subsequent required rollout | not_run | none |
| Maintain/Retire | required: compatibility, rollback and unpublished-work preservation | pending | none |

Build persists a private applicability plan naming
`docs/specs/dbsctr_v3_lifecycle/PROFILE.md` with every gate above exactly once.
The support cycle uses critical risk and existing GitHub `draft_pr` delivery with
the explicitly selected public support account. No global account switch is
required or allowed as a substitute. A current default account is not authority.
Only committed public-safe Discovery documents may enter its import closure.

The source cycle's Final Push publishes its reviewed source candidate through
the existing GitHub path. The separate required rollout starts only after verified
integration and explicit managed-installation authority. Its plan marks Deploy
and Operate required, naming the merged revision and verifying installed/loaded
helper bytes before private consumer use. Source fixtures cannot satisfy those
rollout proofs. Installation is not a prerequisite to publishing the candidate
that must first be reviewed and integrated.

The consumer's later local cycle has its own private profile, plan, source,
preflight and exact approval. Installation is limited to the merged support
revision, through the existing managed distribution; no installation from this
unmerged Discovery branch. The first real qualification exercises safe reads and
local-only completion in separately approved scope, without publication. No
consumer application deployment or remote server change is included.

## Validation and acceptance

Use the existing project-selected publication/instruction authority on the exact
candidate, including new files in its tracked/index inventory before publication:

```sh
uv run --group test pytest tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers tests/test_opencode_control_plane.py tests/test_dbsctr_lifecycle.py -q
```

The primary stages only intended artifacts for that authority; a helper must not
claim untracked files were checked by a tracked-file scan. Manifest validation,
receipt provenance and privacy review remain distinct proofs. Run affected
pytest, Python compilation of changed helpers, `git diff --check`, and applicable
managed configuration rendering. Current CI also runs the explicit native Swift
warnings-as-errors authority and `uv run --group test pytest --maxfail=1`. Bun
checks are conditional on changed TypeScript adapters; no adapter rewrite is
required by this feature.

Acceptance must cover these meaningful boundaries:

1. Full-identity host/provider/port collisions, strict URL/path parsing, case
   rules, mixed selectors, schema 2 expected JSON, and unsupported target modes.
2. Unchanged schema 1 canonical digests, receipts and GitHub schema 5 registration,
   draft delivery and legacy local delivery behavior. Old-helper schema rejection
   and historical record readability remain explicit regressions.
3. Controlled Git reads with exact selected credential lookup, missing/wrong
   selections, redirects/rewrites, configuration/helper/header/proxy injection,
   TLS failure, timeout and sanitized diagnostics. Successful fetch must not be
   misreported as API principal or future mutation authority.
4. Clean linked registration at the approved comparison base, complete exact
   Discovery import, stale source/base/profile/account/endpoint/plan rejection,
   post-consent drift, occupancy and exact resume without renewed consent.
5. Schema 6 validation through native record, gate/evidence, status/history and
   preservation readers; malformed, unknown and incompatible state must fail
   safely rather than skip required evidence.
6. Local completion with exact source/tree/ordered commits, failed/stale gates,
   artifact review, interruption and idempotency. Include configured fsmonitor,
   executable filters, lazy-fetch refusal and invalid outgoing-record mutation. Instrument network/credential
   entry points to prove none execute during completion or local-only Final Push
   refusal. Assert no push/API/source sync/feedback export occurs.
7. Unpublished-local removal blockers and preserved failure evidence; completion
   cannot become publication, remote preservation or cleanup authority.

Existing affected owners include `tests/test_dbsctrctl.py`,
`tests/test_initiative_cli_approval.py`, `tests/test_initiative_local_launch.py`,
native workspace/record tests, lifecycle/distribution/instruction checks and
their implementation owners. Synthetic Git transports, accounts and operator
input establish test behavior only; they do not prove real consent, account
identity, deployment or first-consumer qualification. The primary calculates
the affected closure before Build. Preserve passing replacement evidence and
earlier failures in the registered cycle.

## Visual Evidence

Canonical tables below answer the bounded local-only review questions without
requiring a renderer. They are accessible text evidence; duplicate diagrams would
not add a decision. Owner: lifecycle maintainer. Update them in the same change
when the represented interface, state, trust boundary or delivery order changes.

| Concern | Decision and canonical evidence | Review question |
|---|---|---|
| Boundary | required: Domain and ownership table | Which owner can select credentials, validate source and authorize manual delivery? |
| Interaction | required: ordered interaction table below | Where do fetch, exact consent, local validation and separate manual delivery occur? |
| State | required: transition table below | Which transition completes local validation without claiming publication? |
| Data/trust | required: directional transfer table below | Which data crosses private runtime and public/source authority boundaries? |
| Schema | required: Schema relationships table | Which versions contain typed identity, approval and completion, and which remain unchanged? |
| Dependency/deployment | required: dependency table below | Which prerequisites permit support installation and consumer use? |
| Quantitative | not_applicable: no measured comparison, forecast or threshold claim | No quantitative decision requires a chart. |

| Order | Sender to receiver | Permitted action and guard |
|---|---|---|
| 1 | Discovery authority to lifecycle primary | Read committed safe requirements, typed receipt and profile/plan. |
| 2 | Primary to controlled Git transport | Fetch exact selected base read-only; bind origin, selection and immutable base. |
| 3 | Preflight to operator | Present exact scope/risk/target and launch digest without registration. |
| 4 | Operator to registration | Approve exact digest; registration repeats checks/fetch before native cycle creation. |
| 5 | Native cycle to local completion | Pass required gates and validate exact source/evidence without network activity. |
| 6 | Local result to operator | Retain source with manual delivery pending; later reviewed Git operation needs separate authority. |

**Text Equivalent (interaction):** Read committed authority, fetch the exact base
through controlled read-only Git, and obtain approval of its complete launch
digest before registration rechecks and creates the native cycle. Required local
validation can then complete without network activity. Its retained source is
pending a separately reviewed manual delivery operation.

| State | Guard and transition | Publication meaning |
|---|---|---|
| Specification ready | Complete bounded contracts permit actual preflight | None; no launch is approved. |
| Preflight verified | Exact fresh digest may be presented for operator approval | None; no cycle exists. |
| Active local-only cycle | Exact approval and rechecks permit local gate execution | None; no remote delivery is enabled. |
| Completion refused | Missing/stale/failed evidence preserves active state and failures | None; repair requires existing lifecycle rules. |
| Completed locally | Exact gates/source persist completion identity and remove active pointer safely | Manual delivery remains pending. |
| Completed locally, repeated | Matching recorded identity returns the same result | Still pending; no new publication inference. |
| Retained unpublished work | Removal check refuses local-only unpublished state | Separate delivery/preservation authority is required. |

**Text Equivalent (state):** Specification and preflight are not registration.
Only exact approved registration creates an active cycle. Failed completion
preserves active state and evidence. Successful local completion is terminal for
local validation, idempotent for the same source, and still pending publication;
it cannot authorize removal.

| Source to sink | Data and trust decision |
|---|---|
| Public Discovery to support PR | Sanitized behavior/interfaces and synthetic examples; no private bindings or credentials. |
| Private manifest to receipt | Typed repository and committed provenance; account/credential bytes are absent from manifest identity. |
| Private selector to native Keychain lookup | Exact origin/account/repository selection; lookup grants no API principal or mutation claim. |
| Operating-system account record to credential child | Bind the current UID's native home before Keychain discovery; Git's home, XDG and configuration remain isolated. |
| Lookup to controlled Git fetch | Secret stays in private memory and is released only for exact selected HTTPS destination. |
| Git/profile/plan/receipt to native Cycle Record | Exact non-secret provenance, private selections and gate evidence; no raw provider error or token. |
| Native record to local completion | Validated source/base/tree and pending manual-delivery status; no export. |

**Text Equivalent (data/trust):** Public support artifacts contain generic
contracts only. Private identities and credential selections remain local to the
consumer and runtime record. Only the credential child's native home comes from
the current operating-system UID; the Git transport remains isolated. Secret bytes flow only from exact Keychain lookup
to controlled Git fetch. Local completion retains source evidence privately and
exports nothing.

| Dependency | Permitted successor |
|---|---|
| Settled public Discovery plus exact publication checks | Fresh GitHub support-cycle receipt and actual preflight. |
| Exact support-cycle launch approval | Native DBSCTR implementation and affected validation. |
| Passing support gates and reviewed verified GitHub integration | Approved managed installation of that merged revision on the current computer. |
| Verified installed capability plus private consumer authority/transport | Fresh private local-cycle receipt, preflight and approval. |
| Passing private local gates | Local completion and retained pending manual delivery. |
| Unresolved full Forgejo safety contracts | Full remote automation remains blocked independently of the local-only release. |

**Text Equivalent (dependency/deployment):** Public source must pass its existing
GitHub delivery path before approved local managed installation. The consumer
then proves installed capability and its own private launch/transport authority.
Local validation can complete, while full remote automation remains blocked.
No server guard or consumer deployment is a dependency introduced by this slice.

## Next proofs and unresolved decisions

No unresolved product/interface decision remains within the bounded local-only
specification. The source cycle uses committed authority and its separately
approved exact launch. Its private Cycle Record retains source review, validation,
failures and final delivery evidence. Synthetic fixtures cover identity,
transport configuration, record mutation and local completion; they do not prove
a real Keychain lookup, HTTPS fetch or consumer consent. Verified integration,
managed installation and bounded real-consumer operation remain required rollout
proofs before private activation.

The complete remote feature still owns its unresolved principal proof, trusted
producer/attestation, atomic server safety, loaded health, durable hosting,
all-writer and remote mutation contracts. Neither this amendment nor local
success silently resolves or waives them.
