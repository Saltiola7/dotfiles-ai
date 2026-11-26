# First worker: one Herdr Build session delivers a draft PR

**Worker brief.** Use a fresh top-level OpenCode Build session in one
Worktrunk feature checkout of the coordinator repository, based on `main`.
Add a fixture regression in `tests/test_integration_initiative_opencode.py`:
if the native session changed to Plan or moved to a sibling checkout before
dispatch, the writer must stop before sending the prompt. Use the existing
scripted transport; no provider call belongs in the regression. The worker
owns the test and its completion entry in `docs/specs/dbsctr_v3_lifecycle/CHANGELOG.md`.
That changelog is shared at integration; the proof ends at draft publication.
If the test reveals a runtime defect, return the failing case for review.

**Why this is independent.** The [marker test](CHILD-WRITER-READINESS.md#marker-test-routing-overlap-and-feedback)
established routing and feedback, and the writer adapter already exists in
the base. This proof uses exact launch-digest approval for one primary;
it needs neither a multi-slice grant nor changes to ordinary subagents.
The prepared checkout, Cycle Record and named test file each have one
writer. No other slice requires this draft to start.

## Acceptance and handoff

| Owner | Check | On failure |
|---|---|---|
| Coordinator before launch | Run `begin --preflight` for `draft_pr` with integration off. Present the exact repository, base, checkout, imported Discovery files, risk and launch digest. | If the base or authority changes, refresh the preview and present the new digest before registration. |
| Coordinator and worker after approval | In the exact new session, verify `build`, no parent and the selected directory by native readback. Give it this brief and the approved cycle reference. The normal lifecycle path registers one record; verify the matching record before editing. | Wrong role, wrong checkout, occupied record or changed launch: stop. A tab label or caller-supplied ID does not establish ownership. |
| Worker | Run the fixture test module and repository publication check; record gate evidence, artifact reviews and owned commits. After passing gates, use the normal DBSCTR final push for the feature branch and return the draft URL and head. | Return the error and preserve the checkout. Local gates alone do not establish draft publication. |
| Coordinator | Read the worker's final reply by session ID. Match its Cycle Record and validated head to GitHub's draft flag, head commit, repository and `main` base. | If the reply is lost, read the same session and record before considering another writer. No gate credit from screen text. |

**Text equivalent.** The operator approves one checkout-bound plan.
The worker runs the cycle there. The coordinator verifies the draft against
the lifecycle record and reports CI separately. Merging requires its own decision.

**Delivery decision.** Use a new draft PR into `main` from the prepared
feature branch. The cycle ID and checkout stay the same; “local” in their
names describes where the worker runs. The only feature work is the test
and changelog entry named above, plus the approved Discovery import.

**Earlier local-only preflight.** At Discovery revision `7538096d`
the standalone slice received its readiness receipt. From a clean Worktrunk
feature checkout based on `826c55d5` and tracking `origin/main`, the installed
`dbsctrctl begin --preflight` for `HERDR-LOCAL-CYCLE-001` refused `local`:
`direct delivery to the protected base branch requires draft_pr`.
It issued no launch digest. Worktree setup and the receipt both succeeded.
The [local completion contract](../../specs/dbsctr_v3_lifecycle/features/forgejo-local-registration.md)
explains why changing the tracking branch would not have supplied that outcome.
The operator selected draft delivery instead; the earlier refusal remains valid.

Profile: [DBSCTR V3 Lifecycle](../../specs/dbsctr_v3_lifecycle/PROFILE.md).
Risk: elevated, because a mistaken session-to-record match would credit
the wrong worker. The [gate plan](HERDR-LOCAL-WORKER.plan.json) requires
the development kernel, Review/Integrate, Operate (live handoff) and
Maintain/Retire (preserve the published head and its evidence). Release and
Deploy do not apply to this source-only draft.

## Visual Evidence

Boundary, interaction, state and data/trust: the handoff table above shows
who may act and what constitutes a result. Schema and deployment: not
applicable; reuse existing record formats and the installed workstation.
Quantitative: not applicable; the decision is whether one cycle finishes.
The Lifecycle owner updates this brief when the accepted delivery or proof changes.
