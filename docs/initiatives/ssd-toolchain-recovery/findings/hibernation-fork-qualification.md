# Bounded hibernation fork qualification

## Selection and baseline

Operator selected bounded fork qualification on 2026-10-08 (INT-039). Context:
`shell_auth_startup`; normative contract: [HIBERNATION.md](../HIBERNATION.md).
No runtime implementation or plugin activation is included in these findings.

Rechecked public upstream release metadata: `dalogax/herdr-agent-hibernate`
v0.4.1 remains latest; inspected commit
`a9eaa028ffaa03d28540026aadfabef117d0bf0f`. License is MIT. The installed Herdr
client/server report 0.9.3, protocol 22, compatible, with no restart required.
The exported native API schema and original upstream clone remain in private
checkout evidence. No transcript or database inspection was needed.

Ran upstream `node --test test/*.test.js`: **25 passed**. These tests encode some
behaviors that conflict with the retained requirements, including focused manual
sleep, startup-dialog success and dropping obsolete recovery entries.

A private read-only VM probe exercised actual upstream functions with mocked
Herdr/process/storage boundaries. Four counterexamples reproduced: missing agent
metadata satisfies exit, changed session satisfies exit, a transition to working
between eligibility observation and process selection is still signalled, and an
unrelated same-kind session consumes the saved wake record as success. No live
pane or process was signalled by these probes. Upstream tests use fake processes.

Repository validation: `initiative-check` accepted all 39 statements and retained
this slice as discovering. The configured publication/instruction contract suite
passed **58 tests**, including the new finding in the Git-index inventory;
`git diff --check` passed. Used the existing project test environment without
installing or updating Python dependencies.

## Source findings

All line references below refer to pinned `bin/hibernate.js`.

| Boundary | Evidence | Required correction |
|---|---|---|
| Positive exit | `waitForExit`, lines 245–252, trusts missing or changed session metadata | Bind and verify the captured process instance and same terminal shell readiness |
| Signal target | `agentPid`, lines 233–242, falls back to foreground process-group leader | Reject an unproven executable/process identity |
| Eligibility race | `sleepPane`, lines 255–274, observes state then separately finds PID and signals | Qualify conditional termination against native lifecycle/focus authority |
| Recovery ordering | Intent written only after termination, lines 276–285 | Persist recovery intent before the irreversible boundary |
| Exact context | Registry at lines 277–284 omits cwd and launch arguments | Preserve reproducible launch context and current session directory |
| Wake ordering | Entry deleted before launch, lines 340–346 | Retain pending intent through interruption and ambiguous completion |
| Exact attachment | Lines 350–355 and 376–378 accept same kind or startup dialog | Positively verify exact conversation and effective launch context |
| Retention | Lines 327–334 and 404–424 drop stale records; lines 115–120 treat parse errors as empty | Retain/quarantine unresolved recovery evidence and fail closed |
| Concurrency | Locks expire by age, lines 142–145 and 304–306 | Prove stale owner before takeover; serialize sleep and wake ownership |
| Idle continuity | Poll loop at lines 483–538 does not reset timers on every observation gap or session replacement | Require fresh continuous eligibility evidence; missed focus transitions need authority |

## Native interface gap

The installed `herdr agent` command group and exported request schema expose
list/get/read/start/prompt/wait and related UI operations, but no conditional
sleep or signal operation. `AgentStartParams` carries kind/name/pane/args/timeout;
it has no explicit cwd or expected session/terminal generation precondition.
`pane.process_info` provides foreground PID, argv and cwd, but that alone does
not establish process-birth identity or session-directory authority.

Read-only observation of the caller confirmed that OpenCode's current session
directory can differ from the foreground client's launch cwd after a native
session move. Retaining process cwd alone therefore cannot qualify exact resume.
OpenCode V2 CLI documentation confirms shared-service, standalone and explicit
server routes are distinct; the candidate must not silently translate them.

Repeated polling narrows but cannot eliminate the check-to-signal race. Herdr's
current public surface does not establish an atomic eligibility interlock, and
shared-server work needs an authoritative OpenCode-side admission check too.
This is an unresolved interface requirement, not a claim that a Herdr-only patch
would solve every concurrency boundary.

## Initial readiness and decision point

**Readiness blocked.** Plugin-only repair of the four original defects cannot
yet substantiate the retained never-sleep-focused/working/blocked contract.
Do not weaken that contract by silently calling a final read atomic.

The initial decision point was broader native Herdr/OpenCode interlock Discovery, or
leave activation deferred. Broader work requires an approved context/repository
map and fresh interface investigation before implementation scope can be fixed.
No native fork, upstream issue, hosted fork or live canary has been created.

### Expanded investigation and subsequent deferral

INT-040 authorized expanded native coordination investigation. Read-only source
inspection pinned Herdr v0.9.3 at
`7b116c05bfda646af39d2524c54e70c751f57ee8` and OpenCode v2.0.24 at
`e7a34f09bfd9134dfade5a8ddb843f7030bc9a69`. Neither upstream source was edited,
built, installed or activated. Relevant boundaries:

- Herdr `src/app/creation.rs:307–356` derives public pane focus from the shared
  active workspace/tab/pane. `src/server/headless/client_views.rs:389–408`
  separately tracks client-specific focus targets. A safe eligibility contract
  needs the appropriate all-client authority, not an assumed single focus flag.
- Herdr's `src/integration/assets/opencode/herdr-tui-session.js:435–450,509–588`
  reports the selected root session through an asynchronous queue. This is
  observation, not a synchronous barrier against server-side work starting.
- OpenCode `packages/core/src/session/run-coordinator.ts:87–145` owns process-local
  execution admission through `run` and `wake`; `awaitIdle` at lines 169–175 waits
  for current work without reserving the subsequent idle interval.
- OpenCode `packages/core/src/session/session.ts:145–178,179–221,246–313` admits
  prompts, starts shell work, and handles compaction and synthetic input through
  distinct paths. `packages/core/src/session/inbox.ts:59–63` exposes an internal
  keyed serialization helper, not a public client-sleep reservation.
- The V2 plugin documentation explicitly excludes synthetic, shell, compaction
  and move controls from prompt hooks. CLI cached state and those hooks cannot
  alone qualify the required cross-process interlock. TUI exit lives separately
  in `packages/tui/src/app.tsx:282–301`.

These observations identify native change candidates; they do not prove a
complete coordinated protocol or establish implementation readiness. A proposed
map assigned recovery integration to dotfiles-ai, focus/process coordination to
Herdr, and work admission/TUI exit to OpenCode. Official-release versus maintained
custom-fork delivery was presented because custom runtime ownership would alter
the selected native update strategy.

**Latest operator decision INT-041:** defer the feature rather than edit
OpenCode and Herdr directly for it now. The proposed expanded context map and
delivery strategy were not selected. No new implementation contexts, Build
slices, launch receipts or external submissions are created. Preserve the
investigation; reconsider only on explicit resumption or official capability
changes. No live plugin registration occurred.

Reviewed the context README and CHANGELOG. Neither receives a completed-cycle
entry: this is unfinished Discovery, not a delivered behavior change. Existing
Host repair, native updates, guest deferrals and failed lifecycle evidence retain
their original authority. No fresh Build receipt or launch digest was issued.
