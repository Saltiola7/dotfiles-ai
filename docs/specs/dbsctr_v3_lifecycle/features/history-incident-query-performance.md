# History And Incident Query Performance

## Purpose

Return bounded History and Incident audit evidence without repeatedly scanning,
reducing, or emitting a full candidate population. The lifecycle helper owns
snapshot selection, immutable capture, pagination, reduction semantics, privacy,
and truthful overflow. OpenCode owns subprocess deadlines and model-visible
availability.

| Boundary | Lifecycle helper | OpenCode |
|---|---|---|
| Source access | Selects the immutable population and reads private local authorities | Has no direct database access |
| Reduction | Binds the page, bulk-reduces metrics, and validates summary schemas | Does not recompute lifecycle metrics |
| Availability | Returns valid local output or fails closed | Bounds the subprocess and maps operational failure to typed availability |
| Privacy | Omits private identities and raw text from summary modes | Prevents unavailable or rejected output from entering model context |
| Projection state | Owns private preparation, activation, compaction, invalidation, and retirement | Receives only sanitized availability |

## Ubiquitous Language

| Term | Definition |
|---|---|
| Immutable Page | Candidate identities selected under one validated snapshot, filter set, cursor, and limit before expensive reduction. |
| Aggregate Page | Metrics and distributions reduced only for one Immutable Page without candidate bodies or identifiers. |
| Incident Summary | Bounded counts by allowlisted tool, sanitized failure class, and recovery state without signal identity or evidence. |
| Availability Denominator | Separate available and unavailable member counts carried beside one metric. |
| Materialized Projection | Owner-private, body-free derived session, metric, ordering, and Incident classification state used by aggregate and summary reads. |
| Projection Generation | One immutable full projection built from a single SQLite read transaction and bound to source, schema, privacy, capture time, and row ceilings. |
| Snapshot Refresh | One asynchronous full replacement that leaves the prior ready generation readable until atomic activation. |
| Material Part Row | A first/last-16 boundary row or tool row needed for eligibility, Incident, or recovery; neutral interior rows are reduced into session counters and not retained. |

## Required Behavior

**Scenario: Reduce only one immutable page**

- Given a validated History snapshot, filters, cursor, and limit
- When the caller requests `aggregate_only`
- Then the first request creates or reuses one immutable membership capture
- And continuation requests read that capture without rescanning the live source
- And the helper selects and binds the page before family telemetry or metric work
- And bulk-reduces only page sessions and their bounded families
- And returns no candidate, message, part, signal, or cycle identifiers

**Scenario: Preserve continuation truth**

- Given more eligible members exist after one Aggregate Page
- When the page is returned
- Then snapshot, ceilings, digest, filters, cursor, and continuation remain bound
- And a continuation cannot silently move to another population

**Scenario: Summarize overflowed Incident evidence**

- Given Incident Signal detail exceeds its bounded output
- When the caller requests `summary_only`
- Then the helper returns counts only by allowlisted tool, sanitized failure class,
  and recovered state
- And reports `signal_overflow=true` without estimating hidden frequency

**Scenario: Preserve existing detailed consumers**

- Given a caller omits `aggregate_only` or `summary_only`
- When History or Incident evidence is requested
- Then the existing candidate and detailed response contracts remain unchanged

**Scenario: Activate one exact projection generation**

- Given a source schema with stable `session_id`, `rowid`, and `time_created`
- When one asynchronous refresh reads session, message, and part rows in a single
  SQLite read transaction
- Then it records exact ordering keys and body-free eligibility, metric, and
  Incident classifications
- And atomically activates the generation only after source, schema, privacy,
  coverage, uniqueness, and ordering validation pass
- And stores no source body or model-visible evidence

**Scenario: Keep the prior snapshot available during refresh**

- Given one ready generation and a daily refresh starts
- When the source continues accepting writes or refresh fails
- Then queries keep serving the prior immutable snapshot with truthful freshness
- And only a complete source-, schema-, privacy-, and size-valid replacement
  activates atomically

**Scenario: Serve one ready projection without source payload scans**

- Given an active ready Projection Generation covers one snapshot
- When aggregate History or Incident summary selects evidence
- Then membership, page metrics, distributions, failure classes, and recovery
  come from the projection
- And the ready query reads no source body column
- And selected aggregate source metadata is validated in one bounded bulk query

**Scenario: Refuse an unavailable projection generation**

- Given the index is missing, preparing, corrupt, privacy-stale, source-incompatible,
  or behind the requested part ceiling
- When aggregate History or Incident summary requests population discovery
- Then the helper exits temporarily unavailable without scanning all source payloads
- And returns no partial population, aggregate, summary, or citation-like evidence

**Scenario: Invalidate private indexed identity**

- Given a privacy tombstone invalidates one indexed session family
- When the tombstone commits
- Then captures containing that family are deleted in the same privacy operation
- And the active generation is invalidated before another summary read
- And maintenance rebuilds without the forgotten family before activation

## Interfaces

The lifecycle CLI adds `--aggregate-only` to structured History telemetry and
`--summary-only` to Incident Scan. Aggregate mode reuses the existing
`--capture-id` continuation input; a first request without one persists an
owner-private transient capture under the existing 24-hour retention policy.
Provider adapters expose the corresponding `aggregateOnly` and `summaryOnly`
booleans. Both default to `false`.

`history-source-index-refresh` owns asynchronous full replacement. It opens one
read-only SQLite transaction before selecting ceilings or source bodies, streams
all selected rows into one preparing schema-version-3 generation, commits the
sidecar independently, and retains the prior ready generation throughout. It is
single-flight, accepts no caller rows or tuning arguments, runs for at most 60
minutes, and aborts if private temporary storage exceeds 1536 MiB or available
space falls below 2048 MiB. Failure or termination deletes only the preparation.
It never mutates or checkpoints the OpenCode source. Successful output is exactly:

```json
{"schema_version":1,"state":"ready","captured_at":0,"duration_ms":0,"indexed_sessions":0,"material_rows":0}
```

`history-source-index-status` is the only five-second operational boundary. It
never starts or advances refresh and returns exactly:

```json
{"schema_version":1,"state":"ready","captured_at":0,"age_seconds":0,"covered_part_ceiling":0}
```

`state` is `ready`, `refreshing`, or `unavailable`; unavailable fields are null.
All counts and durations are non-negative signed 64-bit integers. Neither command
emits generation, source, privacy, path, session, message, or part identity.
`history-source-index-maintain` is retired when refresh activates successfully.
Aggregate and summary reads never synchronously refresh, verify, or scan source
payload columns.

Operational index unavailability has one local machine boundary: process status
`75`, empty stdout, and stderr exactly `source_index_unavailable\n`. Missing,
preparing, stale, incompatible, corrupt, and insufficiently covered generations
share this sanitized class. OpenCode owns later model-visible availability.

Aggregate History output preserves the existing schema identity and snapshot
envelope, sets `mode=aggregate`, and contains only:

| Field | Contract |
|---|---|
| Snapshot envelope | Existing snapshot, ceilings, database digest, exclusion digest, and sanitized filters |
| Page envelope | Requested limit/cursor, selected count, and immutable continuation |
| Cohort counts | Primary/child, review/non-review, correlation quality, active/completed, available/unavailable |
| Metrics | Available count, unavailable count, integer-floor mean, nearest-rank p50, and nearest-rank p90 |
| Distributions | Authoritative agent and model counts only |

Metrics cover elapsed milliseconds, tokens, tool calls, tool errors, child
sessions, and available delegation counts. A field with no authority is
unavailable rather than zero.

The exact schema is version 1:

```json
{
  "schema_version": 1,
  "mode": "aggregate",
  "capture_id": "<24 lowercase hex>",
  "snapshot": 0,
  "session_ceiling": 0,
  "part_ceiling": 0,
  "database_digest": "<sha256>",
  "exclusion_digest": null,
  "query": {
    "after": null,
    "before": null,
    "method_revision": null,
    "cycle_filter_applied": false,
    "state": null,
    "context": null,
    "project_digest": null,
    "reviewed_status": null,
    "archive_only": false
  },
  "limit": 25,
  "cursor": 0,
  "selected_count": 0,
  "continuation": null,
  "digest": "<sha256>",
  "cohort": {
    "sessions": {
      "relation": {"primary": 0, "child": 0, "unavailable": 0},
      "review": {"review": 0, "non_review": 0, "unavailable": 0},
      "telemetry_available": 0,
      "telemetry_unavailable": 0
    },
    "correlation_quality": {
      "exact": 0,
      "family": 0,
      "worktree": 0,
      "source": 0,
      "ambiguous": 0,
      "unavailable": 0
    },
    "cycle_states": {
      "active": 0,
      "blocked": 0,
      "abandoned": 0,
      "completed": 0,
      "unknown": 0
    }
  },
  "metrics": {
    "elapsed_ms": {"available_count": 0, "unavailable_count": 0, "mean": "unavailable", "p50": "unavailable", "p90": "unavailable"},
    "tokens": {"available_count": 0, "unavailable_count": 0, "mean": "unavailable", "p50": "unavailable", "p90": "unavailable"},
    "tool_calls": {"available_count": 0, "unavailable_count": 0, "mean": "unavailable", "p50": "unavailable", "p90": "unavailable"},
    "tool_errors": {"available_count": 0, "unavailable_count": 0, "mean": "unavailable", "p50": "unavailable", "p90": "unavailable"},
    "child_sessions": {"available_count": 0, "unavailable_count": 0, "mean": "unavailable", "p50": "unavailable", "p90": "unavailable"},
    "delegations": {"available_count": 0, "unavailable_count": 0, "mean": "unavailable", "p50": "unavailable", "p90": "unavailable"}
  },
  "distributions": {
    "agents": [{"value": "build", "count": 1}],
    "models": [{"value": "gpt-5.6-sol", "count": 1}]
  }
}
```

`selected_count` is the number of members on this page. Each `relation`, `review`,
correlation-quality, and telemetry partition totals `selected_count` independently.
Cycle-state counts count cycle records and may therefore exceed it. A retained
member lacking an explicit `review_session` value is review `unavailable`, not
`non_review`. `telemetry_available` means the member has a schema-valid telemetry
object; absence or invalid source authority counts as `telemetry_unavailable`.
Metric sources are, respectively,
`aggregates.elapsed_ms`, `telemetry.token_total`,
`aggregates.tool_call_count`, `aggregates.tool_error_count`,
an exact page-scoped bulk count of direct child sessions, and
`telemetry.delegation_count`. Truncated detailed child arrays are not a metric
authority. Only non-negative integers are available. Distribution rows count each
authoritative agent or model identity once per member, sort by descending count
then ascending `value`, and omit unavailable identities. Candidate, session, and
cycle ID arrays are absent. `cycle_filter_applied` says only whether a cycle filter
was supplied. The raw cycle ID is bound inside the private capture query and
aggregate digest but neither it nor a reversible standalone digest is returned.

Incident summary output preserves the existing bounded scan snapshot, sets
`mode=summary`, and contains registered-Incident count, total visible Signal
count, `signal_overflow`, and bounded count rows keyed only by allowlisted tool,
sanitized failure class, and recovered boolean.

The exact schema is version 1:

```json
{
  "schema_version": 1,
  "mode": "summary",
  "snapshot": 0,
  "session_ceiling": 0,
  "part_ceiling": 0,
  "database_digest": "<sha256>",
  "incident_count": 0,
  "incident_overflow": false,
  "signal_count": 0,
  "signal_overflow": false,
  "groups": [
    {"tool": "read", "failure_class": "tool_failed", "recovered": false, "count": 1}
  ]
}
```

Counts cover at most the first 100 validated rows in the existing detailed sort
order. The corresponding overflow boolean is true when the 101-row sentinel is
present; no hidden total is estimated. Group rows sum to `signal_count`, sort by
descending count then ascending tool, failure class, and recovered value, and
contain no evidence text.

The tool allowlist is the fixed names `apply_patch`, `bash`, `glob`, `grep`,
`question`, `read`, `skill`, `task`, `todowrite`, and `webfetch`, plus names that
match the exact safe syntax `^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$` and begin with
`dbsctr_`, `dks_`, or `herdr_`. Every other name
becomes `unknown`. Failure classes are `timed_out`, `cancelled`,
`permission_denied`, `service_unavailable`, `invalid_output`, `tool_error`,
`tool_failed`, and `unknown`. Classification reads only a mapping-valued
`state.error`: `code` takes precedence over `name`. A string is normalized by
trimming ASCII whitespace, lowercasing ASCII letters, replacing each maximal run
of ASCII space, `.`, `-`, `/`, or `:` with `_`, and rejecting any remaining
character outside `[a-z0-9_]`. The result maps only exact `timeout`, `timed_out`, `timeout_error`,
`cancelled`, `canceled`, `abort_error`, `permission_denied`, `eacces`, `eperm`,
`service_unavailable`, `unavailable`, `invalid_output`, or `validation_error`
tokens. Otherwise status `error` maps to `tool_error`, status `failed` maps to
`tool_failed`, and every other value maps to `unknown`. Status normalization uses
the same algorithm. Raw error strings are never parsed for classification.
`recovered` retains the detailed-mode rule: a later successful or completed call
with the same validated private raw tool identity in the same session and bounded
snapshot. Recovery is computed before an output tool name is collapsed to
`unknown`, so unrelated unknown tools cannot recover one another.

## Reduction Contract

- Sort numeric available values ascending.
- Use zero-based nearest-rank index `ceil(p * n) - 1`, clamped to the available
  bounds, for p50 and p90.
- Use integer floor for mean.
- Carry available and unavailable denominators beside every metric.
- Permit singleton descriptive output; comparative activation requires at least
  five complete comparable members.
- Select page identities before expensive joins and use bulk queries per authority
  family. Per-candidate database queries are prohibited.
- An immutable reduction cache may reuse only exact snapshot, digest, filters,
  cursor, page, and method identity. Changed identity is a cache miss.

The first aggregate request selects eligible ordered membership from one active
Projection Generation, applies lifecycle and review filters, and persists membership in
the existing immutable capture store. It performs no source body read. Page
selection then reads capture membership and binds ordered hidden page IDs before
resolving projected metrics and bounded lifecycle telemetry. Continuations require
the returned capture ID and remain bound to the captured projection generation.
The subsequent metric work uses projection lookups and a fixed number of bounded
metadata queries whose count does not grow with page size. Aggregate digest identity includes mode
`aggregate-v1`, capture ID, snapshot, ceilings, database and exclusion digests,
canonical filters, limit, cursor, ordered hidden page IDs, and every selected source
identity. A cache is optional; when absent, these values still define immutable
continuation and digest validation.

### Materialized Projection Contract

The projection is the separate owner-private SQLite sidecar
`reviews/history-source-index.sqlite3` under lifecycle review state, mode `0600`,
with symlink and non-owner rejection. It is not part of Git, review
history, backup or federation payloads, transient capture output, or canonical
OpenCode state. Schema version 3 contains immutable full snapshot generations,
cumulative session projections, safe categorical values, and material part rows.

No title, prompt, response, command, URL, credential, environment value, body,
raw error, model output, message ID, part ID, cycle ID, or evidence text is stored.
Raw private session IDs and parent IDs remain owner-local and are never emitted.
Unknown tool identity is stored only as one generation-keyed digest. A private
disposition digest may match existing Incident state but is never emitted.

The exact private schema is:

```sql
CREATE TABLE index_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
) WITHOUT ROWID;
CREATE TABLE index_generations (
  generation_id TEXT PRIMARY KEY,
  state TEXT NOT NULL CHECK (state IN ('preparing','ready')),
  source_device INTEGER NOT NULL,
  source_inode INTEGER NOT NULL,
  schema_digest TEXT NOT NULL,
  privacy_epoch_digest TEXT NOT NULL,
  captured_at INTEGER NOT NULL,
  target_session_ceiling INTEGER NOT NULL,
  target_message_ceiling INTEGER NOT NULL,
  target_part_ceiling INTEGER NOT NULL,
  covered_session_ceiling INTEGER NOT NULL,
  covered_message_ceiling INTEGER NOT NULL,
  covered_part_ceiling INTEGER NOT NULL,
  session_row_count INTEGER NOT NULL,
  message_row_count INTEGER NOT NULL,
  part_row_count INTEGER NOT NULL,
  material_row_count INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  completed_at INTEGER
);
CREATE TABLE index_sessions (
  generation_id TEXT NOT NULL REFERENCES index_generations(generation_id) ON DELETE CASCADE,
  session_id TEXT NOT NULL,
  session_rowid INTEGER NOT NULL,
  parent_session_id TEXT,
  created_at INTEGER NOT NULL,
  last_activity INTEGER NOT NULL,
  eligible INTEGER NOT NULL CHECK (eligible IN (0,1)),
  review_marker INTEGER NOT NULL CHECK (review_marker IN (0,1)),
  project_digest TEXT,
  source_digest TEXT NOT NULL,
  part_count INTEGER NOT NULL,
  tool_call_count INTEGER NOT NULL,
  tool_error_count INTEGER NOT NULL,
  provider_error_count INTEGER NOT NULL,
  child_count INTEGER NOT NULL,
  delegation_count INTEGER NOT NULL,
  token_total INTEGER,
  PRIMARY KEY (generation_id,session_id),
  UNIQUE (generation_id,session_rowid)
) WITHOUT ROWID;
CREATE INDEX index_sessions_membership
  ON index_sessions(generation_id,eligible,last_activity DESC,session_id);
CREATE TABLE index_session_values (
  generation_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('agent','model')),
  value TEXT NOT NULL,
  PRIMARY KEY (generation_id,session_id,kind,value),
  FOREIGN KEY (generation_id,session_id)
    REFERENCES index_sessions(generation_id,session_id) ON DELETE CASCADE
) WITHOUT ROWID;
CREATE TABLE index_rows (
  generation_id TEXT NOT NULL REFERENCES index_generations(generation_id) ON DELETE CASCADE,
  part_rowid INTEGER NOT NULL,
  session_id TEXT NOT NULL,
  part_time INTEGER NOT NULL,
  material_kind TEXT NOT NULL CHECK (material_kind IN ('boundary','tool','both')),
  eligibility_flags INTEGER NOT NULL,
  tool_name TEXT,
  tool_key_digest TEXT,
  tool_state TEXT CHECK (tool_state IN ('success','failed','other')),
  failure_class TEXT,
  disposition_digest TEXT,
  PRIMARY KEY (generation_id,part_rowid)
) WITHOUT ROWID;
CREATE INDEX index_rows_ascending
  ON index_rows(generation_id,session_id,part_time,part_rowid);
CREATE INDEX index_rows_recovery
  ON index_rows(generation_id,session_id,tool_key_digest,part_time,part_rowid)
  WHERE tool_key_digest IS NOT NULL;
CREATE INDEX index_rows_incident
  ON index_rows(generation_id,tool_state,part_time DESC,part_rowid DESC)
  WHERE tool_state='failed';
CREATE TABLE active_generation (
  singleton INTEGER PRIMARY KEY CHECK (singleton=1),
  generation_id TEXT NOT NULL REFERENCES index_generations(generation_id)
);
```

`index_meta` contains exactly `schema_version=3`. Digests are lowercase SHA-256;
generation and session IDs use existing private opaque-ID validation. Every count,
ceiling, rowid, and timestamp is a non-negative signed 64-bit integer. Nullable
metric authority is unavailable, never zero. `eligibility_flags` records only the
fixed DBSCTR, Discovery, QA, and review marker classes. `tool_name` is the same
sanitized allowlisted output class used by Incident summary. Session
`source_digest` binds the ordered cumulative source snapshot and body digests
without retaining any body or neutral interior row.

Eligibility bits are `1=DBSCTR`, `2=Discovery`, `4=QA`, and `8=review marker`;
unknown bits are invalid. A session is eligible when its exact first/last-16 flags
or safe agent value satisfies the existing detailed-mode seed rule. Project,
source, tool-key, and disposition digests use lowercase SHA-256 except the existing
24-hex disposition identity. Parent IDs are null or valid private opaque IDs.
Agent/model values use `^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$`; message model values
use the same syntax and provider errors are `0` or `1`; failure classes use
the exact summary allowlist. A non-tool row has null tool fields. A failed tool row
has tool name, key digest, failure class, and disposition digest; a successful tool
row has tool name and key digest but no failure or disposition value. Session
counters are complete cumulative non-negative values at that generation; only
`project_digest` and `token_total` may be null for unavailable source authority.
`material_kind` proves why a part row is retained; a neutral interior row has no
sidecar row and contributes only to complete session counters and snapshot digest.

Each refresh starts a read-only SQLite transaction before selecting row ceilings.
That transaction is the immutable source snapshot: concurrent WAL writers may
continue, but every session, message, part, body, and timestamp read by the refresh
comes from one consistent view. A process exit cannot resume that transaction;
the next run deletes only the preparation and starts a new full refresh. The prior
ready generation remains query-visible throughout.

The refresh streams source rows once. Session scalar columns supply token,
project, agent, and model values. Message bodies contribute safe model values,
provider-error counts, marker flags, and the cumulative session digest without a
persisted message row. Part bodies contribute complete counters, marker flags,
tool/failure/recovery classifications, and the cumulative session digest. The
builder retains only each session's exact first and last 16 ordered part rows and
all tool rows; overlap is one `both` row. Neutral interior bodies and identities
are discarded after reduction. Equivalent source snapshots produce byte-identical
session and material-row projections regardless of SQLite fetch chunk size.

Before activation, the refresh validates exact schema, source file identity,
captured ceilings, row counts, uniqueness, foreign keys, material-row reasons,
forbidden-byte absence, final size, and the unchanged privacy epoch. Activation
holds the exclusive review lock only for that bounded comparison and active-pointer
swap. A privacy change discards preparation. Source writes after the read
transaction began do not invalidate the historical generation; they belong to a
later refresh. Source replacement, incompatible schema, corruption, or privacy
invalidation makes the projection unavailable.

Readers use only one active ready generation. A first aggregate request binds its
capture to that generation; later activation never changes the continuation.
Capture-bound older generations remain until their final capture expires or is
deleted. Unreferenced preparations and prior generations are retired after a
successful activation. The status command exposes capture time, age, and covered
part ceiling without private identity. Ready aggregate and summary paths read no
source body column; the OpenCode source remains canonical while the projection is
an immutable derived snapshot.

Incident summary selects at most 101 projected failed rows in detailed sort order,
excludes private disposition digests, classifies only sanitized tool and failure
values, and resolves recovery through a later projected success with the same
private session and tool-key digest. It reads no raw state or error body. Detailed
Incident mode keeps its existing source path unchanged.
The recovery and Incident indexes are partial by contract: non-tool rows consume
no recovery-index entry, and non-failed rows consume no Incident-index entry.
Changing either predicate is a private schema incompatibility and requires rebuild.

Privacy forgetting deletes dependent captures and invalidates any generation
containing the forgotten family in the same exclusive-lock operation. A changed
privacy epoch is always stale. Expired transient captures do not keep a generation
alive. Source disappearance or replacement leaves the projection unavailable; it does
not serve stale membership.

Schema versions 1 and 2 are rebuildable cache state, not migrated authority.
Upgrade and rollback delete only incompatible sidecars and rebuild the selected
schema from source.
Detailed modes continue unchanged. Aggregate and summary modes return
`source_index_unavailable` until refresh activates a fresh compatible
generation. Retirement removes preparations and unreferenced ancestors after all
dependent captures expire or are deleted. On the representative source, the
version-3 final sidecar must remain at or below 1 GiB; temporary preparation may
not exceed 1536 MiB.

The persisted capture is a derived read-side cache, not review, Incident, cycle,
or gate state. The lifecycle helper owns its owner-private directory, existing
exclusive review lock, atomic publish, 24-hour retention, exact query/source
identity, and deletion when source privacy tombstones invalidate a member. A
failed create publishes no capture and returns no partial page. Cleanup may remove
only expired, unreferenced captures. This bounded cache does not authorize a
review marker, Incident disposition, lifecycle transition, or other canonical
write, so the typed operation remains permission-classified as read-only.

## Privacy And Failure Contract

Summary modes contain no prompt, response, command, URL, credential, environment
value, absolute path, candidate identity, message identity, part identity, Signal
identity, cycle identity, or raw error. Failure classes and tool names come from
an allowlist; unknown values aggregate as `unknown` rather than retaining text.
Invalid snapshots, continuations, filters, or schemas fail closed. Missing source
authority remains explicit unavailable evidence.

Refresh may parse private bodies only inside its source-local read transaction.
It does not hold the review lock while scanning. Persisted cumulative digests are
one-way SHA-256 values and are never emitted.
Stored model and agent values must pass the existing safe identifier syntax;
stored tool names use the Incident output allowlist, while raw tool correlation
uses a generation-keyed digest. A schema violation, forbidden column, unsafe file,
or forbidden cleartext byte makes the projection unavailable rather than partially
readable.

`history-incident-query-performance.schemas.json` is the normative closed-schema
authority. Every object rejects unknown properties; integers are non-negative and
bounded to signed 64-bit range; digests and opaque values match their declared
patterns; arrays are bounded and unique. Prose invariants such as partition sums,
sort order, percentile formulas, digest derivation, and continuation greater than
cursor apply in addition to JSON Schema validation.

Incident summary validates all selected rows before sentinel counting. Any
malformed selected row fails the summary instead of being skipped. One hundred
valid rows means no overflow; 101 valid rows means count 100 and overflow true.

## Visual Evidence

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | required: ownership table | Which context owns reduction versus subprocess availability? | Purpose and Interfaces | Ownership change |
| Interaction | required: sequence diagram | Does a ready query select and reduce from the projection without source payload scans? | Required Behavior and Reduction Contract | Query-order change |
| State | required: transient capture and snapshot-refresh lifecycles | Can refresh, activation, stale serving, invalidation, continuation, expiry, and failed publication be distinguished? | Reduction Contract and state diagrams | Capture or projection lifecycle change |
| Data/trust | required: flowchart | Can private candidate or signal identity reach aggregate output? | Privacy And Failure Contract | Privacy-boundary change |
| Schema | required: field tables are the accessible canonical schema | Which fields are present in summary modes? | Interfaces | Response-shape change |
| Dependency/deployment | not_applicable: existing helper and typed adapters are extended | - | Purpose | Runtime dependency change |
| Quantitative | not_applicable: formulas are contracts, not comparative evidence | - | Reduction Contract | Formula change |

```mermaid
sequenceDiagram
    accTitle: Page-first History reduction
    accDescr: A first aggregate read creates membership from one ready private projection and persists an immutable capture. Continuations use that capture and its bound generation. Both bind a page before projected reduction and never scan source payloads.
    participant C as Local caller
    participant H as Lifecycle helper
    participant P as Private projection
    participant K as Transient capture cache
    alt first aggregate read
        C->>H: Aggregate request with filters
        H->>P: Validate generation and select membership
        H->>K: Atomically publish immutable capture
    else continuation
        C->>H: Aggregate request with capture ID and cursor
        H->>K: Read immutable membership
    end
    H->>K: Select and bind bounded page
    H->>P: Resolve projected metrics and distributions
    P-->>H: Body-free page evidence
    H-->>C: Aggregate page, capture ID, and continuation
```

**Text Equivalent:** On a first aggregate read, the lifecycle helper validates one
ready Projection Generation and atomically persists immutable ordered membership. A
continuation reads that capture and the generation it binds. Both paths select one
page before resolving body-free projected metrics and bounded lifecycle evidence,
then return aggregate metrics, capture ID, and continuation without identities.

```mermaid
stateDiagram-v2
    accTitle: Transient aggregate capture lifecycle
    accDescr: A first read either atomically publishes a ready capture or leaves no capture; ready captures serve continuations until expiry or privacy invalidation, then cleanup removes them.
    [*] --> Preparing: first aggregate read
    Preparing --> Ready: atomic publish
    Preparing --> [*]: failure leaves no capture
    Ready --> Ready: continuation read
    Ready --> Expired: 24 hours elapsed
    Ready --> Invalid: privacy tombstone
    Expired --> [*]: cleanup
    Invalid --> [*]: cleanup
```

**Text Equivalent:** A first aggregate read prepares a capture. Successful atomic
publication makes it ready; failure leaves no capture. Ready captures serve
continuations until 24-hour expiry or privacy invalidation, after which cleanup
removes them.

```mermaid
stateDiagram-v2
    accTitle: Materialized snapshot refresh lifecycle
    accDescr: A daily single-flight refresh reads one immutable SQLite transaction while the prior generation remains ready. Complete validation activates the replacement atomically. Failure discards only preparation; privacy invalidates active state.
    [*] --> Preparing: start full snapshot refresh
    Ready --> Preparing: daily refresh; keep serving Ready
    Preparing --> Ready: validate and atomically activate
    Preparing --> Ready: refresh failure; retain prior Ready
    Preparing --> [*]: first refresh fails; no projection
    Ready --> Invalid: privacy, source identity, schema, or integrity failure
    Invalid --> [*]: delete incompatible generation
    Ready --> [*]: retire unreferenced prior snapshot
```

**Text Equivalent:** A daily single-flight refresh reads one immutable SQLite
transaction into a preparing generation while the prior generation remains
readable. Complete source, privacy, size, and integrity validation activates the
replacement atomically. Refresh failure retains the prior snapshot; a failed first
refresh leaves projection reads unavailable. Privacy, source identity, schema, or
integrity failure invalidates affected state, and unreferenced snapshots retire.

```mermaid
flowchart LR
    accTitle: History and Incident summary trust flow
    accDescr: Private source bodies are parsed only inside one snapshot refresh transaction and never stored. A body-free private projection feeds page-first aggregate and Incident summary reducers. Only allowlisted counts, metrics, availability, overflow, and continuation reach local typed consumers.
    S[Private source bodies] --> M[Snapshot refresh]
    M --> P[Body-free private projection]
    P --> R[Page-first local reducer]
    R --> A[Allowlisted aggregate fields]
    A --> T[Local typed consumer]
    S -. bodies and identities never .-> T
```

**Text Equivalent:** Snapshot refresh parses private source bodies locally and
stores only body-free derived projection rows. Aggregate and Incident reducers read
that projection and emit allowlisted metrics, counts, availability, overflow, and
continuation. Source bodies and private identities never enter aggregate output.

## Validation

- Fixtures prove page selection precedes metric and family reduction.
- SQL-trace evidence rejects per-candidate access and every ready-path source body read.
- Snapshot and continuation fixtures reject changed populations.
- Aggregate fixtures cover empty, singleton, unavailable, mixed, and five-member
  cohorts with exact mean/p50/p90 results.
- Incident fixtures prove allowlisted grouping, unknown collapse, truthful
  overflow, and absence of forbidden identities.
- Existing candidate and detailed-mode fixtures remain byte-compatible.
- Sidecar fixtures prove one-transaction snapshot consistency, exact 16-row
  boundary parity, material-row retention, prior-snapshot availability, failed
  refresh rollback, capture-bound prior stability, privacy invalidation, source
  replacement rebuild, symlink and permission rejection, and forbidden-byte absence.
- Projection fixtures prove membership, metric, model/agent distribution, Incident
  failure/recovery, disposition, and digest parity with the detailed source path.
- Privacy fixtures prove forgetting invalidates dependent captures and generations
  before another read.
- On a representative large source, five post-warmup aggregate and Incident
  summary runs each complete with p95 below 30 seconds, no detailed-result drift,
  no source body in the sidecar, and a final sidecar size at or below 1 GiB.
  Refresh completes within 60 minutes with preparation below 1536 MiB; status
  settles below five seconds and reports truthful freshness.

## Gate Ledger

| Gate | Applicability | Result | Authority |
|---|---|---|---|
| Domain | required | pending | Lifecycle README and Initiative manifest |
| Behavior | required | pending | Page, summary, overflow, and compatibility scenarios |
| Spec | required | pending | Interfaces, reduction, privacy, and visual contracts |
| Contract | required | pending | Helper and OpenCode ownership boundary |
| Test-driven implementation | required | pending | Focused lifecycle helper fixtures |
| Refactor | required | pending | Query-count and duplicated-reducer review |
| Review/Integrate | required | pending | Diff, privacy, downstreams, and affected QA |
| Release | not applicable: no versioned artifact is published | not_run | Engineering Profile |
| Deploy | required | pending | Managed helper source identity |
| Operate | required | pending | Bounded live aggregate and Incident summary smoke |
| Maintain/Retire | required | pending | Detailed-mode compatibility and cache invalidation |

## Non-Goals

- Exporting raw History or Incident evidence.
- Replacing immutable pagination with one unbounded aggregate.
- Changing review completion, Incident mutation, or privacy dispositions.
- Claiming causal performance improvement from mixed cohorts.
- Mutating the OpenCode database or requiring a source-owned index or migration.
