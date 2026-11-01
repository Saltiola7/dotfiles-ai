# Sandbox Command Deadlines (PY-05)

Status: Discovery-ready target contract. Implementation, source integration and
runtime qualification are pending. Context: `dotfiles_ai_distribution`. Owner:
project maintainers. Engineering Profile: [PROFILE.md](../PROFILE.md). Existing
[Product Intent](../PRODUCT.md) remains authoritative for managed workspace
journeys and private-data boundaries.

## Problem And Evidence

The existing `command` helper in `dot_local/bin/executable_sandbox-vm` creates
stdin/stdout/stderr pipes, starts a monotonic deadline, then writes and closes
all input synchronously before draining output or checking that deadline. A child
that stops reading stdin can block the controller indefinitely. A child that
writes output before reading input can also prevent both sides from progressing.

Source inspection at `12f5959701f8c075699b69ee5b4bac2cc5c2c535` confirms this order.
The Python audit's isolated extracted-helper probe supplied 4 MiB to a local
non-reading child with a 0.2-second timeout; an independent watchdog expired after
approximately one second. This proves the helper-level failure, not its frequency
in Lima or a full controller/guest integration result. Existing tests cover safe
nonzero diagnostics and output overflow but do not exercise blocked stdin.

Relevant consumers upload guest configuration, Codex helper bytes and bounded
transaction JSON, and transport private Tailscale/PostgreSQL input. Other commands
use the same helper for provisioning, status and history. Caller recovery owns
guest state and transaction reconciliation.

## Scope And Profile Overrides

| Concern | Decision |
|---|---|
| Deliverable | Repair the existing helper and its focused tests/contracts in one source pull request |
| Risk | Elevated: process lifetime, private input and update/recovery behavior share this helper |
| Modules | Existing Python, Security and Cloud guidance; resource management, resilience and testing techniques apply |
| Runtime | Existing Python `>=3.12`; standard library and current pytest authority; no dependency or checker migration |
| Platform | Managed controller on Apple Silicon macOS, calling existing Fedora aarch64 Lima guests; Linux excludes the installed controller |
| Compatibility | Preserve synchronous signature, caller timeouts, output cap, decoding, environment and safe failure contracts |
| Delivery | Source PR only, selected explicitly; local deployment and live operations are separate |
| Implementation boundary | `dot_local/bin/executable_sandbox-vm`, `tests/test_lima_sandbox.py`, and these existing context artifacts |

A shared subprocess framework, package extraction, async rewrite, signal-handler
framework, input-size policy change, updater redesign, new retries and VM lifecycle
redesign are outside scope. Other Python-audit findings retain their own slices.
No new public CLI flag, configuration key, persisted state or error schema is needed.

## Domain And Ownership

- **Invocation:** one existing synchronous `command` call and its local child.
- **Execution deadline:** one absolute monotonic deadline established immediately
  after successful `Popen`, before subsequent selector and descriptor configuration;
  setup, input transport, output capture and final child wait consume that same budget.
- **Cleanup allowance:** at most one additional second of deliberate waiting in
  total after a failed/interrupted invocation. It is separate from the execution
  deadline and never restarts per cleanup action.
- **Capture bound:** the existing combined 256 KiB of raw stdout and stderr.
- **Owned resources:** the created local process/session, its created pipe ends
  and selector. Inherited stdin is borrowed and must not be closed or altered.
- **Known incomplete input:** remaining bytes could not be accepted by the local
  pipe because the child closed it or another write failure occurred. Successful
  pipe writes do not prove that a guest processed or committed the input.

The controller owns bounded local transport and cleanup. Lima/guest commands own
remote effects; callers retain restoration, rollback and reconciliation policy.
Termination of a local process group does not establish remote cancellation,
rollback or safe replay. Escaped/detached descendants are outside that group.

## Required Behavior

1. **PY05-001 — One execution budget.** Input writes, output reads, EOF handling
   and final wait must make bounded progress or fail against the same deadline.
   Active traffic does not extend it. A non-reading child cannot strand a blocking
   writer outside deadline enforcement.
2. **PY05-002 — Duplex progress.** Readable stdout/stderr and writable stdin are
   serviced without one channel indefinitely starving the others. Partial writes
   preserve input byte order and content. Close owned stdin after the final byte;
   explicitly empty input sends EOF without waiting for output first.
3. **PY05-003 — Success compatibility.** Preserve
   `command(argv, timeout=30, input_data=None, environment=None)`. `None` retains
   inherited stdin; bytes use an owned pipe. A supplied environment replaces the
   child environment as before. Success requires complete local input transport
   when supplied, both captured streams reaching EOF and child exit zero within
   the execution budget. Return stdout decoded with replacement and stripped as
   before. Do not return captured stderr on success.
4. **PY05-004 — Live output bound.** Enforce the combined raw stdout/stderr bound
   while the child runs. Exactly the cap is permitted; exceeding it fails with
   the existing output-bound diagnostic. Retention and pending buffers remain
   bounded. Preserve existing nonzero-exit diagnostic restrictions.
5. **PY05-005 — Owned cleanup.** Register cleanup from each successful acquisition.
   Close every owned pipe and selector on success, partial setup failure, timeout,
   I/O failure and interrupt. Failure cleanup retains immediate local process-group
   termination, direct-child fallback when group signaling is unavailable, and a
   bounded direct-child reap attempt. One cleanup failure must not prevent other
   cleanup attempts or replace the primary error/interrupt with success. If cleanup
   itself is the first failure, fail rather than reporting a successful invocation.
6. **PY05-006 — Failure compatibility.** Preserve timeout, output-bound and safe
   nonzero-exit failure categories. Known incomplete input remains a failure even
   when the child exits zero; do not silently report full delivery. `KeyboardInterrupt`
   and other catchable termination paths run owned cleanup and then propagate the
   original interruption. No automatic replay or new global signal handler is added.
7. **PY05-007 — Privacy.** New handling, diagnostics and test logs must not expose
   stdin, selected environment values or arbitrary child output. Preserve the
   existing executable-basename/exit and restricted managed-script error detail.
   Input remains outside argv and no raw capture is newly persisted.
8. **PY05-008 — Caller boundaries.** Preserve current per-call timeouts, configured
   `LIMA_HOME`, byte/JSON request limits, disabled native-owned update routes and
   caller recovery ordering. A timeout reports failed local invocation and leaves
   guest effects uncertain for the existing caller to reconcile.

Deadline guarantees concern helper-controlled work after process creation and
bounded cleanup waiting, subject to OS scheduling and available signaling/reaping
permissions. They do not promise interruptible OS process creation, cleanup after
uncatchable termination, or proof that every remote/escaped process stopped.
Python documents the process-creation limitation and pipe deadlock concerns in
its [subprocess contract](https://docs.python.org/3.12/library/subprocess.html).

## Acceptance Scenarios

| Scenario | Given / when | Required result |
|---|---|---|
| Blocked input | A local child never reads input larger than its pipe capacity | Timeout within execution budget plus cleanup allowance and declared test tolerance; no indefinite write |
| Duplex traffic | A child fills stdout/stderr before reading a large payload | Output is drained while input progresses; exact input bytes reach the pipe; expected output returns |
| Partial writes | Input can be accepted only in several writes | No missing, duplicated or reordered bytes; EOF follows the last byte |
| Empty or inherited input | Caller supplies `b""` or `None` | Empty bytes send EOF; inherited stdin retains its borrowed ownership and behavior |
| Early input close | Child closes stdin while bytes remain, including exit zero | Bounded failure; no success claim for known incomplete input; owned resources close |
| Output boundary | Combined streams emit exactly the cap or one byte more | Exact cap succeeds if other success conditions hold; excess fails without retaining unbounded output |
| Final wait | Streams close but child stays alive | Remaining execution budget bounds child wait; output EOF alone is not completion |
| Pipe-holding descendant | A same-group child descendant keeps a captured pipe open | Deadline still expires; group termination and direct-child reap are attempted within cleanup policy |
| Setup or interrupt | Selector registration/I/O raises, or a catchable interrupt arrives after child creation | All acquired resources receive cleanup; original error/interrupt propagates |
| Cleanup failure | Child already exited, or group signaling is denied | Remaining cleanup and direct-child fallback are attempted; original failure survives; no unbounded wait |
| Private failure | Input, output and environment contain synthetic private sentinels | New diagnostics/test logs exclude those values; existing safe failure detail remains |
| Caller compatibility | Existing configuration/upload/recovery/federation callers use the helper | Current arguments, timeout values, request content and recovery authority remain unchanged |

## Visual Evidence

| Concern | Decision | Canonical evidence and update trigger |
|---|---|---|
| Boundary | required: ownership table below | Domain And Ownership; update when an owner or resource changes |
| Interaction | required: transition table below | Required Behavior and Acceptance Scenarios; update when ordering changes |
| State | required: transition table below | Same contract; update when completion/failure disposition changes |
| Data/trust | required: ownership table below | Privacy and caller boundaries; update when data crosses a new boundary |
| Schema | not_applicable: no new persisted entity, config or result schema | Existing interfaces remain authoritative |
| Dependency/deployment | not_applicable: installed standalone-file ownership and topology remain unchanged; rollout is separate | Engineering Profile and existing distribution contracts |
| Quantitative | not_applicable: timeout/output constants are boundary conditions verified by tests, with no comparative performance claim | Validation below |

| Boundary/data | Owner | Permitted disposition |
|---|---|---|
| Input bytes and selected environment | Caller supplies; helper transports locally | Preserve bytes, keep private values outside new diagnostics, close only owned pipe ends |
| Captured stdout/stderr | Helper until return/failure | Shared live cap; compatible stdout return or existing safe failure detail |
| Local child/group, created pipes, selector | Helper after acquisition | Normal reap/close, or bounded failure cleanup and original failure propagation |
| Inherited stdin | Caller | Borrow without closing or changing descriptor behavior |
| Remote guest mutation and previous VM state | Existing caller and guest workflow | Existing reconciliation/restoration; no inferred cancellation, rollback or retry |

| State/event | Next action | Completion condition |
|---|---|---|
| Child created | Establish one deadline and acquire/register owned I/O resources | Setup consumes execution budget and is cleanup-protected |
| Input/output ready | Advance eligible channels with bounded buffers | Provided input completes, then owned stdin closes |
| Captured streams reach EOF | Reap direct child within remaining execution budget | Return compatible stdout only for completed input and exit zero |
| Deadline, overflow, write/setup failure or interrupt | Stop transport; terminate owned local group/fallback; attempt reap; close resources | Original error/interrupt propagates after bounded cleanup |
| Cleanup error | Continue other applicable cleanup attempts | Never restart budget, replace primary failure or claim success |

**Text Equivalent:** The caller supplies private input and optional environment.
The helper owns only its newly created local process resources and bounded
capture. It services all channels within one execution budget, closes input on
completion, and returns only after both output EOF and successful child exit.
Any managed failure or interruption enters bounded cleanup while preserving the
original failure. Inherited stdin and remote guest recovery retain their owners.
These two tables are canonical for this bounded helper. Owner: distribution
maintainers; update with interface, timing, ownership or failure-policy changes.

## Validation And Evidence

- Add a red-first regression against the actual helper using local Python child
  processes, an independent outer watchdog and deterministic readiness signals.
  The watchdog must clean up its test-owned groups even when the regression hangs.
  Do not mock away pipe readiness, writes or reads in the decisive blocked/duplex cases.
- Use payloads demonstrably larger than the tested pipe's available capacity and
  explicit child rendezvous. Record interpreter/platform, monotonic elapsed time,
  configured execution/cleanup budgets, permitted scheduling tolerance and child
  disposition. A tolerance catches hangs without treating scheduler jitter as a bug;
  document its rationale instead of relying only on tiny sleep thresholds.
- Cover every acceptance row. Supplement real-pipe checks with controlled partial
  writes, acquisition/registration failures, interruption, group-signal denial
  and cleanup faults. Check direct-child reap and owned-descriptor closure;
  verify borrowed stdin is preserved. Compare original error identity/category
  where compatibility requires it. Check private sentinels without logging them.
- Preserve existing safe-error and output-overflow examples plus guest-upload,
  Codex transport, Tailscale input, service-token and VM-state restoration tests.
  Mocked `execute` caller tests prove argument/recovery contracts, not real pipe I/O.
- Build runs `uv run --group test pytest tests/test_lima_sandbox.py -q`, existing
  publication/instruction checks, then the configured full pytest suite. Stage
  intended new documents before the public-tree check so its Git-index inventory
  includes them. Reuse only source/environment-matching evidence.
- Native CI currently uses macOS with Python 3.14; weekly/manual compatibility
  also covers 3.12/3.13. Obtain matching native helper/caller evidence before
  claiming those targets qualified. Linux process fixtures do not qualify the
  installed macOS controller or live Lima operation. No checker is configured in
  root metadata; record that capability gap instead of inventing a typing pass.

Discovery writes no implementation or new tests. Existing audit probe and source
inspection remain defect evidence. Future test commands above are acceptance
work, not executed results. Discovery validation results belong in its handoff;
the context CHANGELOG receives a completed-cycle entry only after actual delivery.

## DBSCTR Handoff

Ready for one bounded implementation cycle. Review README and CHANGELOG; update
the existing context rather than creating another context or Initiative. Begin
with the blocked-stdin regression, implement the smallest compatible bounded I/O
and cleanup change, then verify callers and publication contracts. Helpers may
independently review source/tests, but one primary owns helper changes and final
evidence. No other Python-audit slice or shared-runner extraction is bundled.

Build verifies fresh checkout/base and lifecycle authority, preserves this
Discovery document closure, and persists the applicability plan below under its
Git-ignored `.dbsctr/plans/` path. Registration/launch feasibility is not claimed by
this document. No source push, PR publication, merge, local activation or live VM
operation has occurred merely because Discovery is ready.

```json
{
  "profile": "docs/specs/dotfiles_ai_distribution/PROFILE.md",
  "gates": {
    "domain": {"applicability": "required"},
    "behavior": {"applicability": "required"},
    "spec": {"applicability": "required"},
    "contract": {"applicability": "required"},
    "test_driven_implementation": {"applicability": "required"},
    "refactor": {"applicability": "required"},
    "review_integrate": {"applicability": "required"},
    "release": {"applicability": "not_applicable", "reason": "Source PR only; no package, registry, release or hosted-service artifact is published."},
    "deploy": {"applicability": "not_applicable", "reason": "Operator selected source PR only; managed local rollout is separate."},
    "operate": {"applicability": "not_applicable", "reason": "No live controller/VM activation or operational change is selected in this source-delivery slice."},
    "maintain_retire": {"applicability": "required"}
  }
}
```

Unresolved material decisions: none under the selected compatibility and source-PR
scope. Maintain/Retire reviews preserved Python/platform/API behavior, documents
the fixed regression and leaves deployment qualification explicitly separate.
