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
uv run --group test pytest \
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
| Weekly schedule, Monday 09:17 UTC | Python 3.12, 3.13, 3.14 | Preserve full supported-runtime coverage; a failed matrix member must not cancel the other compatibility results |
| Manual workflow dispatch | Python 3.12, 3.13, 3.14 | Maintainers can request the complete compatibility matrix without changing source |

Every selected runtime retains the same pinned tooling, early publication checks,
native Swift authority and full pytest command. Each job has a 90-minute timeout.
Workflow tokens have read-only repository contents permission. No path filter,
test exclusion, failure waiver, dependency change or privileged PR event is added.

Before merging this workflow migration, maintainers verify the new exact-head
Python 3.14 job succeeds, then replace the three required runtime contexts with
the app-bound `test (3.14)` check. Preserve strict current-base validation,
administrator enforcement, PR review/conversation requirements and force/deletion
restrictions. Do not temporarily remove all required checks or use an admin merge
bypass. Other applicable platform smoke failures still block integration.

The weekly matrix detects compatibility regressions after ordinary merges; it is
not per-PR evidence for Python 3.12/3.13. A compatibility failure requires repair
and a successful full-matrix rerun. Reverting this cadence requires restoring
the three-version workflow and matching required checks together. Native CI
results, queue times and protection snapshots remain the execution evidence;
the configuration alone proves no measured wall-clock speedup.

## Maintenance and rollback

Maintainers update the selected early checks when shared instruction consumers or
publication rules change. Native CLI import-set narrowing is deferred; this change
checks the current import closure. Reverting source restores previous ordering;
it must not erase failed evidence or change existing approval records. No live
instruction activation is claimed by source delivery.

## PY-08 compatibility qualification amendment

Distribution's [Python runtime contract](../../dotfiles_ai_distribution/features/python-runtime-qualification.md)
selects standard CPython 3.15 as an additional weekly/manual full macOS target
with Worktrunk 0.81.0. Implementation and candidate qualification are pending;
the table above remains the current workflow until that source change lands.
Build updates the existing canonical cadence table in the same candidate as the
workflow. Qualification requires a passing exact-source full manual matrix.
Preserve all current matrix members,
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
| Data/trust | not_applicable: no private data is moved; reuse the existing publication authority |
| Schema | not_applicable: no schema changes |
| Dependency/deployment | required: CI event/runtime/cancellation and merge dependency table above |
| Quantitative | not_applicable: no speedup claim |

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
