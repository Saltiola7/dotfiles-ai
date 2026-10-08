# Superseded empty detached registration recovery

Operator-approved narrowly scoped maintenance exception: qualify this recovery
source outside registration because the stale record itself blocks registration.
Normal Initiative registration and exact launch confirmation remain required
afterward. Engineering Profile: ../PROFILE.md.

`dbsctrctl workspace-recover-orphan --cycle-id ID --superseded-by ID --preview`
is read-only. The mutating form requires its fresh `--expected-state` digest and
interactive `RETIRE-ORPHAN ID DIGEST` confirmation from the operator.

Eligibility is deliberately narrow: an active schema-4 non-native record with
no recorded commits, source or retirement, no branch, a cycle-relative root,
and no DBSCTR-created checkout. Its recorded Git baseline must agree with the
worktree baseline. No registered detached worktree may still have that baseline.
A different completed same-context successor must have recorded commits, all
ancestors of the inspecting checkout. Preview binds both record byte hashes and
native Git worktree inventory; confirmation rechecks them under the evidence lock.

The operator confirms the registration was superseded and its old writers cannot
write. The command preserves an exclusive, fsynced, private original-byte backup
before atomically marking only the old record retired with explicit recovery
provenance. Failed gates, uncertain operations, histories, active pointers,
worktrees and branches are retained. This is administrative retirement, not a
claim of successful completion or an inferred reassignment of writer authority.
Existing bound legacy cycles still require ordinary in-place workspace adoption.

Validation: reproduce failed registration in an unrelated new native checkout;
confirm explicit recovery removes that blocker while preserving dirty work and
exact record bytes. Reject noninteractive mutation, stale state, recorded work,
live baseline candidates and uncompleted successors. Run adoption/execution
regressions alongside the recovery checks. A failed final record write retains
the immutable backup and original record for inspection/retry.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: ownership and operator responsibility are specified above |
| Interaction | not_applicable: preview, confirmation, locked recheck and backup ordering are explicit in prose |
| State | required: table below defines the only permitted transition |
| Data/trust | not_applicable: private record remains in the same repository metadata boundary |
| Schema | not_applicable: existing Cycle Record and private migration backups are reused |
| Dependency/deployment | not_applicable: native CLI distribution remains unchanged |
| Quantitative | not_applicable: no quantitative decision |

| Initial state | Event | Result |
|---|---|---|
| Eligible active orphan | Preview | No mutation; digest returned |
| Eligible active orphan | Fresh explicit operator confirmation | Exact preimage retained; record administratively retired |
| Ineligible or changed record | Preview or confirmation | Refusal; original retained |

**Text Equivalent:** only a freshly confirmed eligible orphan becomes retired;
preview never mutates and changed/ineligible state is refused. Canonical source:
this contract. Owner: lifecycle maintainer. Change trigger: eligibility, mutation
ordering or confirmation semantics change.
