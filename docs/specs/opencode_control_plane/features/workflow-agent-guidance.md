# Workflow agent guidance and compression evaluation

**SOURCE IMPLEMENTED — runtime qualification remains capability-specific.** Owner: control-plane Discovery
primary. Profile: [../PROFILE.md](../PROFILE.md); risk: elevated; modules:
ML/AI, Security. Covers convergence INT-024–INT-025, INT-028, INT-044–INT-052,
Q-12–Q-13 in the [Initiative](../../../initiatives/dbsctr-workflow-convergence/README.md).
No prompt rollout, install, routing change or measured benefit is claimed.

## Domain and canonical ownership

| Concern | Frozen contract |
|---|---|
| Communication | Canonical installed `caveman` skill selected once through AGENTS; concise prose preserves conclusions, evidence, caveats, decisions and next actions; no full prompt copy is added to this repository |
| Engineering | Canonical installed `ponytail` skill selected once through AGENTS; inspect existing functionality/callers/shared owner, use minimum correct change, retain validation/security/data preservation; distribution provenance is Build acceptance, not invented source ownership |
| Routing | Managed `private_dot_config/opencode/AGENTS.md` selects defaults once; DBSCTR phase instructions reference authority rather than copying full prompts repeatedly |
| Provider overlay | Existing `dot_agents/skills/dbsctr/references/{openai,anthropic}.md`; small verified deltas only, loaded only by corresponding provider-affine primary, never selected merely by model label |
| Compression | RTK command-output filtering and trim-1 query-conditioned line selection are different mechanisms from terse generated prose; research does not enable either |

Review existing prompt loading/duplication before editing. No new repository-root
directories, monolithic prompt replacement or phase-by-phase full-skill injection.
Semantic interviews concern consequences, not every implementation detail.
Native permissions remain enforcement; denied routes stay denied. Delegate only
bounded independent work with explicit ownership and affordable reconciliation;
helpers never register/own cycles or claim gates. Keep Build-GPT OpenAI and
Build-Claude configured Vertex routes; native model-inheriting helpers retain
selected provider. Missing capability is unavailable, not silent family fallback.

Missing canonical skill yields explicit `canonical_skill_unavailable` and no
copied substitute. Preserve substantive native instructions and required safety;
report missing guidance without claiming successful loading. The source-only
deliverable is references/routing and tests, not installing these skills.
Record resolved skill version or content digest through existing qualification
evidence before later distribution. Canonical skills are not forced provider
templates and do not alter the selected primary or globally change default models.

## Public research and minimal provider deltas

Public documents fetched 2026-10-15; external facts, not installed capability:

| Source | Verified public guidance / selected evaluation boundary |
|---|---|
| [GPT-6.1 Sol model](https://developers.openai.com/api/docs/models/gpt-6.1-sol) | ID `gpt-6.1-sol`; tool calling uses Responses, not Chat Completions; `none`/`minimal` reasoning unsupported. Check harness support before proposing parameter changes |
| [GPT-6 model guidance](https://developers.openai.com/api/docs/guides/model-guidance) | Names GPT-6 Astra and GPT-6.1 Sol; recommends one clear instruction, consequential clarification, bounded appropriate testing and model-specific evaluation. Astra observations are hypotheses for Sol, not proven identical behavior |
| [Opus 5.5 overview](https://platform.claude.com/docs/en/models/opus-5-5/overview) | ID `claude-opus-5-5`, including Google Cloud; thinking always on, forced tool use unsupported, thinking blocks tied to model/conversation. Qualify actual Vertex/harness compatibility |
| [Opus 5.5 prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) | Existing Opus 5 prompts remain a starting point; calibrate effort on own evaluations, preserve risky-action confirmation, distinguish progress from completion. No wholesale template adoption |
| [RTK source](https://github.com/rtk-ai/rtk) | Filters command output, includes unfiltered bypass; advertises OpenCode integration with version constraints. Repository documentation is not proof of active supported local integration; API proxy is explicitly out of scope |
| [trim-1 source](https://github.com/caveman-ai/trim-1) | Query-conditioned extraction preserves retained lines/order but drops others; upstream warns dense coding outputs yield limited savings. Omission markers/unchanged fallbacks do not prove evidence recall |

OpenAI reference already says GPT-6.1: no rename-only rewrite. Anthropic reference
already says Opus 5.5 but links Opus 5; correct only the verified current source
link and any evaluated relevant delta. Use **Astra**, never Astro. Public model
IDs/availability do not prove credentials, configured route or runtime behavior.
Do not import upstream autonomy prompts as permission grants or pricing as actual
cost. Keep native approval and gate authority unchanged.

## Frozen evaluation interface and acceptance

Reuse existing local evaluation/performance records; no service, registry or new
CLI flags. Schema 1 is a logical source contract, not installed runtime behavior.
Unknown schema/field refuses mutation and preserves existing evidence. `digest`
is lowercase SHA-256 of canonical UTF-8 JSON (sorted keys, compact separators);
`oid` is a full lowercase Git object ID (40/64 characters by repository format),
`id` matches `[a-z][a-z0-9-]{0,63}`. Counters are integers 0–2^53−1, durations
nonnegative integer milliseconds, free strings UTF-8/control-free ≤256 bytes.

| Record | Exact fields/types and bounds |
|---|---|
| `Fixture` | `{schema_version:1, fixture_id:"workflow-guidance-v1", rubric_version:1, source_commit:oid, digest:digest, provenance:"public"\|"synthetic", cases:Case[]}`; 9–16 unique case IDs; total canonical serialized fixture ≤256 KiB; digest excludes its own field |
| `Case` | `{id, input:string, query:string, required_evidence:[{id, fact:string}], expected_gate_outcome:"pass"\|"block"\|"reopen", secret_sentinels:[{id, value:string}]}`; input ≤16 KiB, query ≤1024 bytes, fact ≤1024 bytes, each list ≤64 unique IDs; sentinel values synthetic and 8–128 bytes; strings in this row override generic bound |
| `Evaluation` | `{schema_version:1, rubric_version:1, fixture_digest:digest, source_commit:oid, model_id:string\|null, provider_id:string\|null, harness_version:string\|null, prompt_digest:digest, arm:"baseline"\|"rtk"\|"trim1"\|"terse", filter_version:string\|null, filter_config_digest:digest\|null, filter_order:id[], attempts:integer, outcomes:Outcome[], usage:Availability, cost:Availability}`; attempts 1–3 per case/arm, outcomes ≤48; order ≤1 until separate stacking approval |
| `Outcome` | `{case_id:id, attempt:integer, recalled_evidence_ids:id[], gate_outcome:"pass"\|"block"\|"reopen", secret_leaks:integer, retries:integer, remediation_count:integer, elapsed_ms:integer\|null, status:"complete"\|"partial"\|"unavailable"}`; attempt 1–3; recalled IDs unique ≤64 |
| `Availability` | `{status:"available"\|"partial"\|"unavailable", source:string\|null, value:integer\|null, unit:"tokens"\|"micro-usd"\|null, reason:id\|null}`; unavailable requires null value and reason; available requires source/value/unit; source identifies authorized measurement authority, never secret/raw runtime content |

Evidence recall is the number of exact expected facts retained divided by all
required facts in that case (at least one per case); ID labels alone do not prove
recall. Synthetic sentinel occurrence in released output increments secret leaks;
the retained private synthetic input is not a leak. Unavailable outcomes retain
expected IDs in the denominator and cannot count as passing replays. Source pins
and rubric changes invalidate comparison digests, requiring a fresh baseline.

Pin tool **source version/content digest** in the evaluation; if installed state
is unavailable, label it unavailable rather than claim user-installed tooling.
No RTK/trim1 install, proxy, API request, remote model evaluation, credentials or
activation is authorized. First evaluation is offline synthetic/public replay
using already authorized local capability; absent capability produces unavailable
evidence rather than new execution authority. Byte counts are not token/billing
measurements. Exact provider effort is part of prompt/config digests and comparable
cohort; effort tuning is evaluated per provider, not a forced primary/model/route
change. Requested model names do not establish their native availability.

| Given | When | Then |
|---|---|---|
| Defaults already load canonical skills | Guidance changes are reviewed | Keep one communication and one engineering authority; preserve required gates and substantive evidence |
| Compaction occurs | Work resumes | Re-read current Git Initiative manifest and referenced authority; compressed summary is not readiness/approval; preserve opaque native compaction/thinking state unchanged |
| Tool/delegation budget is exhausted | More evidence is needed | Report bounded blocker or seek authorized scope; never omit required validation, invent elapsed timing or switch denied routes |
| RTK integration is unknown | Compatibility is researched | Bind executable/source version, active hook/plugin route, command coverage, permission behavior and bypass; report runtime unavailable until qualified |
| Optional filters are evaluated | Approved public/synthetic fixture runs | Keep activation default off; preserve unfiltered evidence/recovery outside filters and test omissions; no default stacking |
| Input is lifecycle authority, approval, gate evidence or opaque native state | A lossy filter is considered | Bypass filtering entirely; no authority/context-state filtering or API/credential proxy routing |
| A provider route fails or is unsupported | Guidance cannot execute | Report unavailable; no automatic family substitution, installs or new helper cycles |

**Text Equivalent (interaction/state):** Resolve canonical guidance and exact
source/model identities, run approved fixture evaluation, compare quality and
available usage, and only then propose a separate activation decision. Drift or
missing capability blocks activation, not this settled source specification.
Compaction resumes from freshly read Git authority and unchanged opaque state.
This contract keeps filters off.

Staged fixture plan, not a mandatory eight-arm factorial: offline unfiltered
baseline versus **one** filter at a time (RTK, then trim1 only if independently
authorized/available). Terse guidance may have a separate single-delta baseline
comparison; do not confound it with filtering. Stacking needs separate approval
after individual quality evidence and a pinned transform order. All activation
defaults remain off, including when tests succeed. Each comparison uses the same
fixture digest, source, rubric, model/effort/harness where relevant and exactly
three paired replays per case when available; unavailable replays stay in the
denominator, not replacement trials. Offline deterministic results do not imply
provider-quality or live-cost results.

Fixture v1 must cover warnings buried in otherwise repetitive output, errors
after success-looking lines, policy exceptions/expiry, synthetic secret sentinels,
mechanical versus material conflicts, hidden dependencies, failed/stale checks,
approval binding and compaction recovery (9–16 cases, no real private evidence).
Each required evidence ID names an exact expected fact in the rubric. Acceptance
requires **100% required-evidence recall**, **zero changed gate outcomes** relative
to the unfiltered expected rubric and **zero secret leaks** on every complete
case/replay; partial/unavailable cases prevent a qualification claim. Filter bypass
tests never transform lifecycle/approval/gate authority, even inside this suite:
test exclusion/routing with synthetic sentinels rather than filter real authority.
Lost warning/error/exception means failed quality, regardless of output reduction.
Report all eligible/complete/partial/unavailable/failed/retried counts and remediation
before latency or provider usage. No savings claim from bytes/4 or tiny samples.
Usage/cache/cost is unavailable until a separately authorized authoritative
evaluation supplies it. Preserve native permission-respecting unfiltered/raw
recovery; do not filter opaque native thinking/compaction or substitute transformed
evidence for gate authority.

## Source ownership, Build acceptance and activation

Inspected routing: `dot_agents/skills/dbsctr/SKILL.md` provider selection and
critical-path sections; managed `AGENTS.md` canonical defaults; provider references
above; existing performance-audit skill. Candidate consumers/tests:
`private_dot_config/opencode/agents/{build-gpt,build-claude,builder-openai,builder-vertex}.md`,
`tests/test_opencode_control_plane.py`, `tests/test_dbsctr_lifecycle.py`,
`tests/test_native_helper_delegation.py`, `tests/test_native_opencode_permissions.py`,
`tests/test_opencode_v2_control_plane.py`, rendered/resolved configuration authorities.
No graph exists in this checkout; authoritative source inspection supplies evidence.

Source-only Build write closure (subject to exact launch approval):
`private_dot_config/opencode/AGENTS.md`, `dot_agents/skills/dbsctr/SKILL.md`,
`dot_agents/skills/dbsctr/references/openai.md`,
`dot_agents/skills/dbsctr/references/anthropic.md`,
`dot_agents/skills/dbsctr-performance-audit/SKILL.md`,
`tests/test_opencode_control_plane.py`, `tests/test_dbsctr_lifecycle.py`,
`tests/test_native_helper_delegation.py`, `tests/test_native_opencode_permissions.py`,
`tests/test_opencode_v2_control_plane.py`. Fixture v1 is embedded synthetic data in
`tests/test_opencode_control_plane.py`, not a new root or installed filter.
Consumer agent files above are read-only; no broad routing/model edits. The new
`dbsctr-pr-review` skill belongs to integration-review's separate write closure.
`prompt-authority` depends on safety-inventory; compression-evaluation depends
on prompt-authority. Existing availability types are reused without requiring the
whole regression-feedback implementation merely to update guidance. Serialize
shared DBSCTR references/tests with other slices.
Native delivery/permissions retain authority; cycle-speed unresolved work/history
is not relaunched or reclassified. Material Build discoveries return
`readiness_reopened` rather than changing normative scope.

Build oracles: routing references canonical skills once with no full prompt copies;
missing skill reports unavailable; provider link delta retains exact route affinity;
denied helper routes stay denied; no global model/default/effort switch; schema
unknown blocks mutation; fixture digest changes on any case/rubric change;
9–16-case coverage and exact recall/outcome/leak thresholds reject deliberately
lost warnings/errors/waivers and secrets; lifecycle evidence and opaque state
always bypass transforms; raw recovery stays reachable with the same permissions;
no stacking or network call/install is implied by research; fixed denominators
include unavailable attempts and never derive cost from bytes. These fixed design
contracts are ready for source implementation without live rollout first.

Later activation separately requires installed skill provenance, effective
route/harness/compaction and permission-negative smokes, pinned RTK active
hook/plugin coverage and bypass, plus approved quality evidence. An absent scoped
RTK source match is not proof of host absence. Unsupported capability stays
unavailable; source readiness never qualifies live filtering. No install or rollout
is part of these source slices. Primary runs configured publication/instruction
authorities in `.github/workflows/test.yml` on the exact candidate inventory and
`git diff --check`. Discovery validation does not pass implementation/runtime gates.

| Gates | Source-only applicability | Result / exception |
|---|---|---|
| Domain, Behavior, Spec, Contract, Test-driven implementation, Refactor; Review/Integrate; Maintain/Retire | required | pending / none |
| Deploy, Operate | not_applicable: source consumption only; required in separately approved runtime activation | not_run / none |
| Release | not_applicable: source consumption, no separately versioned publication | not_run / none |

## Visual Evidence

| Concern | Plan and review question |
|---|---|
| Boundary | required: canonical ownership table; who supplies prose, engineering and permissions? |
| Interaction | required: acceptance table; when may evaluation become activation? |
| State | required: acceptance table; what blocks and what survives compaction? |
| Data/trust | required: acceptance table/evaluation fields; what cannot enter filters or external transport? |
| Schema | required: logical evaluation fields; what binds comparable trials? No new persistent engine |
| Dependency/deployment | required: source closure and research table; which harness/model/filter capability must qualify? |
| Quantitative | not_applicable: staged evaluation is a plan, not measured results; any later chart needs source/denominator/uncertainty |

**Text Equivalent (boundary/schema/dependency):** Canonical skills supply distinct
communication/engineering guidance through managed routing; provider references
add only verified applicable deltas. Native permissions constrain every route.
Versioned fixture/model/prompt/filter identities bind comparisons; unfiltered
evidence and opaque native state stay outside lossy transforms. Existing harness
and filter capabilities must qualify before any activation proposal. Source: this
contract, public sources above and INT-044–INT-052. Owner: control-plane Discovery
primary; update tables/equivalents on loading, schema, capability, trust or ordering
changes. No deployment or measured chart is implied.
