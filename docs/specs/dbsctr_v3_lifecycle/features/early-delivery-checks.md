# Early publication checks and bounded remediation

Context: dbsctr_v3_lifecycle. Profile: ../PROFILE.md. Risk: routine.
Delivery: source-only draft PR; managed activation follows integration with the
pending approval-policy change. No approval transport, record schema, or CLI
validation bypass changes.

## Domain and ownership

Discovery owns publication-ready source artifacts. Build owns affected validation
and implementation. The repository owns its publication authority; receipt and
import provenance do not certify document privacy. An editorial correction changes
presentation without changing requirements, behavior, acceptance criteria, risk,
dependencies, or source authority. The operator owns amendments to writable scope.

## Behavior and contracts

| Given | When | Required outcome |
|---|---|---|
| Documents will be published or imported | Discovery prepares receipt, preflight, or push | Run the repository's existing publication check over the exact candidate set, including import closure; failure blocks publication readiness |
| Shared instructions change | Build selects affected tests | Include all tests reading the changed instruction files, across context boundaries |
| A cheap source-contract defect exists | CI starts validation | Publication/instruction checks fail before the expensive full suite |
| A correction is editorial and in approved writable scope | Build repairs validation | Preserve cycle, import provenance, failed evidence and semantic constraints; rerun affected validation |
| An editorial correction is outside approved writable scope | Repair is proposed | Obtain one explicit scope amendment before editing; do not infer permission from this classification |
| A correction changes material intent or launch authority | Repair is proposed | Reopen affected readiness and retain exact changed-plan approval requirements |
| A repaired test passes | Evidence is recorded | Retain the original failure and record the passing replacement; a prose note is not a gate transition |

## Interfaces and validation

Discovery and DBSCTR skills carry these instructions; global OpenCode routing
states the same bounded remediation rule. Codex consumes the shared skills.
The CLI receipt/import schema is unchanged. No repository-independent scanner,
duplicate denylist, dependency graph service, or new approval mechanism is added.

This repository's early authority, used locally before handoff and by CI, is:

```sh
uv run --frozen --python 3.14 --group test pytest \
  tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers \
  tests/test_opencode_control_plane.py tests/test_dbsctr_lifecycle.py -q
```

CI runs that command after installing its existing tools and before the full
suite. Locally, the publication authority inventories tracked files: stage intended
new artifacts before checking, and verify the tested worktree matches the intended
commit. Do not stage unrelated work merely to broaden the scan.
Full CI uses the runtime cadence below. Failed early checks are not waived, and
an unavailable authority is not success.
The lifecycle regression verifies step ordering, selected authorities, and policy
coverage. Existing approval tests remain authoritative for CLI consent behavior.

## CI runtime cadence

The distribution owner maintains the hosted validation workflow; lifecycle owns
the early publication contract. This bounded cadence amendment is elevated risk
and serves distribution Product Intent journey 12: submit reviewable source
without repeating every compatibility run on every edit. Python support remains
`>=3.12`; this changes validation cadence, not supported runtimes or test scope.

| Event | Full macOS suite runtimes | Cancellation and merge consequence |
|---|---|---|
| Pull request | Python 3.14 | A newer run for the same PR cancels its predecessor; only the current head's successful `test (3.14)` can satisfy the native required check |
| Push to `main` | Python 3.14 | Main validation is separate from PR runs and is not cancelled by a PR update |
| Weekly schedule, Monday 09:17 UTC | Python 3.12, 3.13, 3.14, 3.15 | Preserve full supported-runtime coverage; a failed matrix member must not cancel the other compatibility results |
| Manual workflow dispatch | Python 3.12, 3.13, 3.14, 3.15 | Maintainers can request the complete compatibility matrix without changing source |

Every selected runtime retains the same pinned tooling, early publication checks,
native Swift authority and complete pytest population. Four independent workers
partition each selected runtime/tool lane. Each worker has a 90-minute timeout.
All pytest invocations use the frozen root lock and explicit matrix interpreter.
The preceding runtime check verifies root and PATH-selected `python3` minors and
records actual patch identities plus lock SHA-256. Both event classes retain the
additional Python 3.14/Worktrunk 0.80.0 compatibility member; the primary Worktrunk
version remains 0.81.0.
Workflow tokens have read-only repository contents permission. No path filter,
test exclusion, failure waiver, dependency change or privileged PR event is added.

Before merging this workflow migration, maintainers verify the new exact-head
Python 3.14 job succeeds, then replace the three required runtime contexts with
the app-bound `test (3.14)` check. Preserve strict current-base validation,
administrator enforcement, PR review/conversation requirements and force/deletion
restrictions. Do not temporarily remove all required checks or use an admin merge
bypass. Other applicable platform smoke failures still block integration.

The weekly matrix detects compatibility regressions after ordinary merges; it is
not per-PR evidence for Python 3.12/3.13/3.15. A compatibility failure requires repair
and a successful full-matrix rerun. Reverting this cadence requires restoring
the three-version workflow and matching required checks together. Native CI
results, queue times and protection snapshots remain the execution evidence;
the configuration alone proves no measured wall-clock speedup.

## Bounded full-suite execution

The distribution owner owns worker execution and result reconciliation. Lifecycle
owns the fail-closed merge contract. A **lane** is one selected Python/Worktrunk
pair. A **partition** is a deterministic, disjoint subset of the lane's complete
collected pytest node IDs, assigned by module. A **receipt** records collection,
selected and observed test IDs, actual terminal exit code, runtime, source commit,
workflow run and attempt. Skipped collector modules are recorded separately from
executable items. Existing failed execution-limit evidence remains valid
history; a receipt is not an approval or lifecycle gate pass.

| Given | When | Required outcome |
|---|---|---|
| A selected lane has a complete test collection | Workers execute | Every collected item belongs to exactly one of four partitions; no existing tests are removed, shortened or newly skipped |
| A selector or another collection hook removes tests | Collection is reconciled | Fail rather than treating the filtered population as the full suite |
| Existing setup skips or collection skips occur | Execution is recorded | Preserve pytest's real skipped outcomes; setup reports count as attempted items, not passing assertions |
| A worker fails, times out, is cancelled or never publishes a receipt | The required aggregate runs | Fail; pending, missing, malformed or nonterminal evidence cannot pass |
| Workers disagree about source, runtime, tool, run, attempt or complete collection | Results are reconciled | Fail before accepting their union |
| All workers succeed with matching identities | Results are reconciled | Require a disjoint selected union equal to the full collection and observed item IDs equal to each selected partition |
| A later PR update starts a new run | Artifacts are reconciled | Accept only the current run and attempt; retain obsolete results as history |

`tests/ci_shard.py run` owns collection and execution. Its fixed interface takes
`--shard` (0–3), `--python-version`, `--worktrunk-version`, `--commit`, `--run-id`,
`--attempt` and `--output`. It invokes the unfiltered configured pytest authority
with the existing first-failure behavior, per-test durations and JUnit output.
It reconciles collected modules against Git's tracked default pytest module
inventory (`test_*.py` and `*_test.py` under `tests/`). An ignored tracked module,
unexpected collection filter, changed source overlay or changed runtime identity
fails rather than shrinking that inventory. Existing module-level skips remain
explicit collector outcomes, repeated consistently across workers. Full node IDs
are retained, including existing multi-megabyte invalid-input parametrizations;
individual IDs are bounded at 4 MiB and each evidence file at 32 MiB.
The amendment module occupies partition 0 and lineage-recovery module partition
1, based on observed slow-module progress intervals. Other modules use SHA-256
modulo two for partitions 2 and 3. This allocation is a bounded scheduling choice,
not a measured speedup claim. New modules join automatically.

`tests/ci_shard.py verify` takes the same lane/run/source identities, an artifact
directory and the native worker-job result. It validates four bounded receipts
and JUnit reports. Duplicate IDs, unknown fields, unsafe files, incomplete
collection, failed phases, nonzero exit codes and incorrect partition assignment
fail closed. Workers must also agree on the actual full Python version and
collector outcomes. Exact item IDs and skip parity are checked against JUnit
properties; propertyless collection skips require a unique canonical module-path
mapping. Their count is reported separately from executed-item skips.
Workflow artifacts contain repository-relative test IDs and ordinary
test diagnostics, never credentials or private lifecycle records. Existing
workflow-token permissions remain read-only. Artifact publication uses only the
native Actions artifact service, with seven-day retention.

The aggregate retains the app-bound names `test (3.14)` and
`test (3.14, 0.80.0)`, and the selected weekly/manual runtime contexts. It runs
after all workers even on failure and cannot succeed when any required worker
job is unsuccessful. No protection change, privileged PR event, admin bypass,
dependency change or timeout increase is part of this amendment.

Focused validation covers deterministic assignment, exact union, setup skips,
test and collection failures, common filtering, missing/corrupt/duplicate results,
source/attempt mismatch and native-workflow dependency binding. Hosted completion
of every current-head worker and aggregate remains required operating evidence.

### Parent items and subtest occurrences

A **parent item** is a collected pytest node ID. A **subtest occurrence** is an
actual `pytest.SubtestReport`, identified by its selected parent and a contiguous
positive occurrence ordinal within that parent. Repeated or nested contexts may
produce distinct occurrences with identical messages or parameters. The worker
does not serialize context values, messages or arbitrary object representations.
The distribution owner maintains this adapter against the locked pytest version.

| Given | When | Required outcome |
|---|---|---|
| A selected parent executes unittest or pytest-fixture subtests | Reports are captured | Preserve each native subtest occurrence separately from the unique ordinary setup/call/teardown phases |
| Repeated or nested contexts have identical values | Subtests are recorded | Assign separate contiguous ordinals; never deduplicate by context or infer children from duplicate ordinary call reports |
| A child fails while its ordinary parent reports success | Evidence is reconciled | Fail independently of the parent result, worker-success claim or exit-code claim |
| A passing parent has skipped children | Evidence is reconciled | Preserve the passing parent and report child skips separately; reconcile every skipped child with JUnit |
| A child is missing, malformed, duplicated, out of sequence, foreign or attached to a setup-skipped parent | Evidence is reconciled | Fail; children never replace missing ordinary parent phases |
| Earlier artifacts flattened children into ordinary call reports | A repaired aggregate receives them | Reject the old schema; never invent lost child identity or relabel old evidence |

Receipt schema **2** adds the required `subtests` list. Each child has exactly
`nodeid`, `index` and `outcome`: the selected parent ID, a non-Boolean integer
ordinal beginning at one, and its actual outcome. The list is bounded at 100,000
occurrences per worker and by the existing 32 MiB file budget. Only passed or
skipped children qualify. Ordinary reports retain their exact three fields,
unique phases and complete execution checks. Child reports require a passed
parent setup and complete ordinary call/teardown, including a legitimate parent
call skip after earlier children. No child enlarges the selected population.

JUnit remains independent evidence. Its one native suite must report
`tests = ordinary passed calls + ordinary skipped phases + subtest occurrences
+ skipped collectors`, zero
failures/errors and matching skip counters. Each parent testcase keeps its exact
item identity; its skipped-element count equals its ordinary skipped reports plus
its skipped child occurrences. The suite skip counter includes those occurrences
and skipped collectors. These counters expose omitted passing children as well
as lost or invented child skips. Parent selected/passed/skipped totals remain
separate from `subtests_passed` and `subtests_skipped` aggregate totals.
An ordinary teardown skip can add a JUnit event after a passed call; a setup
skip followed by a teardown skip can also produce two skipped events for one
parent. Preserve those actual phase counts without inflating the parent totals.

Actual native fixture validation covers passing, repeated, nested, skipped and
failing subtests, a failed child with a passing parent, and child skips followed
by parent skips. Corruption checks cover ordinary duplicate phases, missing
children/parents, ordinal gaps or Booleans, unknown fields, false successful exit
claims and JUnit count/skip disagreement. The complete test population, pinned
tools, required check contexts, worker time limits, retention and native merge
protections remain unchanged. This amendment grants no deployment, validation
policy activation or history-recovery credit.

| From | Guard/action | To |
|---|---|---|
| Complete unfiltered collection | Assign every module deterministically | Four disjoint partitions |
| Each partition | Preserve actual pytest outcomes and identity | Terminal receipt and JUnit |
| All four receipts | Native workers succeeded; identities and full population agree | Exact-union verification |
| Missing, failed or inconsistent evidence | Always-run aggregate rejects | Required check failed |
| Exact union and actual attempts verified | Required aggregate succeeds | Eligible for existing native merge checks |

**Text Equivalent:** Each selected runtime/tool lane executes its complete
collection across four bounded workers. The native required aggregate accepts
only successful, matching, terminal evidence covering every collected item
exactly once. Any missing, failed, filtered or inconsistent evidence blocks it.
Canonical source: the interfaces and behavior table in this section. Owner:
distribution and lifecycle maintainers. Update trigger: partition, identity,
artifact, workflow dependency or merge-check contract changes.

## Maintenance and rollback

Maintainers update the selected early checks when shared instruction consumers or
publication rules change. Native CLI import-set narrowing is deferred; this change
checks the current import closure. Reverting source restores previous ordering;
it must not erase failed evidence or change existing approval records. No live
instruction activation is claimed by source delivery.

## PY-08 compatibility qualification amendment

Distribution's [Python runtime contract](../../dotfiles_ai_distribution/features/python-runtime-qualification.md)
selects standard CPython 3.15 as an additional weekly/manual full macOS target
with Worktrunk 0.81.0. The table above and workflow carry that source change
together. Qualification requires a passing exact-source full manual matrix and
current PR checks, recorded privately before Review/Integrate passes. Preserve
all current matrix members,
PR/main 3.14 check identities, native protections, early authorities, failure
behavior and timeouts. No floor, isolated runtime or advisory-default migration
is selected. The linked feature owns this candidate's acceptance and gate plan;
lifecycle publication and approval semantics remain unchanged.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: Domain and ownership names each owner explicitly |
| Interaction | required: ordered transition table below |
| State | required: ordered transition table below |
| Data/trust | required: native worker/artifact/aggregate handoff table below |
| Schema | required: bounded receipt field/authority table below; Cycle Record schema is unchanged |
| Dependency/deployment | required: CI event/runtime/cancellation and merge dependency table above |
| Quantitative | not_applicable: no speedup claim |

| Receipt fields | Producer and validation authority |
|---|---|
| `schema_version`, `shard`, `identity` | Worker schema 2; aggregate requires its fixed lane, source/tree/authority hashes, repository, run, attempt and partition identities; flattened schema 1 is rejected |
| `collected`, `selected`, `collection_reports`, `collection_complete` | Worker collection hooks and tracked-module inventory; aggregate checks exact populations, allocation and common skipped collectors |
| `reports`, `subtests`, `exit_code`, `python_full` | Unique ordinary phases and separately identified native child occurrences, terminal code and interpreter; aggregate reconciles every selected parent, child outcome, full runtime and exact JUnit identities/counters/skips |

| From | Direction and trust boundary | To |
|---|---|---|
| Selected source and pinned runtime/tool lane | Worker executes the complete configured population in an isolated native job | Bounded terminal receipt and JUnit diagnostics |
| Worker diagnostics | Native Actions artifact service; current run/attempt names and seven-day retention | Aggregate job for that lane |
| Downloaded artifacts | Validate fixed identities, every worker outcome and exact coverage; artifacts grant no approval | Existing app-bound required check |

**Text Equivalent:** Workers publish only ordinary test evidence through the
native artifact service. The aggregate validates the fixed receipt schema and
current-run source/runtime identities before accepting complete coverage. Unique
ordinary parent phases and separately identified subtest occurrences must agree
with JUnit identities, total counts and skipped occurrences; failed children
block acceptance even when their parent passes. Artifact
claims alone grant no merge, lifecycle or installation approval. Canonical source:
the bounded-execution interfaces above. Owner: distribution/lifecycle maintainers.
Update trigger: receipt fields, artifact transport, identity or retention changes.

| From | Guard/action | To |
|---|---|---|
| Candidate artifacts | Publication check passes | Receipt/preflight eligible |
| Candidate artifacts | Publication check fails | Bounded repair or material Discovery correction |
| Bounded repair | In scope or explicitly amended; affected validation passes | Resume existing cycle with replacement evidence |
| Material correction | Changed authority is prepared and exact approval renewed as required | Fresh readiness |
| PR update | New run replaces the same PR's obsolete run | One current primary runtime suite |
| Exact primary job succeeds | Matching required-check migration preserves strict native base protection | Ordinary guarded merge eligible |

**Text Equivalent:** Validate publication before handoff. Repair nonsemantic defects
inside approved ownership without discarding the cycle. Material changes retain
Discovery and exact-approval boundaries. Source: Behavior and contracts above.
Owner: lifecycle maintainers. Update trigger: publication authority, ownership,
approval, import closure, validation-order or CI runtime-cadence changes. The CI
cadence table is the canonical event-to-runtime and merge dependency mapping;
distribution maintainers update it with workflow and required-check migrations.
