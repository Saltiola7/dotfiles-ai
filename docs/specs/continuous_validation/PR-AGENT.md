# PR-Agent advisory review with Vertex

**Readiness: ready for launch preflight; unregistered and uninstalled.** The
operator selected Vertex and interactive authentication on the local computer,
with OpenCode support where available. This contract defines the implementation
slice. Exact digest-bound launch approval is still required before implementation;
this document passes no lifecycle gate and activates no runtime.

## Purpose, scope, and ownership

Add an optional PR-Agent review to the existing Dagger shadow so an opted-in task
can inspect an immutable change before final CI. The existing
[context contract](README.md), [Engineering Profile](PROFILE.md), and
[checkpoint and feedback contract](SESSION-HOOKS.md) retain authority except for
the explicit review capability and completion-notification extension below.

The review check is expensive, advisory, and eligible at checkpoint or manual
requests only. It shares the existing host-wide admission budget. Cheap
edit-triggered checks remain unchanged and never initiate model calls. Review
execution and review-completion feedback each require explicit default-off opt-in.

`continuous_validation` owns the trusted wrapper, snapshot binding, execution
identity, artifact validation, and observations. Distribution retains installation,
pins, private credential configuration, and activation ownership. Each repository
retains affected selection and permitted source scope. Lifecycle and native
control-plane owners retain gates and session transport. Python, Security, ML/AI,
and the existing local-runtime Cloud controls apply. Risk is elevated because a
credential enters the isolated tool process and source can cross a provider
boundary during a separately enabled real review.

This launch covers source delivery, isolated local installation, CLI help and
synthetic-provider qualification. It permits no real Vertex inference, paid
provider call, live private-source upload, GCP compute provisioning, public
listener, global rollout, always-on service, consumer-repository source change,
GitHub review/comment publication, automatic merge, test waiver, or authoritative
evidence reuse. Draft PR publication of the reviewed source is the delivery route.
Real inference requires local interactive authentication, explicit private runtime
configuration, source-disclosure opt-in, and a separately bounded activation.

## Pinned upstream route

PR-Agent release `0.49.0`, source commit
`efdde4afe14aa401a3889012c7f3e9ef3081a430`, supports a
[plain-diff CLI](https://github.com/The-PR-Agent/pr-agent/blob/efdde4afe14aa401a3889012c7f3e9ef3081a430/docs/docs/usage-guide/plain_diff_mode.md)
with local Markdown and structured JSON output:

```text
python -m pr_agent.cli --diff-file /input/changes.diff \
  --output /output/review.md --json-output /output/review.json review
```

The [plain-diff provider](https://github.com/The-PR-Agent/pr-agent/blob/efdde4afe14aa401a3889012c7f3e9ef3081a430/pr_agent/git_providers/plain_diff_provider.py)
needs no hosted PR or GitHub token and does not obtain repository settings through
its provider interface. Plain-diff mode forces `config.publish_output=true` for
local output. Setting it false is not a no-publication control; the local provider,
absence of hosting credentials, and disabled external sinks enforce that boundary.

| Artifact | Immutable identity |
|---|---|
| Official image index | `pragent/pr-agent:0.49.0@sha256:10a8893d5e081be1a5ae825843d9fc14f8e8d59d8a4f61d67c1775415156079f` |
| Linux ARM64 manifest | `sha256:72bf20078583aadb63f4cdb6cf350668d6f622a79ed00cba2d30643ec802d4a4` |
| Linux AMD64 manifest | `sha256:e47e1108778407cd85882cd035f9217f69daae08c8a826617ccb2eb2373b4071` |

The image contains Python `3.14.9` and LiteLLM `1.105.1`. Its relative CLI
entrypoint assumes `/app`; execution from another directory uses the module
command explicitly. Pins and available architecture manifests do not establish
signature verification, native execution, source safety, or ARM/AMD64 equivalence.

Use PR-Agent's native `vertex_ai` model route, with an explicitly configured
supported Claude or Gemini model. The upstream
[model guide](https://docs.pr-agent.ai/usage-guide/changing_a_model/) owns provider
settings; no ambient model or fallback is inherited. PR-Agent calls Vertex
directly. Local OpenCode's API is an agent/session interface, not a documented
compatible PR-Agent inference endpoint. OpenCode-as-model-backend, its separate
hosted Console gateway, and a custom bridge are outside this slice. OpenCode and
Codex receive bounded review references through their existing qualified session
transports; neither supplies PR-Agent authentication or selects its model.

## Interactive authentication and credential custody

Reuse the existing distribution-owned
[`vertex-reauth`](../../../dot_local/bin/executable_vertex-reauth.tmpl) flow. The
operator runs it in a foreground terminal on the Mac and completes its interactive
Google authentication. It targets the configured isolated Vertex ADC and preserves
unrelated default ADC. Do not replace it with a generic unqualified
`gcloud auth application-default login`, create another credential owner, or move
the browser flow into a background worker. Google's
[local ADC guidance](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment)
describes the interactive credential lifecycle; the existing owner selects the
actual local configuration.

Private configuration explicitly selects the isolated ADC, project, location,
exact model ID, and permitted source scope. Required values may remain unconfigured
after installation; that makes real review unavailable, not installation readiness
ambiguous. The controller validates the selected ADC as an owned, single-link,
regular private file with mode `0600`, outside repository source. Repository
adapters cannot select arbitrary credential files, secrets, endpoints, or models.
No service-account-key discovery or alternate credential fallback is permitted.

Native Vertex authentication needs the selected ADC JSON. The controller supplies
it only as an ephemeral Dagger secret mounted into the pinned tool process. The
refresh credential therefore **does enter the isolated worker while that job
runs**; it is not exclusively confined to the Mac. Its persisted owner remains the
Mac's existing isolated credential file. Do not mount a host credential directory
or put credential values in descriptors, arguments, source snapshots, cache keys,
logs, exported artifacts, or session input. Secret mounts must not enter exported
container layers or ordinary files. Enrolled repository adapters already execute
as the user; this feature does not create an operating-system security sandbox.
Only the pinned PR-Agent container receives the explicitly selected secret.

Missing credentials, revoked access, session-control expiry such as `invalid_rapt`,
and refresh failure return an unavailable observation with fixed
`pr_agent_reauth_required` when classified as authentication failure. Other denied
project/model access remains a distinct unavailable diagnostic. Do not include raw
provider errors or credential contents in feedback. The worker never opens a
browser, invokes interactive login, rewrites ADC, or silently retries through
another identity. A foreground instruction points the operator to `vertex-reauth`;
the pending request is not automatically replayed after reauthentication.

## Enrollment, snapshot, and execution contract

Extend enrollment with `reviews_enabled`, default `false`, and a private
`review_config` selected explicitly by `enroll --reviews --review-config FILE`.
The configuration is outside source and validated independently of repository
adapter configuration. Existing enrollments without these fields remain disabled
for reviews. Add `review_feedback_enabled`, default `false`, as the independent
completion-notification opt-in; existing feedback enrollment and qualification
remain necessary. Disabled review capability performs no credential lookup,
container execution, source disclosure, or completion notification.

The closed private configuration has exactly `schema_version: 1`,
`provider: "vertex"`, `model`, `project`, `location`, `adc_file`,
`source_patterns`, `real_inference_enabled`, and `dagger`. The model uses an
explicit supported `vertex_ai/` identifier. Source patterns are bounded positive
relative globs over already captured inputs. The boolean real-inference flag
defaults to false in configuration examples and must be explicit in enabled
configuration. It is independent of review enrollment. The `dagger` object has
exactly `platform`, `engine`, `cli`, `cli_sha256`, and `sdk_python`: it selects
the existing private local engine, checksum-bound CLI and prepared isolated SDK
interpreter. No configuration field supplies an arbitrary image, command,
provider endpoint, environment body, secret value or test fixture.

The shared controller module exposes configuration loading, a reserved
`pr-agent-review` descriptor, bounded patch preparation and execution. A separate
process under the explicitly selected SDK interpreter evaluates the trusted
image strategy. Its closed request carries version, check descriptor, private
log and patch paths, and validated private configuration; it never enters the
repository adapter protocol. Exported `review.md` and `review.json` belong under
the observation log's sibling `.artifacts` directory. Existing artifact lists
retain their relative filenames; completion points to one of those exact files.

The runner adds its own stable expensive review descriptor for opted-in checkpoint
or manual requests. Repository test adapters remain unchanged and never receive
review configuration or credentials. Their existing input allowlists and source
scope remain authoritative for capture. The controller prepares the review before
Dagger execution without passing provider configuration to an adapter.

Construct the patch from the immutable captured base and permitted snapshot,
including approved uncommitted changes. Bind snapshot, base, patch digest, selected
paths, wrapper/configuration, prompt, model and image/platform identities. Never
substitute a live hosted PR head or recalculate against another worktree. Empty
diffs, excluded inputs, unsupported file kinds, oversized inputs and omitted or
clipped files receive explicit dispositions. The initial route is patch-only: no
repository `.git`, host Git metadata, full worktree mount or implicit file
enrichment enters the container.

The existing frozen-project Dagger strategy remains unchanged. Add a separately
typed trusted-image strategy for PR-Agent with a closed configuration contract.
Do not smuggle an arbitrary tool command or credential injection into the old
project route. Trusted controller code selects the pinned tool and secret;
repository code cannot alter that strategy. Preserve existing adapter and
observation compatibility.

Selected engineering defaults are a maximum `256 KiB` patch, `32` changed files,
`32768` input-context tokens, `4096` output tokens and a `300`-second job deadline.
There are zero automatic provider retries and no model/provider fallback.
Oversized requests stop before inference rather than silently broadening or
claiming complete review. These token and concurrency bounds are not a hard dollar
budget. A real pilot must separately select its spend/disclosure scope; cost
telemetry explicitly distinguishes measured or estimated values from unavailable.

Disable ambient settings, repository configuration, external configuration URLs,
output pushes, callbacks, telemetry exporters and optional skill/artifact
injection. Use bounded warning-level private logs and fixed diagnostic errors.
Mark the check uncacheable for this slice, and prevent Dagger execution-cache reuse
from disguising a new provider call by binding a fresh non-secret execution nonce.
Existing request idempotency may return its original retained observation only
with explicit reuse provenance. Uncertain execution is retained and never
replayed automatically.

## Advisory artifacts and same-session completion feedback

Declare `test_identity: not_applicable`; no test IDs, coverage success, or full-CI
parity is inferred. Fresh Markdown and JSON artifacts must validate against the
reviewed upstream output contract, with content digests and explicit omitted or
clipped-file coverage. Bound each exported review artifact to `1 MiB`. A zero
tool exit means only that a valid review artifact was produced. Findings, absence
of findings and partial coverage do not change pytest, security or formal gates.
Missing, malformed or oversized output is unavailable rather than a clean review.

Add the optional closed `runtime.advisory_review` receipt with exactly these
fields. Unknown fields and malformed values reject completion notification.

| Field | Contract |
|---|---|
| `schema_version` | Integer `1` |
| `kind` | Literal `pr-agent-review` |
| `event` | Literal `review_completed` |
| `coverage_disposition` | Literal `complete` or `partial`, derived from validated coverage |
| `artifact_locator` | Bounded absolute private path matched to the permitted exported review artifact path |
| `artifact_sha256` | Lowercase 64-character SHA-256 of that artifact, computed by the trusted review controller after export |

The controller produces this receipt only after successful tool execution and
artifact validation. Existing `runtime.artifacts` remains a list of relative
paths and supplies no digest authority. This feature adds the digest in the
closed review receipt without changing that legacy list. Its locator must remain
inside the owned private artifact root and match the permitted exported path.
Immediately before feedback the dispatcher independently opens the owned regular
file through the bounded private-file reader and recomputes its hash. A missing,
replaced or mismatched artifact is unavailable and cannot produce completion
feedback.
The receipt contains no raw model findings, source snippets, arbitrary message
text or executable instructions. A partial review remains explicitly partial in
both its artifact and completion notification.

This receipt supplies the narrow additional completion-notification event for a
`passed` review observation. It does not introduce a new observation status or
reclassify model findings as deterministic test failures. It is accepted only for
the typed PR-Agent check under explicit review-feedback opt-in, existing enabled
feedback enrollment and qualified exact-session transport. Without that opt-in,
artifacts remain inspectable but no successful-review message is sent. Existing
`failed`/`unavailable` feedback for ordinary checks keeps its current semantics.

Completion notification uses the fixed `pr_agent_review_completed` diagnostic,
private artifact locator, and coverage disposition. Reuse the existing intent
journal, deduplication, task-open, source/enrollment/generation freshness and
immediate pre-send qualification guards. Unknown send outcomes suppress replay;
queue acceptance never proves consumption. No new service, session, competing
resume process or Dagger-to-OpenCode listener is created. Model text remains
untrusted private diagnostic data and grants no automatic repair or delivery
authority. The existing task scope and native permissions still govern agent work.

## Behavior

| Given | When | Then |
|---|---|---|
| Shadow or review opt-in is absent | Edits or checkpoints occur | No review, credential lookup, provider call or review notification occurs |
| Review is enabled for an open task | An edit request arrives | Existing cheap checks run; PR-Agent is not selected |
| A current checkpoint/manual request is allowed | Shared expensive admission is available | One bound review becomes eligible within the existing budget |
| Real inference has not been separately activated | Installation or synthetic qualification runs | No Vertex call or live-source disclosure occurs |
| Required private settings or credentials are missing | Real review is requested | Return unavailable before inference; do not choose implicit defaults |
| Credentials require interactive reauthentication | Worker attempts review | Retain unavailable with a fixed reauth diagnostic; operator authenticates on Mac |
| Repository content requests another credential, endpoint or callback | Review is prepared | Trusted configuration rejects the override |
| Snapshot, base, task or enrollment changes | Execution or feedback is considered | Suppress stale delivery and retain original evidence |
| Image, platform or configured model identity drifts | Review is prepared | Return unavailable without an upgrade or fallback |
| Execution times out or completion is uncertain | Result is collected | Retain interrupted/unavailable or uncertainty; no automatic retry or replay |
| Output is missing, malformed or oversized | Validation runs | Return unavailable; do not imply a valid or finding-free review |
| Valid output omits or clips files | Review completes | Preserve partial coverage and notify only with that disposition |
| A review contains findings | A valid artifact is retained | Preserve advisory findings; deterministic test and gate results remain unchanged |
| A valid review completes and review feedback is opted in | Exact-session guards pass | Queue a fixed completion reference in the existing OpenCode or Codex session |
| Operator disables enrollment | Work is queued or running | Stop admission, cancel owned work where supported, and retain evidence |

## Validation and lifecycle plan

Source delivery is a draft PR. Kernel and Review/Integrate gates are required;
Release is not applicable because this slice publishes no new package or image.
Deploy and Operate cover the explicitly selected isolated installation and
synthetic runtime qualification. Maintain/Retire covers pins, upstream
vulnerability intake, credential custody, revocation/reauthentication, safe opt-out
and retained private evidence. No gate is passed by specification readiness.

Obtain regression evidence for disabled/no-side-effect behavior, denied secret and
configuration overrides, snapshot/base binding, platform drift, no GitHub access,
error propagation, artifact/patch/token bounds, cancellation, uncertain execution,
stale/wrong-session feedback, explicit completion opt-in and legacy failure-only
compatibility. Use synthetic credentials and provider fixtures for denied/expired
auth, secret leakage and receipt validation. Real local Dagger help and bounded
synthetic-provider execution qualify the selected container path. Qualify native
completion transport independently with synthetic session fixtures, active and
idle behavior, and negative identity/freshness cases.

No real credentials are needed for fake-provider qualification. A later bounded
Vertex pilot uses synthetic source first after the operator's local login and
private configuration. It separately measures artifact usefulness, review coverage,
latency, usage and available cost; no quality, model availability, spend, useful
feedback target or native AMD64 result is claimed by the installation slice.
Rollback disables review execution/feedback and safely cancels owned work. Preserve
observations and credentials under their existing owners; deletion, credential
revocation and worker disposal remain separately authorized operations.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: editable plaintext ownership and data-flow diagram below |
| Interaction | required: ordered local login, preparation, admission, execution, validation and notification flow below |
| State | required: transition table below |
| Data/trust | required: diagram identifies ephemeral ADC disclosure, later source disclosure and untrusted output |
| Schema | required: additive advisory receipt contract above; no duplicate schema diagram |
| Dependency/deployment | required: diagram places the pinned tool in the existing local Dagger worker |
| Quantitative | not_applicable: selected bounds are engineering defaults, not measured results |

Review question: where does interactive authentication happen, which owner may
send credentials or source, and how does an existing session receive one review?

```text
Operator's foreground Mac terminal: existing vertex-reauth
  |
  v
Existing isolated Vertex ADC on Mac (persisted credential owner)
  |
  +-- explicit private selection --> trusted controller validation
                                      |
Task review opt-in + immutable base/snapshot + private runtime settings
  |
  v
Trusted wrapper constructs bounded patch and checks real-inference permission
  |
  v
Existing shared expensive admission
  |
  v
Existing private local Dagger worker
  +-- pinned PR-Agent image + patch-only input
  +-- ephemeral ADC secret from trusted controller
  |     |
  |     +-- separately activated inference/source --> selected Vertex model
  |     |                                             |
  |     +<-- untrusted model output -------------------+
  |
  +-- reauth required --> fixed unavailable diagnostic; operator returns to Mac
  |
  v
Trusted artifact validation + explicit complete/partial coverage
  |
  v
Advisory observation + completion opt-in + exact-session freshness guards
  |
  +-- fixed code / private locator / coverage --> existing OpenCode or Codex session

Installation and fake-provider qualification make no real Vertex inference call.
Formal gates and deterministic checks remain separately authoritative.
No hosted PR provider, GitHub token or new session service is present.
```

**Text Equivalent:** The operator authenticates interactively with the existing
`vertex-reauth` command in a foreground Mac terminal. The isolated ADC stays under
its existing persisted owner. Trusted controller validation explicitly selects
that file; an ephemeral secret copy enters the isolated Dagger tool process for
an allowed real review. Task opt-in, immutable base/snapshot and private settings
precede bounded patch preparation and shared expensive admission. Only separately
activated real inference sends approved source to the selected Vertex model.
Its output is untrusted. Authentication failure produces a fixed unavailable
diagnostic and leaves interactive reauthentication on the Mac. Artifact validation
and complete/partial coverage precede an advisory observation. Explicit completion
opt-in and existing exact-session guards permit only a fixed diagnostic, private
locator and coverage disposition in OpenCode or Codex. Installation and fake
qualification make no real inference call; formal gates retain authority.

| State | Permitted transition or terminal disposition |
|---|---|
| Installed, review disabled | No review execution or credential lookup |
| Requested | Validate explicit task/settings/snapshot/source scope and activation |
| Unconfigured or not activated | Unavailable before real inference |
| Reauthentication required | Unavailable; operator runs foreground Mac reauthentication, then makes a fresh request |
| Queued | Shared-budget admission or cancellation |
| Running | Complete, fail, interrupt or retain uncertainty; no automatic replay |
| Validated artifact | Retain findings and complete/partial coverage; evaluate completion feedback |
| Notification eligible | Journal intent, recheck exact target/freshness and queue bounded reference |
| Stale, revoked or uncertain send | Retain history and suppress current or repeated delivery |

Canonical source: this feature contract and the existing context contracts. The
context owner updates the receipt definition, flow, Text Equivalent and state
table together when authentication, secret custody, source disclosure, publication,
admission or feedback boundaries change. Plaintext is directly readable in CLI
and Markdown clients; it makes no Mermaid rendering claim.
