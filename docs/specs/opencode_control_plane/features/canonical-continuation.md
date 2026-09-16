# Canonical Conversation Adapter

Status: specified for isolated implementation after the continuation core.

## Profile And Boundary

Use `../PROFILE.md`, critical risk, Security and ML/AI modules plus Python for
native-identity translation and tests. Owner: dotfiles owner. Deliver a draft PR;
no live enrollment, process restart, or installed configuration change in this
slice. The separate distribution slice owns host-first activation and guest
qualification. Preserve native conversation identity and Plan-to-Build behavior.

Shared state and transitions are owned by
`../../dbsctr_v3_lifecycle/features/canonical-continuation.md`. This adapter is not
a second state machine or an OS sandbox. It mediates cooperating managed sessions
only. Every participating process must load the adapter and revalidate attachment
before cycle mutation; a failed/unmanaged initializer is not a participating
runtime. Existing nonparticipants must be explicitly quiesced before enrollment.

## Native Qualification

OpenCode 1.18.29 was exercised through its installed executable in disposable
homes and a disposable Git repository, using a loopback scripted provider, not
host credentials, production sessions, or delegated model work. Observed:

| Scenario | Evidence |
|---|---|
| Successful read | before and after hooks have exact session/call identity |
| Before-hook denial | no after hook; denied native write creates no file |
| Failed read | before hook only; after is not a finalizer |
| Successful write | before and after hooks; only fixture file created |
| Native bash | before, shell.env and after carry the same exact call identity |
| Message correlation | Native part session ID plus JSON callID selects one exact message before execution |
| Legacy plugin SDK | global.health is not exposed; do not call it in initialization or infer loaded version from an on-disk binary |
| Failed initializer | OpenCode can omit a failed plugin and continue; no enrollment/attachment may rely on assumed plugin loading |

Keep a reproducible body-free probe with the implementation. Distribution must
qualify the native hooks on each deployed platform and during future runtime
candidate validation. A version/help/config-only smoke cannot substitute for
native write-denial evidence. Do not install a new test framework or provider SDK.

## Interfaces And Routing

- Add read-only `dbsctr_preflight({worktree?})`, available to primary Plan and Build.
  It returns bounded core status plus adapter capability availability, without
  attaching, enrolling, claiming a writer or repairing configuration.
- Extend `dbsctr_attach` with optional `mode: reader|writer` (writer default).
  Require a loaded participating adapter. Inspect the explicit or persisted
  target, ask for exact enrollment/quiescence approval if not enrolled, then ask
  separately for a provider transition where required and perform generation-bound
  attachment. Never fall back to legacy attach on a continuation error.
- Add `dbsctr_continuation_recover({worktree?})` and
  `dbsctr_continuation_handover({worktree?,targetSessionId})`. Both use current
  structured identity, exact core binding and typed permission prompts. Model
  arguments never contain an approval boolean or fabricated receipt.
- Permission prompts bind the action, cycle/worktree identity, generation,
  state/record/activation digests, requested mode and target session. Recheck
  after consent. Plan and child sessions cannot invoke mutators. Existing external
  write, Git, DVC and lifecycle permissions remain separate checks.
- Native before/after hooks expose call and session IDs but not message ID. Use
  Bun's existing read-only SQLite capability to project only the unique native
  part's message ID. The core revalidates primary identity. Query only structured
  fields, reject missing/ambiguous identity and never select by newest message or
  timestamp. No session body is exported or retained, and no extra CLI is needed.
- Restore the session's validated execution target before cycle-scoped tools run.
  Use the returned opaque target worktree ID and Git's registered worktree list;
  never accept a returned path or create a missing worktree. Keep the existing
  synchronous cycleTarget map as a cache only, populated after core validation.
- If no route exists, preserve ordinary unenrolled work. If a stored route is
  invalid, do not fall back to canonical main for mutation. Preflight, target
  selection and read-only diagnostics remain available so recovery stays in the
  same conversation.

Complete the core's read-only no-selection case: `continuation-check` without an
explicit target or stored route returns `not_enrolled`, null cycle/target IDs and
`select_target`, without inspecting a canonical checkout as if it were a registry
cycle. An invalid stored route remains an error and never takes this branch.

Loaded adapter registration is process-local capability evidence, never durable
cycle authority. Initialization must not make optional SDK/network calls that can
throw before hooks are registered. Typed attach/enrollment requires registration;
hook failure or missing helper must fail admitted operations closed, not invoke
raw tools as fallback. Managed deployment verifies complete module loading before
enrollment; corrupt/unmanaged runtimes are excluded from the coordination boundary.

## Tool Mediation

The before hook obtains exact native identity, resolves the selected cycle and
validates current authority. Native read/search tools may inspect as readers.
Mutation admission uses a core operation ID bound to session, generation and call.
The after hook finishes only the corresponding successful operation. Error or
missing completion remains outstanding/uncertain; never synthesize success from
an absent callback. Explicit recovery is required before writer transfer.

| Entry path | Treatment |
|---|---|
| Native edit/write | Map canonical-relative paths to the selected cycle; require writer admission and resolved path containment |
| apply_patch | Validate every Add/Update/Delete/Move header; map paths consistently, refuse external or Git-metadata targets; never rewrite content lines |
| bash | Require writer admission even for apparently read-only commands; set explicit cycle cwd, inject the admitted operation ID only into that call's environment |
| shell.env without matching before admission | Refuse direct/unmediated shell execution for a participating route |
| Cycle-scoped typed tools | Restore target cache first; propagate that call's operation identity to child helper execution without changing process-global environment |
| Attach/preflight/recovery/handover | Dedicated control paths; do not wrap them in the ownership operation that they must drain or recover |
| Begin | Dedicated control path; does not silently enroll an existing cycle or waive confirmation; explicit continuation attachment follows new-cycle creation |
| Unknown custom/MCP/code-mode mutators | Refuse for participating routes until separately qualified; never assume a tool is read-only by its name |

Use AsyncLocalStorage for per-call helper environment where needed, not global
process.env mutation. Do not let concurrent calls inherit another call's operation
ID. Preserve native tool approvals; mediation adds checks, never replaces them.
Do not delegate. Native reads outside the selected worktree retain normal read
permissions; native writes must remain inside it. Shell internals are cooperative
and not claimed to be confined by cwd. Detached mutating work is unsupported and
blocks handover until explicitly quiesced.

Advertise the configured worktree registry as a reference derived from the existing
state-root setting and native fallback. Do not hardcode machine paths, broaden
child permissions, or grant access to all unrelated private state. Preserve
operator provider/model choices and existing explicit deny rules.

## Recovery Completion

An idle writer whose process is lost still owns its generation. Exact approved
quiescence recovery must also work for owned/draining state with zero outstanding
operations; otherwise a stopped idle process is permanently irreplaceable.
This completes the shared core recovery contract without automatic lease expiry:
the action still binds current state/generation, retains evidence and fences the
old owner before returning to reader-only. Completed cycles cannot be revived.

## Acceptance

1. An enrolled canonical-home conversation resumes after adapter reinitialization
   with unchanged session ID and validated cycle target, including a model change.
2. Plan can inspect/preflight; Plan, child and foreign identities cannot mutate.
3. A different reader cannot write, steal ownership or finish another call.
4. Native edit/patch/bash routes cannot accidentally write canonical main through
   their structured path/cwd arguments; symlink, traversal and Git-metadata paths
   are rejected. Arbitrary shell isolation is not claimed.
5. Provider and quiescence confirmations bind exact state; denial or state drift
   leaves ownership unchanged. Failure never invokes legacy attach as fallback.
6. Missing adapter registration/helper/identity and unknown mutation entry points
   produce bounded capability failures. Invalid routes remain recoverable through
   dedicated tools without opening another conversation.
7. Failed/cancelled/interrupted calls cannot release someone else's operation or
   permit stale generation mutation; idle lost-owner recovery remains possible.
8. Concurrent operations carry separate helper environments; no global env leaks.
9. Rendered permissions/references work for managed macOS/Linux defaults; source
   checks and fake tool contexts are not substitutes for the native probe.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: sequence below identifies native, adapter and lifecycle authority |
| Interaction | required: sequence below preserves admission/finish ordering |
| State | not_applicable: canonical transitions remain in the linked lifecycle contract |
| Data/trust | required: sequence below limits native projection to exact identity |
| Schema | not_applicable: no new persistent adapter schema; core owns private storage |
| Dependency/deployment | not_applicable: no live deployment in this slice; Initiative owns rollout order |
| Quantitative | not_applicable: no performance comparison is claimed |

```text
Native call (session/call ID)
  -> adapter projects exact message identity
  -> core validates route, actor and writer generation
  -> native permission check + admitted tool execution in cycle target
  -> successful after hook finishes that operation
Failure/missing completion -> retain outstanding evidence -> explicit recovery
```

**Text Equivalent:** Native session/call identity is projected to one exact
message, not guessed. Core validates the route and writer generation before
native permission checks and execution. Only the corresponding successful after
hook finishes the operation. Failure or missing completion retains evidence and
requires explicit recovery. The control-plane owner updates this sequence when
the mediation boundary or native qualification changes.

## Gates And Ownership

Kernel, Review/Integrate and Maintain/Retire are required. Release, Deploy and
Operate are not applicable to this isolated source slice; dependent rollout must
pass Deploy/Operate and existing-conversation recovery. No exception. Use scoped
pytest for control-plane, continuation and touched distribution contracts, Bun
execution, rendered chezmoi validation and the native loopback probe. Preserve
Python 3.12/3.13/3.14 compatibility. No new dependency or private session export.

Build owns the continuation adapter/plugin, typed tools, permissions/reference
rendering, native metadata projection, the bounded no-selection and idle-owner
core corrections and their tests. Discovery owns this feature, the core recovery
clarification, plans and Initiative. Unrelated delivery/merge behavior is excluded.
