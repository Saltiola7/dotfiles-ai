# Audited recovery of omitted historical Gate Commits

## Domain and scope

This critical-risk source slice adds an explicit, private recovery transaction
when an existing cycle's Git first-parent history contains reviewed documentation
commits or an exact accepted-base merge omitted from its recorded commit list.
It does not turn a Git commit into passing gate evidence. The lifecycle owner
owns the helper, private recovery custody, compatibility and security response.

The first release accepts only ACTIVE, native **registered schema-5 GitHub
Initiative cycles**, in their original clean linked checkout with the recorded
branch, upstream, remote destination and committed Engineering Profile intact.
Reject ordinary, adopted, legacy, Forgejo, completed/finalizing and unknown-schema
cycles. Reject existing or prepared Initiative amendments. One recovery per cycle
is supported. Existing record readers remain compatible when the optional
`lineage_recovery` field is absent. Method Revision remains 3.29.

Definitions:

- **Recorded lineage:** the ordered existing Gate Commit entries from registration.
- **Missing commit:** a first-parent commit absent from that list. Existing entries
  must remain a unique ordered subsequence of actual history.
- **Reviewed documentation commit:** one-parent, nonempty change containing only
  regular, nonexecutable Markdown files under `docs/`. The private plan lists all
  changed paths, modes and blobs, including deletions. Human review and exact-plan
  approval are required; the extension alone does not establish publication safety.
- **Accepted-base merge:** two ordered parents, first parent from the owned branch
  and second parent exactly the operator-selected accepted commit. That commit
  must be an ancestor of the selected upstream. Its tree must equal a clean native
  merge computed in a disposable object store. No conflict overlay is admitted.
- **Recovery plan:** immutable private selection, complete original record hash,
  exact HEAD/tree, original/recovered lineages, missing-commit proofs, accepted
  base, upstream target, checkout and delivery/profile/applicability identities.
- **Recovery custody:** plan, original record bytes, approval envelope and exact
  deterministic replacement outcome, all owned private regular files.

No replacement cycle, baseline reset, Git rewrite, force push, remote publication,
provider/credential access, installation or resource deletion occurs in recovery.
Source delivery is a draft PR. Managed installation and first-consumer proof follow
accepted-source qualification through the existing targeted distribution process.

## Behavior

1. Given admissible omitted documentation commits and one exact accepted-base
   merge, preflight preserves Git/record bytes and writes a deterministic private
   plan whose digest binds the complete selection.
2. Given explicit approval of that exact digest and unchanged state, apply inserts
   missing entries in chronological order with `gates: []`, preserving every
   existing entry, evidence envelope, registration and discovery authority. It
   resets Review/Integrate to pending and gives no other gate credit.
3. Given stale record, HEAD/tree, target, upstream, profile, plan, checkout or
   missing-commit selection, apply blocks before replacing the Cycle Record.
4. Given an executable/unsafe documentation path, unexplained commit, reordered or
   duplicate recorded entry, wrong merge parent/tree, missing object or conflict,
   preflight fails closed. No network fetch repairs missing objects implicitly.
5. Given another native writer or prepared Initiative amendment, preflight/apply
   blocks under the existing shared cycle mutation lock and delivery target lock.
6. Given durable approval custody but interrupted replacement, other mutators
   remain blocked. Exact replay can finish only while the record still equals its
   preserved original bytes. Conflicting custody remains actionable.
7. Given replacement succeeded but acknowledgement was lost, exact replay observes
   its retained outcome and returns already_applied without repeating mutation.
   After genuine cycle progress, the old replay is stale and cannot reset review.
8. Given ordinary progress or historical reading, immutable recovery custody is
   validated without requiring the old checkout or current HEAD to exist. The
   recovered commit sequence remains an exact prefix; later Gate Commits may
   append. Original evidence remains retained. Corrupt custody blocks reading.
9. Given repaired lineage but stale/failed required evidence, Final Push still
   fails. Normal current-base reconciliation, gates, Graphify, CI and protected
   delivery requirements continue to apply.

## Interfaces and contracts

```text
dbsctrctl lineage-recover --cycle-id ID --accepted-base COMMIT \
  --reason TEXT --preflight --json
dbsctrctl lineage-recover --cycle-id ID --accepted-base COMMIT \
  --reason TEXT --expected-launch-digest SHA --approval agent-confirmed --json
```

Default apply approval is interactive: the operator enters `RECOVER ID SHA`.
Agents never synthesize terminal input. `agent-confirmed` reports explicit chat
approval for the exact private plan; it is not authenticated actor identity.
General repair approval, shell permission or a source PR is not live-plan consent.

Hosted output is only `{schema_version,cycle_id,status,state_digest,reasons,
next_action}`. Status is preflight, applied, already_applied, blocked or
recovery_required. Use exit 0 for the first three, 1 for blocked, and 75 for
uncertain durable custody. Reasons are classified codes. Private reasons, paths,
commit diffs, record bytes and raw exceptions never enter that output.

Internal functions own snapshot/admission, commit proof, deterministic replacement,
custody validation and transaction execution. Git reads use the existing offline,
no-replacement/no-lazy-fetch context and bounded commands. Merge-tree generation
writes only disposable objects, preserving source refs, index, worktree and object
store. Plan size, lineage count, changed-path count and private reads are bounded.
Resolve every nonzero old/new historical documentation blob as an existing blob
in a bounded offline batch. Reject unsafe file types, symlinks, hard links,
foreign ownership and permissive private evidence. Preflight checks the serialized
transaction capacity; apply bounds all exact artifacts before publishing approval.
Each custody artifact must fit the existing 32-MiB private reader limit, including
the escaped replacement stored inside the outcome. Existing immutable write/fsync and atomic private replacement
primitives remain authoritative; no second lifecycle engine is introduced.
The lineage publisher stages single-link files in a separate private staging
area, fsyncs bytes, then atomically publishes into absent custody destinations
under the existing locks. A crash before publication leaves retained staging,
which is never read as approval. A published approval envelope blocks competing
mutation; exact replay can supply missing subsequent custody artifacts without
changing that approval time. Unknown or corrupt final artifacts are never
replaced. Cooperating writers must use the qualified installed helper; older
copies do not enforce this newly introduced recovery contract.

`lineage_recovery` has a closed schema identifying the plan digest and approval
method/time. Custody locations are derived from cycle ID/digest, never supplied
arbitrary locators. Readers validate plan/preimage/envelope/outcome digests,
reconstruct the exact replacement and verify its recorded recovery entry. The
outcome owns replacement bytes/hash, avoiding a circular record hash. An old
record cannot be rewritten by replay after normal progress.

The dedicated command bypasses generic workflow telemetry and owns its locks.
Existing native mutators inspect prepared recovery custody under the same shared
lock; approved-but-unapplied recovery blocks them. Initiative amendment rejects
prepared/applied lineage recovery in this first release. Plan-only preflights do
not block normal work. No gate exception is introduced.

## Threats, validation and maintenance

The principal threat is laundering unexplained Git history into delivery authority.
Exact reviewed commit proofs, immutable preimages, zero gate credit, reset review,
current-base enforcement and independently reviewed negative tests address it.
Concurrent writers and interrupted persistence threaten audit continuity; shared
locks, expected-state checks, immutable durable outcomes and atomic final writes
supply safe recovery. Untrusted Git configuration, private paths and malformed
custody threaten execution/privacy; offline reads, disposable merge objects,
strict file checks and bounded output preserve those boundaries.

Use synthetic disposable repositories and private fixture records. Test all nine
behaviors, exact four-gap recovery, stale digests/targets/profiles, unsafe paths and
files, wrong merge trees, competing writers, interrupted writes, exact retry,
post-progress rejection, evidence preservation and final-delivery refusal. Do not
copy consumer identifiers or private evidence into source fixtures. Run affected
native lifecycle, Initiative, publication and instruction contracts; Python
compilation; supported-runtime checks and configured hosted CI. Qualified
independent review is required. No dependency or runtime upgrade is included.

Maintain the ordinary strict lineage guard and Profile-only adoption route.
Unsupported record classes or authority combinations need a separate reviewed
extension. Recovery never removes preimages, old failures, worktrees or branches.
The owner retains evidence with the cycle and handles vulnerabilities through the
existing repository process. Rollback preserves the transaction files and record;
old helpers must not be used to mutate recovered records. If validation or
installation fails, retain the consumer hold and original evidence.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: ownership table below |
| Interaction | required: ordered transaction table below |
| State | required: transition table below |
| Data/trust | not_applicable: explicit private-custody and bounded-output contracts state all transfers without a second diagram |
| Schema | not_applicable: optional field/custody relationships are explicit above; no domain database schema |
| Dependency/deployment | not_applicable: source PR then existing managed installation; no new runtime topology |
| Quantitative | not_applicable: no measured comparative or capacity claim |

| Boundary | Authority |
|---|---|
| Operator | Approves one exact recovery plan |
| Recovery helper | Validates and preserves private provenance; grants no gate passes |
| Ordinary lifecycle | Owns subsequent evidence, integration and delivery |

| Order | Action |
|---|---|
| 1 | Lock cycle/target; validate original state and proofs |
| 2 | Persist immutable private plan; operator reviews exact digest |
| 3 | Reacquire locks; revalidate state and explicit approval |
| 4 | Persist approval, preimage and deterministic outcome |
| 5 | Revalidate then atomically replace record; report bounded result |

| Current state | Guard/event | Result |
|---|---|---|
| Unrecovered | Admissible preflight | Plan retained; record unchanged |
| Planned | Exact approval and current state | Prepared custody |
| Prepared | Atomic replacement succeeds | Recovered; review pending |
| Prepared | Interruption/conflicting state | Recovery required; other mutation blocked |
| Recovered | Exact unchanged replay | Already applied |
| Recovered | Ordinary progress then old replay | Stale replay blocked |

**Text Equivalent:** The operator approves a private exact plan. The helper locks
and validates state, persists immutable recovery custody, then changes only cycle
provenance and review readiness. Ordinary lifecycle gates still own delivery.
An interrupted prepared recovery blocks competing mutation; a confirmed replay
never repeats the change. Canonical source: this feature; owner: lifecycle
maintainer; update these tables with any boundary, ordering or state change.
