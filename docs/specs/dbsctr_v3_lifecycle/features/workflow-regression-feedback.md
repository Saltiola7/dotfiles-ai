# Workflow rollback and regression feedback

**SOURCE IMPLEMENTED — runtime qualification remains capability-specific.** Owner: lifecycle Discovery primary.
Profile: [../PROFILE.md](../PROFILE.md); risk: critical (privacy and rollback data safety); modules: Python,
Security, Data, Analytics, ML/AI. Covers convergence INT-040–INT-043, INT-047–INT-048
and Q-10–Q-11 in the [Initiative](../../../initiatives/dbsctr-workflow-convergence/README.md).
No Incident creation, publication, runtime measurement or gate result is claimed.

## Domain and frozen interfaces

| Term | Meaning / owner |
|---|---|
| Feature switch | Existing TOML/local policy capability switch, identified per feature; distribution owns configuration/rendering, lifecycle owns evidence semantics |
| Regression observation | Sanitized local finding correlated to release/source commit, config schema/version and enabled feature IDs; correlation is not causation |
| Rollback | Disable optional behavior or restore a compatible release/config; not delete evidence, rewrite records or unmerge delivery |
| Feedback envelope | Bounded local sanitized diagnostic, distinct from a registered native Incident and from PM tickets |

Reuse existing TOML configuration and the existing private lifecycle evidence
envelope under its qualified local persistence owner. No flag service, registry,
controller, scheduler, root directory or new command-line flags. Distribution
owns schema/rendering; lifecycle owns the following logical record semantics.

### Types, optional switches and record schema 1

`feature_id` is lowercase kebab-case, matching
`[a-z][a-z0-9]*(?:-[a-z0-9]+)*`, at most 64 ASCII characters;
`category` matches `[a-z][a-z0-9-]{0,63}`. A `digest` is lowercase
SHA-256 of canonical UTF-8 JSON (sorted keys, compact separators); `commit` is a
full lowercase 40/64-character Git OID of the repository format. Times are UTC
RFC3339. IDs are opaque UUIDv4 strings. All numeric counters are integers
0–2^53−1; overflow reports an error rather than wrapping. All free strings are
UTF-8 and control-free. Unknown versions/fields refuse mutation/export, preserve
the original record and report `unsupported_schema`; read-only readers may show
known metadata plus that status, never rewrite newer data.

Optional feature settings use `{schema_version:1, features:[{feature_id,
enabled:boolean}]}`, at most 64 unique entries, with each `enabled` defaulting
false. This is the normalized internal view of existing typed configuration
switches, **not another feature-flag file or duplicate enable control**. Map stable
feature IDs to the owning typed switch (for example `delivery.enabled` and
`preservation.automatic_remove`) or coherent activation status. The owner's schema
and exact-repository authorization remain authoritative; a snapshot cannot enable
an action. Missing/invalid optional settings disable new optional actions and emit a
bounded diagnostic, not a downgrade of required safety. Authorization, preservation
hooks, redaction, gate validation and approval enforcement are never flaggable.
Disable is reversible only while the installed reader/data formats remain
compatible; it stops new actions, not existing evidence or already merged work.

| Logical type | Exact fields and bounds |
|---|---|
| `FeatureSnapshot` | `{schema_version:1, release_commit:commit, config_schema_version:1, config_digest:digest, effective_enabled_feature_ids:feature_id[]}`; sorted, unique, ≤64 IDs; digest of resolved non-secret effective settings, never raw config/environment |
| `Availability` | `{source:category, status:"available"\|"partial"\|"unavailable", reason:category\|null}`; unavailable requires reason; no sensitive source path/identity |
| `Observation` | `{schema_version:1, observation_id:UUID, category, feature_id:feature_id\|null, snapshot:FeatureSnapshot, signature:digest, summary:string, availability:Availability[], gate_outcome:"passed"\|"failed"\|"pending"\|"not_applicable"\|"unavailable", retry_count:integer\|null, first_seen:time, last_seen:time, occurrences:integer, export_state:"local"\|"pending"\|"published"\|"blocked", issue_number:positive integer\|null}`; summary ≤2048 bytes, availability ≤16 entries, occurrences ≥1, times ordered; unavailable retries use null, not zero |
| `FeedbackPolicy` | `{schema_version:1, external_enabled:boolean, destination:string\|null, consent_digest:digest\|null, payload_scope:"sanitized-diagnostic-v1"}`; disabled default; destination exact GitHub `owner/repository`, ≤256 bytes, no URL/wildcard; enabled requires destination plus explicit standing consent |
| `QueueStatus` | `{schema_version:1, queued:integer, coalesced:integer, dropped:integer, expired:integer, storage_status:"available"\|"unavailable", error:category\|null}`; counters are availability-labelled existing local diagnostics, not a second registry |

Signature is SHA-256 of a canonical **sanitized public/synthetic reproduction
signature**, never a hash of raw secrets/private content. Dedup key is SHA-256 of
`[category, feature_id, release_commit, signature]`. Matching observations update
only occurrences/last_seen and available retry/outcome facts; retain original
failure in the existing evidence authority (later success does not overwrite it).
Observed failure and enabled-feature correlation do not establish causation.

### Bounded local persistence and publication

One queue contains at most **256** observations, each serialized record ≤**16 KiB**,
aggregate ≤**4 MiB**, retention **30 days** from `last_seen`. Use existing locking
and atomic persistence: serialized append/coalesce transaction, fsync temporary
replacement and atomic rename under the same local lock. No unlocked multiwriter
append or new registry. Lock acquisition has a 1-second bound; no retry loop in
safety processing. If the existing owner cannot provide that transaction, writes
remain unavailable until Build supplies it within that owner, never a parallel
store. Interrupted transaction leaves either old or new valid queue, not partial
records. Dedup and expiry happen inside the same lock.

Expire records with `last_seen <= now - 30 days` first; coalesce matches next;
if still full, drop the incoming
record (do not evict unexpired unique evidence). Reject oversized records rather
than truncate safety facts. Report exact coalesced/dropped/expired counts and
bounded `queue_full`, `record_too_large`, `lock_timeout`, `storage_unavailable` or
`unsupported_schema` error. If counters cannot persist, explicitly mark coverage
unavailable, not zero. Safety action proceeds without indefinite feedback writes.
No raw transcripts, private project names/content/config/results, paths, tokens,
prompts, environment or runtime identities are admitted even to this envelope.
Redact **before** persistence and again before export using existing publication/
redaction authority; an unclassified payload is blocked, not “best effort safe.”

External publication is optional through native `gh` and existing reporting
mechanisms, not native Incident mutation. Exact destination and sanitized payload
scope need explicit standing consent; no repeated per-issue approval inside that
scope. Changed destination or payload scope requires new approval. Native GitHub
credentials/permissions remain authority; policy cannot grant them. Policy-off
stops new exports but retains local observations and previously published facts.

Configure `FeedbackPolicy` only at the trusted exact repository's
`workspaces.repositories[].feedback` table; it is forbidden globally. Its
`schema_version`, `external_enabled`, `destination`, `consent_digest` and
`payload_scope` have the exact types above. Absent table means local-only feedback.
The digest records consent provenance, not authentication or a credential grant.

An **explicit flush** has a total 30-second deadline and at most three transient
API attempts, with delays 1 then 2 seconds inside that deadline; native request
timeout is remaining deadline. Authentication/permission/redaction/consent errors
block immediately. Publish at most one issue per dedup key/destination and update
its occurrence count on repeats. Serialize exports under existing local locking;
include a sanitized dedup marker in the issue. After an ambiguous create response,
query that exact marker first; retry creation only if absence is authoritative.
Unknown outcome stays pending for the next explicit flush, avoiding duplicates.
Destination search/read failure never authorizes a second create. Keep failures
local with visible `pending`/`blocked` state; no daemon or background retry service.
An opted-in cycle may invoke this bounded flush automatically as its ordinary
feedback step under standing destination/scope consent; no fresh per-issue prompt
is required. Without that opt-in, publication never occurs automatically.
No native Incident/fork ID may be synthesized.

Native Incident capability is typed `Availability{source:"native-incident",
status:"unavailable",reason:"native-incident-invocation-unavailable"}` until its
operator route is independently qualified. Local diagnostics/external issues
satisfy feedback without claiming a registered Incident. This source-only slice
does not implement or qualify native Incident mutation.

## Behavior and recovery

| Given | When | Then |
|---|---|---|
| Optional feature is disabled | An older enabled-feature record is read | Preserve readability and source identity; no schema/data-loss rollback |
| A sanitized regression or affected gate failure is observed | Rollback is considered | Preserve failed evidence, compare feature/config/source versions and disable only policy-permitted optional behavior; repair still uses approved DBSCTR scope |
| Compatible flag-off rollback exists | Operator/policy invokes it | Stop new feature actions without erasing records, retained work or already-merged outcomes |
| Record reader/config schema is incompatible, irreversible migration occurred, or data format changed | Rollback would lose access/data | Block downgrade, retain evidence and specify explicit migration/backup/restore qualification; flag-off is not a migration |
| Local queue is full or writer fails | A new observation arrives | Bound work; expose dropped/coalesced/unavailable counts and backpressure; never block safety processing indefinitely or silently claim complete coverage |
| External reporting has no exact destination opt-in | Feedback is prepared | Keep sanitized evidence local; no network publication |
| Destination is explicitly approved | Publication is considered | Revalidate allowlist, redact before enqueue/export, deduplicate, enforce finite retries/retention and stop on changed destination or unsafe payload |
| Native Incident invocation remains unqualified | Automated registration is requested | Report typed unavailable reason `native-incident-invocation-unavailable`; no fabricated incident/fork IDs or replacement commands |
| Evidence source is unavailable | Inventory/report is produced | Distinguish unavailable from zero/empty; no direct database/transcript reads or broader private fallback |

**Text Equivalent (interaction/state):** Capture only sanitized bounded local
observations, identify source/config/features, preserve failure, then consider
compatible flag-off rollback. Incompatible migrations block downgrade. Queue
limits produce visible coverage loss. Export requires separate exact destination
approval and revalidation. An envelope never becomes an Incident without the
qualified native invocation route; it grants no remediation/gate authority.

## Reuse, Build acceptance and live activation

Read-only source closure: `dot_agents/skills/{dbsctr-review,dbsctr-incident,dbsctr-backlog,dbsctr-performance-audit}/SKILL.md`;
`dot_local/bin/executable_dbsctrctl` (`command_phase_span`, `command_cycle_performance`,
`command_review_history`, `command_incident_scan`, `agent_analytics_output`);
`tests/test_dbsctrctl.py`, `tests/test_native_cli_projection.py`,
`tests/test_dbsctr_lifecycle.py`, `tests/test_portable_distribution.py`.
Existing review/history completion and maintenance writes retain their distinct
permissions and retention; observation collection does not invoke them.

Audit review, incident, autonomous-improvement backlog and telemetry **availability**
before prioritizing gaps; do not create/read PM Kernel tickets. Use only qualified
sanitized projections. Incident summary availability is not detailed invocation
qualification. Never inspect raw databases, transcripts or private ledgers.
Keep existing unresolved [cycle-speed serial contracts](../../../initiatives/dbsctr-cycle-speed/SERIAL-DELIVERY.md)
and failed history intact; do not relaunch work from stale labels.

Reuse [cycle-performance](cycle-performance.md) and phase-span availability and
attribution semantics. Compare fixed comparable cohorts with the same risk,
method, source, model/harness/config and required quality outcomes. Report complete,
partial and unavailable denominators, gate failures/reopenings, retries and
remediation together. No causal speed/cost claim from an association. Actual
usage/cache billing is unavailable unless authoritative evidence supplies it;
never manufacture cost from bytes or missing attribution.

After activation, collect **CLI-owned operation boundaries** automatically at
registration, evidence recording, gate commit, target reconciliation, Final Push,
bounded CI watch and preservation/removal checks. Reuse the existing phase-span/
private evidence owner and version its reader if an additive event is needed;
do not add a parallel telemetry database. Each event binds operation category,
source release, feature snapshot, valid cycle association when available,
helper-owned start/end timestamps, outcome and availability. Invocation arguments,
raw errors, source paths and private content are excluded. Incomplete/crashed
intervals remain incomplete, not inferred durations. Unassociated failed startup
is a local diagnostic, never a fabricated cycle event.

This measures the invoked helper's wall interval, **not** the primary's complete
autonomous time, provider usage or native actor/call identity. Preserve the
existing timing schema's allowed operation/attribution classes; unavailable native
attribution stays unavailable. Operator/external waits remain separately labelled
when actually known. Expose capture/drop/unavailable coverage together with failure,
retry and remediation counts. Optional telemetry failure cannot block indefinitely
or erase required gate evidence; a failed required evidence write still fails its
gate under the existing lifecycle contract. This is the incremental collection
improvement, not a revival of deferred History/DKS/runtime-adapter work.

Build source write closure (subject to exact launch approval):
`dot_local/bin/executable_dbsctrctl`,
`dot_agents/skills/dbsctr-performance-audit/SKILL.md`,
`dot_agents/skills/dbsctr-review/SKILL.md`,
`tests/test_dbsctrctl.py`, `tests/test_native_cli_projection.py`,
`tests/test_dbsctr_lifecycle.py`, `tests/test_portable_distribution.py`.
Incident/backlog skills remain read-only authorities. Existing `report` mechanism
is reused, not extended into native Incident authority. Distribution configuration
is owned by `storage-config`, not by this slice. `regression-telemetry` depends on
`storage-config`; integration and guidance share the helper executable/test
closure and must serialize edits. Build may record completion evidence only;
material contract changes return `readiness_reopened` to Discovery.

Deterministic Build oracles: unknown schema preserves bytes and blocks writes;
flag-off reads old snapshots unchanged; safety feature IDs cannot be disabled;
incompatible downgrade blocks; 257 unique records drop exactly one; 16 KiB/4 MiB
limits reject overflow, duplicate burst coalesces counts, clock expiry at 30 days
is deterministic; crash injection yields old/new valid queue only; lock timeout
returns within one second; synthetic secret/path/prompt sentinels never persist
or export; missing/changed consent blocks network; fake-clock flush stops after
three attempts or 30 seconds; ambiguous create queries before retry and repeated
flush updates one issue; unavailable Incident and attribution remain unavailable.
These fixed choices are not design questions deferred until implementation.

Report performance on a predeclared comparable cohort (same risk, method,
source/model/harness/config and quality requirements). Denominator is all eligible
attempts, including failed/retried/partial runs, with included/excluded/unavailable
counts and reasons; no four-sample/generalized or causal claim. Public evidence
contains only synthetic/public fixture results, never host/adopter facts. Actual
usage/cache/cost stays unavailable without authoritative, authorized measurements.

Later live activation requires managed persistence/redaction/consent and native
GitHub permission-negative smokes, not a new design decision. No external
publication or Incident mutation is authorized by spec readiness. Primary runs
configured publication/instruction authorities from `.github/workflows/test.yml`
on the exact inventory and `git diff --check`. Discovery validation does not pass
implementation/runtime gates.

| Gates | Source-only applicability | Result / exception |
|---|---|---|
| Domain, Behavior, Spec, Contract, Test-driven implementation, Refactor; Review/Integrate; Maintain/Retire | required | pending / none |
| Deploy, Operate | not_applicable: source consumption only; required for separately approved runtime activation | not_run / none |
| Release | not_applicable: source consumption, no separately versioned publication | not_run / none |

## Visual Evidence

| Concern | Plan and review question |
|---|---|
| Boundary | required: domain/ownership table; who owns config, evidence and Incident authority? |
| Interaction | required: behavior table; when may rollback/export happen? |
| State | required: behavior table; what survives disable, overflow or migration failure? |
| Data/trust | required: record and behavior tables; what crosses local/export boundary? |
| Schema | required: logical record table; what enables compatibility and attribution? |
| Dependency/deployment | required: source closure/qualification above; which existing capability must qualify first? |
| Quantitative | not_applicable: no measured cohort or benefit yet; later charts require source denominators |

**Text Equivalent (boundary/schema/dependency):** Distribution supplies versioned
feature policy; qualified lifecycle projections supply availability-labelled
observations. Local envelopes relate to feature snapshots and bounded feedback
policy; sanitized dedup keys combine matching observations. External export is a
separate opt-in trust crossing; native Incident registration remains unavailable.
Existing readers and telemetry must qualify before feedback activation; native
Incident invocation requires its own independent qualification, not a dependency
for local diagnostics or consented GitHub issues.
Source: this contract, existing skills and INT-040–INT-043/INT-047–INT-048. Owner:
lifecycle Discovery primary. Update tables/equivalents on schema, privacy,
retention, ordering, compatibility or capability changes. No new runtime topology.
