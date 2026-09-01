# Codex History Adapter

**Status:** Ready

## Boundary

`codex-history-adapter` converts stable Codex `0.151.0` app-server responses into
one lifecycle generic history-source envelope in private process memory. It does
not implement review, Incident, telemetry, capture, benchmark, or federation
reducers. It never opens Codex native storage, writes app-server state, repairs
thread metadata, or returns private page content or identity to shell/hosted tool
output.

The internal adapter accepts only the delivered generic schema-1 request through
stdin. The sole public operation is
`codex-control-plane history-probe --request-json -`; it runs the complete adapter
and validator but returns only the six body-free capability fields fixed by
`history-adapter.contract.json`. No generic page, continuation, member ID, thread
ID, digest, timestamps, text, path, provider/model identity, or raw error may
appear.

Every failure exits 2 with empty stdout and the exact bounded stderr line from
the contract. Raw app-server, schema, path, identity, text, and subprocess data
are never interpolated into an error.

Private pages use the exact source object from the contract. Snapshot, page, and
continuation digests use the delivered lifecycle canonical formulas unchanged.
Continuation requests must reproduce that source, frozen membership, overflow,
offset, prior page digest, and current active/archive membership; any difference
is `stale_continuation` before a read.

## Wire Contract

Build must generate the six named schemas with installed
`codex app-server generate-json-schema`, verify every SHA-256 in the contract,
and refuse a release/schema mismatch. It starts the probe-verified
`codex app-server` command, whose frozen default transport is stdio, uses
newline-delimited messages without a `jsonrpc` field, and sends sequential integer
IDs. Initialization uses the exact request and notification in the contract and
does not advertise `experimentalApi`.

The adapter issues the exact active and archived `thread/list` requests in the
contract. Explicit stable source kinds include every frozen source variant;
`useStateDbOnly: true` is mandatory so listing cannot scan or repair rollouts.
The two results are deduplicated by ID and sorted `updatedAt DESC, id ASC`,
independent of server tie ordering. The first 100 form membership. Additional
rows or either non-null `nextCursor` set truthful page `overflow: true`; they do
not invalidate the first bounded membership. A duplicate ID is reduced to
`id`, `sessionId`, `createdAt`, `updatedAt`, `source`, `modelProvider`, `cwd`,
`historyMode`, `parentThreadId`, and `forkedFromId`, then compared with lifecycle
canonical JSON (sorted keys, compact separators, UTF-8, ASCII escaping enabled).
Disagreement is source drift and fails before membership construction.

For the requested offset/limit, the adapter issues one `thread/read` per member
with `includeTurns: true`. Top-level responses must match the pinned generated
schemas. Additive optional `Thread` fields are ignored. Required fields, selected
field types, or known enum discriminators that differ from the pinned contract
fail closed. `historyMode` must be `legacy` or `paginated` and must match between
list and read. Both modes use only stable `thread/read(includeTurns=true)`; every
returned turn must have `itemsView: full`. The adapter never invokes
`thread/turns/list`, `thread/items/list`, or any experimental pagination method.
The frozen `ThreadReadParams` schema explicitly describes `includeTurns` as
"full-history hydration" for paginated threads, and the pinned
`ThreadReadResponse` has no continuation field. Those generated-schema hashes are
the exhaustive-read authority for release `0.151.0`; a changed description or
response shape changes a hash and fails before app-server startup. Absent,
summary-only, or non-full turn items are unavailable rather than silently
truncated.

Each line is bounded to 1 MiB, total stdout to 20 MiB, input to 1 MiB, members to
100, entries to 20, and the whole operation to five seconds. EOF, duplicate IDs,
duplicate JSON keys, malformed JSON, schema mismatch, JSON-RPC error, unexpected
server request, timeout, nonzero exit, stderr overflow, or extra response fails
with one fixed local error class and no raw data. Responses are exactly `{id,
result}` or `{id,error}` without `jsonrpc`; IDs must match the outstanding
request. Bounded server notifications may interleave and are ignored. Any server
request, second response, unknown envelope field, or more than 100 notifications
fails closed.

## Conversion

`Thread.id`, `sessionId`, `createdAt`, `updatedAt`, `source`, `modelProvider`, and
`cwd` are mandatory. Read identity and timestamps must equal list membership.
Timestamps remain Unix seconds and pass safe-integer bounds checks. `cwd` must be
an absolute normalized path, then is discarded. This adapter deliberately emits
workspace `unknown` and `project_digest` as lowercase SHA-256 of UTF-8
`codex-project-v1\0unknown`; project attribution remains owned by the captured
consumer-parity slice. `path`, `preview`, `name`, Git metadata, project identity,
agent nickname/role, and section fields are always discarded. Absolute paths
never enter the page, error, or output.

Stable source maps exactly: scalar `cli`, `vscode`, `exec`, and `appServer` map
directly; scalar `unknown` and object `custom` map to `unknown`; subagent review,
compact, thread-spawn, and other variants map to their matching generic source
kinds, with memory consolidation mapping to `subAgentOther`. `modelProvider` must
equal the contract's fixed `openai` provider and becomes `provider_id`; any other value
is unavailable. `parent_id` is `parentThreadId` when present, otherwise
`forkedFromId`; both present with unequal values is a conflict. All emitted IDs
must satisfy the generic opaque-ID contract.

For either accepted history mode, only turns with `itemsView: full` are accepted.
`userMessage` contributes
only `content` elements whose type is `text` and whose `text_elements` is empty;
each text becomes one generic user content item in source order.
Any image, audio, local image, skill, mention, or unknown user input rejects the
complete operation. `agentMessage` contributes only `text` when `phase` is `final_answer` or
null and `delivery` and `memoryCitation` are null. Stable `commentary` agent
messages are interim output and are discarded without projection.

| Frozen item discriminator | Action |
|---|---|
| `userMessage`, `agentMessage` | Project bounded text as defined above |
| `commandExecution`, `fileChange`, `mcpToolCall`, `dynamicToolCall`, `collabAgentToolCall` | Emit one bounded signal as defined below; never project payload fields |
| `hookPrompt`, `functionCallOutput`, `plan`, `reasoning`, `subAgentActivity`, `imageView`, `sleep`, `webSearch`, `imageGeneration`, `enteredReviewMode`, `exitedReviewMode`, `contextCompaction` | Discard without projection |
| Unknown discriminator | Reject the complete operation |

Content preserves native turn, item, and user-content order. `turn_count` is the
number of native turns. User/assistant counts equal emitted generic content items
exactly.

The adapter supports only `commandExecution`, `fileChange`, `mcpToolCall`,
`dynamicToolCall`, and `collabAgentToolCall` tool items. It emits one signal per
item with `signal_id` equal to the first 24 hex characters of SHA-256 over
canonical JSON `[session_id,turn_id,item_id,type]`; tool is the fixed
`codex.<type>` string and never a native command/name. Native `completed` maps to
generic `completed`; `failed`, `declined`, or `interrupted` map to `failed`, with
failure class `permission` for declined, `network` for failed MCP, `command` for
failed command/file/dynamic calls, and `unknown` otherwise. Recovered is false.
Timestamp is turn `completedAt`, or `startedAt` only when completed time is null;
both null, `inProgress`, contradictory success/error fields, or any unknown tool
variant rejects the complete operation. Tool counts equal
emitted signals and failed signals exactly; no arguments, output, errors, names,
paths, prompts, or model fields are read into the page.

Content or signals above 100 reject the entry rather than truncating. Before page
construction, each candidate text is checked with the delivered generic
validator's exact byte, control, credential, entropy, email, URL, POSIX,
Windows-drive, and UNC lexical predicates. A rejected text item is discarded in
full; the entry's content availability becomes `partial` with fixed reason
`unsafe_text_discarded`. Safe sibling text remains in source order. The adapter
never rewrites, truncates, or emits an unsafe value.

Family ID is `sessionId`. Token and cost values are null with `unavailable` and
the exact fixed reasons in the contract. Content availability is `available`,
including an empty accepted content list, only when no unsafe text was discarded;
otherwise it is `partial` as defined above. Successful tool signals use
`failure_class: none`. Every constructed envelope is sent through a private
stdin subprocess running `dbsctrctl history-source-validate --envelope-json -`;
only its body-free valid status is consumed before probe metadata is emitted.

## Checks

- Fake app-server fixtures cover initialization, exact list/read requests,
  deterministic membership, conversion, and body-free probe output.
- Adversarial fixtures cover pagination, drift, private/unsupported content,
  schema/release mismatch, duplicate/oversized protocol input, timeout, errors,
  and no native-storage or lifecycle-state mutation.
- Host and every managed guest run positive and privacy-negative body-free probes
  before Operate passes.
- The current host's body-free runtime probe confirms paginated history returns
  full item views through stable `thread/read`; no private identity or content is
  retained as evidence.
- The current host's positive body-free probe also covers interim commentary,
  web-search items, and unsafe-text omission with partial availability.

## Visual Evidence

Not applicable. This slice has no view or user-interface change; its only public
result is closed body-free JSON.

## Quantitative Evidence

Build records response/input byte ceilings, five-second deadline enforcement,
100-member/20-entry/100-content/100-signal bounds, exact schema digests, zero
private identifiers or digests in probe output, and host/all-guest probe counts.
