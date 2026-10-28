# Workflow native handoff

For explicitly approved non-success retirement, the
[retirement journey](cycle-retirement-journey.md) and lifecycle archival contract
replace merge proof with verified local preservation before handoff/removal.
Primary compatibility, native identity/history preservation and consumer checks
remain. Record-only closure may precede consumer exit; preparation/removal may
not. This approved specification amendment does not qualify installed shutdown
or automatic cleanup behavior.

**Specification ready; implementation and rollout unqualified.** Owner: OpenCode
control-plane maintainers. Profile: [../PROFILE.md](../PROFILE.md). Risk: critical
for retained history and checkout identity. This contract resolves convergence
INT-018–INT-021 without reinstating transparent continuation or custom launch tools.

## Selected native route

The primary uses the native OpenCode `session_move` tool for its **current**
conversation, omitting a supplied session identity and selecting the canonical
primary checkout. The tool returns the same session identity and new directory.
The public V2 API also documents `session.move` at
`POST /api/session/{sessionID}/move` with an absolute `directory`. The native tool
is preferred: an ordinary lifecycle CLI cannot authenticate its invoking session
from an argument, environment variable, PID, branch name or latest-message guess.

Public interface source: [OpenCode V2 OpenAPI](https://opencode.ai/v2/openapi.json).
Interface availability is not an attachments/history or installed-version test.
If the selected harness lacks the native route, report `native_handoff_unavailable`
and retain a checkout still targeted by the live conversation. Do not create a
new session, implement an identity shim or invoke another session as a workaround.

## Ordered behavior

1. Finish or explicitly pause all work owned by the current checkout. Preserve
   lifecycle evidence and verify Git/default and applicable DVC delivery under
   the [preservation contract](../../dbsctr_v3_lifecycle/features/workflow-preservation-retirement.md).
2. Resolve the unique canonical primary from native Git worktree membership.
   Check its branch, tracking destination, cleanliness and compatibility. Fetch
   the approved default and use fast-forward only. Dirty/diverged state remains
   untouched; explain the conflict and interview for intent before reconciliation.
3. Use native `session_move` for the current conversation. Check its returned
   directory and unchanged native identity. Resume tools at the new Location;
   a shell subprocess's `cwd` change does not satisfy this step.
4. Let in-flight tools and helper writers finish; then run the preservation hook
   from outside the former checkout. Any remaining process/open-file consumer,
   uncertain ownership or unavailable inventory blocks removal without signaling.
5. Worktrunk alone removes an eligible checkout with hooks enabled. Observe native
   membership and branch outcomes separately before recording success.

If the native move fails, leave both checkout and session alone and report the
failure. If it succeeds but synchronization/removal later fails, keep the successful
move evidence and retained checkout; do not move back or repeat destructive work
merely to make the sequence appear atomic. Retry from current observations.

Completed idle checkouts need no manufactured conversation or resurrection of a
historical one. Preserve historical identities and source-independent record
readability. The primary's native move is not CLI actor authentication, a universal
busy fence, or permission to take over someone else's active cycle.

## Discovery-to-Build reuse and bootstrap

Reuse one physical linked checkout when its native registration requirements
already hold: clean state, no active cycle/writer, matching repository, current
base, preserved authority and qualified native session Location. No extra checkout
is required merely for a lifecycle phase or bounded docs helper.

Current source registration requires task `HEAD == approved remote base` before
import. Unmerged Discovery commits therefore cannot simply become an ordinary
Build baseline. Never reset them, publish them prematurely just to bypass this
check, or claim `--resume-existing` registers new work. The supported bootstrap is:

- Retain the small code-only Discovery authority checkout and its committed ref.
- Allocate one code-only Build checkout with Worktrunk at the freshly fetched
  approved base; set its intended tracking ref before preflight.
- Point Initiative registration at the retained Discovery checkout; include the
  complete changed-document closure in the receipt. Import uses existing CLI
  exact-artifact behavior after digest-bound approval.
- Once that authority is in the default branch, use its primary checkout as the
  authority source for later slices. Reuse existing eligible task checkouts when
  registration permits; never create a new data/environment copy for a phase.

This temporary two-checkout bootstrap is an explicit current capability limit,
not an additional allocator or permission for duplicate environments/datasets.
Discovery checkout retirement still needs preservation of its private reports.
An alternative immutable-Git-ref registration interface is not part of this cycle.

## Acceptance and qualification

| Case | Required result |
|---|---|
| Current conversation moves | Same native identity, requested canonical Location; existing messages, attachments and saved compaction remain usable |
| Wrong/changed primary or dirty/diverged primary | Retain; no reset, branch swap or hidden route substitution |
| Native move unavailable/denied | Explicit blocker; no shell, session or provider workaround |
| Move succeeds; cleanup fails | Session remains at primary; original checkout/evidence retained; retry from observations |
| Other live consumer remains | No removal or automatic termination |
| Idle completed checkout | No new conversation; source-independent historical evidence remains readable |
| Discovery has unmerged commits | Supported authority-import bootstrap, not unknown ahead-commit bypass |
| New Build source/base drifts | Fresh receipt/preflight; changed launch plans need renewed approval |

Build tests use synthetic histories and disposable checkouts; do not transport
private transcripts. Live operation verifies the invoking conversation only after
explicit rollout approval, without provider/model requests or forced restarts.
Guest/Desktop/Codex-specific behavior is not newly claimed; missing capabilities
remain fail-closed until their own configured runtime qualification.

Source closure: managed `AGENTS.md`, DBSCTR/Discovery skills and existing
`tests/test_native_workspace_execution.py`, `tests/test_native_helper_delegation.py`,
`tests/test_native_opencode_permissions.py`, `tests/test_dbsctr_lifecycle.py` and
`tests/test_native_cli_projection.py`. Lifecycle identity and retention source
remains owned by its context; no new custom continuation plugin is authorized.

| Gates | Applicability |
|---|---|
| Domain, Behavior, Spec, Contract, Test-driven implementation, Refactor, Review/Integrate, Maintain/Retire | required |
| Release | not_applicable: no independent package is published |
| Deploy, Operate | required for live activation; not applicable to source-only PR delivery |

All implementation/operation results remain pending; specification readiness is
not a gate-pass claim, launch receipt or deployment approval.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: native route and source ownership above distinguish harness, lifecycle, Git and Worktrunk |
| Interaction | required: ordered behavior and bootstrap sequence above |
| State | required: acceptance table covers unavailable, partial-success and retry states |
| Data/trust | required: native route/identity constraints and private-history preservation above |
| Schema | not_applicable: reuse the published native interface; no new persistence schema |
| Dependency/deployment | required: bootstrap sequence and gate table; source import precedes independent live activation |
| Quantitative | not_applicable: no timing, storage or cost benefit measured |

**Text Equivalent:** The primary first preserves work and safely refreshes the
canonical base, then moves its current conversation through native OpenCode. Only
after other consumers stop and preservation is rechecked may Worktrunk remove the
former checkout. Unavailable identity/move or unsafe base retains it. Successful
handoff survives failed cleanup. One temporary code-only authority checkout may
be needed for the existing import protocol; it never implies a data copy.
Canonical source: this contract and the published native interface. Owner:
control-plane maintainers; update on native interface, registration, preservation
or handoff ordering changes.
