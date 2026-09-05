# Historical Reporting Without Live Checkouts

## Ownership And Scope

Lifecycle owns retained Cycle Record validation, historical enumeration, and live
execution authority. This elevated-risk slice uses PROFILE.md, Python and Security
modules, and managed local helper deployment with feature-branch delivery.
Writable implementation paths are dot_local/bin/executable_dbsctrctl and
tests/test_dbsctrctl.py. Discovery owns this contract, Initiative scope, and plan.
Completion evidence may update the lifecycle CHANGELOG without revising scope.

Two failures are in scope: live source resolution during historical reads and
legacy record-directory discovery against removed Git worktrees. No private
record rewriting, checkout recreation, migration, schema change, concurrency,
new daemon, or source-database scan is permitted as a repair.

## Behavior And Contracts

| Scenario | Required outcome |
|---|---|
| Valid completed record; historical source checkout absent | Cycle performance includes the same completed member and authoritative timing as before removal |
| Git lists a removed worktree with no accessible legacy record directory | Enumeration retains accessible common-directory records; no OS traceback or fabricated record |
| Valid active or retired record encountered by a historical reader | Validate its stored structure; existing state filters still control population membership |
| Malformed record, duplicate JSON keys, mismatched IDs or incompatible runtime representations | Fail closed; do not skip corruption, emit partial aggregates as complete, or silently reduce denominators |
| Live execution or mutation targets an absent or mismatched checkout | Reject using existing live authority checks |
| Historical correlation lacks usable path evidence | Retain exact stored identity evidence where valid; unavailable path correlation does not become an exact match |

Stored validation must always enforce existing schema/version, adapter fields,
opaque IDs, capability availability, activation, locator root/path syntax, and
generic/legacy OpenCode agreement. State `retired` must not bypass these checks.
Reject unsafe absolute or traversal locators without requiring the historical
target to exist. Preserve schemas 3/4 and existing schema-less compatibility.

Separate structural validation from live path resolution. Use explicit historical
read intent only in completed-cycle enumeration and History correlation; all
other callers retain live validation by default. Direct schema-5 validator calls,
active load, Begin/attach, portabilize, retirement/cleanup, incident updates,
export, worktree inventory, and batch delivery must not silently acquire relaxed
authority. Any additional historical consumer requires Discovery scope review.

`cycle-performance` output schema, completed-state selection, exact filters,
quality counters, mean/percentile reductions, and unavailable timing semantics
remain unchanged. A missing checkout alone never changes completed-member counts.
Malformed retained records fail the whole affected report under its current error
contract, with no successful output. No new partial-report schema is introduced.

Legacy enumeration may tolerate absence of a registered checkout only when probing
its legacy directory; do not broadly suppress record corruption, access errors in
the authoritative common directory, or unrelated failures. Preserve deduplication
and ambiguous identity rejection. Historical reads remain non-mutating.

## Validation

- Parameterized structural tests cover active, completed, and retired schema-5
  records with malformed adapter fields, unsafe locators, duplicate keys, and
  generic/legacy disagreement.
- Removed-source fixtures prove identical cycle-performance membership and
  reductions before and after removal, plus missing-timing unavailability.
- Dangling Git-worktree fixtures prove common-directory evidence survives an
  absent legacy checkout without modifying the registry.
- Live-mode fixtures reject missing/mismatched source identity and prove explicit
  historical mode cannot authorize mutation, attachment, or delivery.
- History correlation fixtures preserve exact identities and unavailable path
  fallback without changing source membership or private-output boundaries.
- Run affected tests/test_dbsctrctl.py plus lifecycle contract tests, compilation,
  and diff checks; configured CI remains the repository-wide authority.
- After targeted helper deployment, run source-local cycle performance and a
  bounded History aggregate smoke. Record availability truthfully; no broad
  performance-improvement claim follows from this reliability repair.

## Gates And Operation

Domain, Behavior, Spec, Contract, Test-driven implementation, Refactor,
Review/Integrate, Deploy, Operate, and Maintain/Retire are required. Release is
not applicable: no separately versioned artifact is published. All required gate
results are pending; no exceptions are granted by this specification.

Deploy only the lifecycle helper after affected gates pass. Keep the prior helper
identity for rollback, reapply it without deleting records or snapshots, and
verify existing lifecycle/History behavior. Restoring the prior helper may restore
the reporting defect; it must never restore deleted private evidence. The dotfiles
owner monitors report availability and revisits the contract when record schemas,
worktree identity, retention, or historical consumers change.

## Visual Evidence

| Concern | Decision | Source and review question |
|---|---|---|
| Boundary | not_applicable: explicit caller policy is clearer than a graph | Ownership And Scope; which callers may use historical validation? |
| Interaction | not_applicable: scenario table describes the read-only decision | Behavior And Contracts; when is live resolution required? |
| State | required: scenario table above | Behavior And Contracts; do all states retain structural validation? |
| Data/trust | not_applicable: invariants and prohibited bypasses are explicit | Behavior And Contracts; can historical reads authorize mutation? |
| Schema | not_applicable: no public schema or stored-data migration | Existing cycle-performance and harness contracts |
| Dependency/deployment | not_applicable: one existing helper is replaced | Gates And Operation; what is deployed and rolled back? |
| Quantitative | not_applicable: exact-result equivalence, not a speed benchmark | Validation; are denominators and reductions preserved? |

Text Equivalent: Stored records always receive structural validation. Only the two
named historical consumers may avoid live source resolution; mutation and other
callers retain live checks. Malformed records fail closed regardless of state.
Owner: lifecycle Discovery. Change trigger: validation, caller, or state-policy change.
