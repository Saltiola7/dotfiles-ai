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
Full CI still runs unchanged on all supported Python versions. Failed
early checks are not waived, and an unavailable authority is not success.
The lifecycle regression verifies step ordering, selected authorities, and policy
coverage. Existing approval tests remain authoritative for CLI consent behavior.

## Maintenance and rollback

Maintainers update the selected early checks when shared instruction consumers or
publication rules change. Native CLI import-set narrowing is deferred; this change
checks the current import closure. Reverting source restores previous ordering;
it must not erase failed evidence or change existing approval records. No live
instruction activation is claimed by source delivery.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: Domain and ownership names each owner explicitly |
| Interaction | required: ordered transition table below |
| State | required: ordered transition table below |
| Data/trust | not_applicable: no private data is moved; reuse the existing publication authority |
| Schema | not_applicable: no schema changes |
| Dependency/deployment | not_applicable: existing CI tool setup and source-only delivery are explicit |
| Quantitative | not_applicable: no speedup claim |

| From | Guard/action | To |
|---|---|---|
| Candidate artifacts | Publication check passes | Receipt/preflight eligible |
| Candidate artifacts | Publication check fails | Bounded repair or material Discovery correction |
| Bounded repair | In scope or explicitly amended; affected validation passes | Resume existing cycle with replacement evidence |
| Material correction | Changed authority is prepared and exact approval renewed as required | Fresh readiness |

**Text Equivalent:** Validate publication before handoff. Repair nonsemantic defects
inside approved ownership without discarding the cycle. Material changes retain
Discovery and exact-approval boundaries. Source: Behavior and contracts above.
Owner: lifecycle maintainers. Update trigger: publication authority, ownership,
approval, import closure, or validation-order changes.
