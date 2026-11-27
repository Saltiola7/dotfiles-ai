# Four-worker qualification

Use four fresh Herdr-launched OpenCode Build sessions in four Worktrunk
checkouts of the same repository at the same `main` base. Each worker
gets only its row, the applicable gate plan, and its approved cycle
reference. These are independent test-only slices; there are no inter-slice
dependencies and no runtime changes are authorized.

| Cycle | Independent regression | Exclusive writes after registration | Focused validation |
|---|---|---|---|
| `HERDR-QUAD-CODEX-001` | A later Codex managed projection preserves the order and Unicode values of a native TUI status line while applying a managed value change. | `tests/test_codex_runtime_state.py`, `docs/specs/codex_control_plane/CHANGELOG.md` | `pytest -q tests/test_codex_runtime_state.py` |
| `HERDR-QUAD-PM-001` | PM frontmatter preserves quoted list members such as `"true"`, `"01"` and `"x: y"` as strings and keeps the body separate. No Jira or ticket writes. | `tests/test_pm_kernel_policies.py`, `docs/specs/pm_kernel/CHANGELOG.md` | `pytest -q tests/test_pm_kernel_policies.py` |
| `HERDR-QUAD-CV-001` | Two completed JUnit fixtures with the same cases in different orders yield the same test-identity digest. This checks identity, not outcome or reuse authority. | `tests/test_continuous_validation_identity.py`, `docs/specs/continuous_validation/CHANGELOG.md` | `pytest -q tests/test_continuous_validation_identity.py` |
| `HERDR-QUAD-OPENCODE-001` | Give inherited slash commands individually named test cases so a route override names the affected command. Preserve the existing assertion and provider-specific command cases. | `tests/test_opencode_control_plane.py`, `docs/specs/opencode_control_plane/CHANGELOG.md` | `pytest -q tests/test_opencode_control_plane.py -k commands_inherit_current_agent` |

Use the repository's existing Python test environment and publication
check. Exercise existing behavior; do not fabricate a red test. Stop
and return a failing fixture if the scope requires a runtime fix.
Each row has its own committed Engineering Profile and gate plan. The
six kernel gates, Review/Integrate, Operate and Maintain/Retire apply as in
the single-worker proof. Release and Deploy do not apply: publication is
draft source only, with no running system change.

## Handoff and shared resources

1. Preflight each exact slice separately. Registration needs exact digest
   approval. Preparing four drafts does not authorize four concurrent
   claims or relax a controller or tool refusal. Keep Auto off.
2. Perform the common Discovery import at registration, before the timed
   work. Workers treat those same docs as read-only. Prepare the existing
   test environment before overlapping gates and use separate temporary
   directories and pytest caches; do not concurrently install packages
   or write shared runtime state. The Git object store is shared; branch
   refs, Cycle Records, test files and changelogs are distinct.
3. Measure actual Build intervals containing the owned edits and actual
   Test intervals containing the focused gate commands. Compare the four
   intervals separately in each phase; report observed concurrency if
   fewer than four overlap. Idle or queue time does not establish overlap.
4. Read each result by native session ID and independently verify the
   gate evidence, commit and worktree. Preserve partial or failed results.
   Publish to separate draft PRs serially and keep merges outside this
   qualification. Report draft and CI status separately.

## Visual Evidence

The ownership table and numbered handoff show boundaries, ordering, state
and trust for this batch. In text: one operator approves four separate
preflights; four sessions produce independent recorded results; the
coordinator checks each and serializes publication. Schema and deployment
do not change. Use a table of actual intervals when evidence exists;
no speedup or concurrency result is claimed at preflight. The Lifecycle
owner updates this brief when worker scope or acceptance changes.
