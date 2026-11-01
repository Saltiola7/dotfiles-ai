# Python runtime ownership and root compatibility qualification

Status: Discovery-ready; implementation and Python 3.15 qualification pending.
Audit reference: PY-08. Owner: distribution maintainers. Profile:
[../PROFILE.md](../PROFILE.md). Product Intent:
[../PRODUCT.md](../PRODUCT.md), journey 12. Risk: elevated because hosted
compatibility validation and public runtime claims change.

## Problem and outcome

The root project declares Python `>=3.12`, while hosted compatibility validation
currently ends at 3.14. Several optional tools have separate interpreter ranges,
exact patches, dependency locks or artifact identities. A root test result must
not be mistaken for qualification of those isolated runtimes, and an update
review must not silently change their installer ownership.

Establish an explicit review policy and qualify standard CPython 3.15 as an
additional root compatibility target. Retain the root 3.12 floor, current 3.14
pull-request/main jobs and every isolated runtime pin. The existing
[update runbook](../../../UPDATES.md#which-owner-updates-what) remains the
canonical family/installer inventory; this feature adds policy, not a registry.

## Selected scope and constraints

| ID | Decision |
|---|---|
| PY08-01 | Keep root `requires-python = ">=3.12"`; distinguish the metadata floor, actual qualified targets and an installed runtime identity |
| PY08-02 | Add standard CPython 3.15 to weekly/manual full macOS validation with Worktrunk 0.81.0; retain every existing matrix member, timeout and failure behavior |
| PY08-03 | Keep PR/main Python 3.14 and the existing 3.14/Worktrunk 0.80.0 job; do not alter native required checks or branch protections |
| PY08-04 | Review declared Python runtime families monthly; upstream security releases/advisories trigger urgent out-of-cycle assessment and prioritized fix qualification |
| PY08-05 | Preserve all deployed/optional runtime pins, lockfiles, installers, disabled states and activation boundaries; root qualification does not authorize their upgrade |
| PY08-06 | Use the existing runbook and installer owners for candidate selection, qualification, recovery and separately approved activation |
| PY08-07 | Allow only compatible source/test repairs demonstrated necessary for root 3.15 qualification; retain 3.12 behavior and security/isolation assertions |
| PY08-08 | Record requested and observed interpreter, lock identity, platform, source revision, command, outcome and skips; unavailable evidence is not a pass |

The distribution owns this single delivery slice and the hosted workflow.
Lifecycle owns early publication semantics; its existing cadence document must
remain consistent with this amendment. Continuous-validation and knowledge-store
owners remain adjacent consumers with unchanged interfaces and runtime contracts.
No independent context implementation is selected. Native documentation-import
packaging is a separate registration concern described in the Build handoff.

Non-goals: raising the support floor; PR promotion to 3.15; free-threaded or
experimental interpreter qualification; new syntax adoption; a checker migration;
dependency upgrades; a Python manager, runtime registry, updater or scheduler;
host/guest installation; service operations; container/model changes; and fixes
for the other Python audit findings. An incompatibility requiring one of these
changes returns for a bounded scope decision instead of being hidden or skipped.

## Runtime and ownership boundary

| Runtime role | Authority and preserved boundary | PY-08 action |
|---|---|---|
| Root scripts, test dependencies and hosted tests | Root `pyproject.toml`, `uv.lock` and `.github/workflows/test.yml`; metadata alone does not qualify future interpreters | Qualify 3.15 against the unchanged root lock and existing full authorities |
| Repository advisory adapter | `.github/continuous_validation.py` deliberately selects its existing frozen 3.14 commands | Preserve this default; hosted 3.15 compatibility does not promote advisory execution |
| Isolated SDKs, workloads and optional tools | The runbook's Dagger, PR-Agent, Graphify, reranker, managed DVC, Hermes and security-toolkit owners; source ranges, exact pins and artifact identities take precedence | Include each in monthly review; preserve its runtime and require its own future candidate qualification |

Review facts separately: upstream support status, declared constraint, exact
source pin, installed interpreter, running process identity and actual consumer
qualification. Use current official Python/dependency evidence at review time.
An exact patch pin may require a coherent runtime/model/lock requalification;
neither a same-minor security release nor a root green job overrides that pin.
An unpinned native prerequisite remains with its existing platform owner.

Maintainers retain review date, source/release evidence, affected family,
disposition, accountable owner and next review condition in existing private
maintenance/lifecycle evidence. No new persistent schema or public host inventory
is introduced. A monthly review is a human maintenance expectation, not automatic
installation. Urgent security intake accelerates review and qualification without
waiving recovery or activation controls. If a fix cannot yet be qualified, record
the unresolved exposure and owner rather than declaring the runtime current.

## Behavior and compatibility contracts

| Given | When | Required outcome |
|---|---|---|
| Root floor is 3.12 and PR/main authority is 3.14 | 3.15 compatibility is added | Existing floor, PR check identities, required protections and older runtime coverage remain unchanged |
| Weekly/manual validation is requested | The candidate workflow runs | Full macOS suites cover 3.12, 3.13, 3.14 and 3.15 with Worktrunk 0.81.0, plus the retained 3.14/0.80.0 member; failure in one member does not cancel the others |
| A job requests 3.15 | Tests or child fixtures execute | The requested and observed standard CPython identities agree; an unavailable interpreter or mismatched child selection fails qualification |
| A month elapses or a relevant security advisory arrives | Maintenance reviews the runbook's Python families | Review every applicable declared owner, preserve disabled states, and record action or missing evidence without starting those tools |
| An isolated owner excludes 3.15 or requires an exact patch | Root 3.15 passes | Its constraint and qualification status remain unchanged; no installer, lock or runtime is rewritten |
| A 3.15 compatibility failure occurs | A repair is considered | Preserve original failure; repair only the demonstrated compatible issue, rerun affected oldest/newest targets, then refresh the full required candidate evidence |
| Candidate qualification fails or cannot finish | Source delivery is assessed | Report failure/unavailability and retain work; do not mask exits, waive tests, add broad skips or call the candidate qualified |
| A previously passing compatibility member regresses after merge | Weekly validation detects it | Prioritize repair and successful full-matrix rerun; preserve the failure and existing PR/main protections |

## Known porting evidence and acceptance

Source inspection found one concrete porting issue:
`tests/test_dbsctr_forgejo_transport.py` embeds a credential-child fixture that
calls `SourceFileLoader.load_module()`. Python 3.15 removes that method. The
fixture should use the supported module-spec/`exec_module` loading path while
preserving the isolated child, OS-home binding, sanitized Git environment and
synthetic credential assertions. This is a source finding, not an executed 3.15
failure or authorization to change credential behavior.

Build must inspect the stable 3.15 porting notes against affected source and
fixtures, including changed default text encoding and removed import APIs.
Qualification does not adopt lazy imports or any other new language feature.

Acceptance requires:

1. The unchanged root lock resolves/installs through existing CI dependency
   setup on the selected runtime. Use frozen lock validation and explicit
   interpreter selection; record exact Python patch and lock digest. Do not
   regenerate dependencies to conceal incompatibility.
2. The focused credential-child regression passes on 3.12 and 3.15 after its
   compatible repair, retaining the current security assertions. Other repairs
   need their own demonstrated trigger and focused oldest/newest checks.
3. Existing early publication/instruction, native Swift and full pytest
   authorities run on the candidate macOS 3.15/Worktrunk 0.81.0 job. Preserve
   existing 90-minute bound, read-only token permissions, triggers, cancellation,
   independent matrix results and all existing full-suite members.
4. At least one complete manual candidate matrix succeeds on the exact candidate
   source before declaring the added target qualified. The current exact-head
   PR jobs and other required checks also pass; no protection migration occurs.
5. Record deselected/skipped optional native workloads and their reasons. Root
   qualification does not claim real Dagger/SDK, model/MPS, Graphify, DVC, scanner,
   guest or remote-runtime qualification from mocks or skipped tests.
6. Review each changed consumer of the workflow/fixture and refresh this feature,
   the existing cadence contract, runbook and profile consistently. Complete the
   context CHANGELOG entry only after actual cycle outcome is known.

Configured root command: `uv run --group test pytest --maxfail=1`. Build uses its
frozen-lock, explicit-interpreter equivalent for qualification. The repository's
early authority remains the portable publication test plus
`tests/test_opencode_control_plane.py` and `tests/test_dbsctr_lifecycle.py`.
No new checker, linter, dependency or test-runner authority is selected.

## Current evidence and open risks

| Qualification state | Guard and next action |
|---|---|
| Proposed target | Discovery fixes scope and acceptance; no runtime qualification claim |
| Candidate prepared | Workflow, compatible fixture repair and cadence documentation identify one source revision; run the full candidate matrix |
| Candidate failed or unavailable | Preserve the result, repair only within scope or return for a scope decision, then refresh affected evidence |
| Candidate qualified | Full exact-source matrix and existing required checks pass; ordinary review/integration may proceed |
| Compatibility regressed after merge | Record the failing member and prioritize repair plus a successful full-matrix rerun |

Discovery inspected source at `12f5959701f8c075699b69ee5b4bac2cc5c2c535`.
Current CI ends at 3.14; no 3.15 full-suite result is claimed. Previous audit
tests are context only, not evidence for this candidate. The root lock currently
selects pytest 9.1.1. The observed `load_module` removal establishes a repair
requirement; other compatibility failures may emerge during qualification.

Official evidence checked on 2026-10-31:
[Python version status](https://devguide.python.org/versions/),
[Python 3.15 release schedule](https://peps.python.org/pep-0790/) and
[stable 3.15 porting notes](https://docs.python.org/3.15/whatsnew/3.15.html#porting-to-python-3-15).
Python 3.15 is stable; 3.12 remains in upstream security support. Recheck these
sources before Build rather than treating this dated observation as a new pin.

Risks: dependency or native fixture incompatibility; tests accidentally using a
different `python3`; CI duration beyond the current bound; optional skips hiding
an unqualified consumer; or shared documentation changing concurrently. These
are qualification risks, not approved exceptions. Existing owner-specific exact
pins remain a deliberate compatibility constraint. No material product decision
remains open for this bounded scope; implementation evidence remains pending.

## Gate applicability and Build handoff

| Gate | Applicability | Current result / rationale |
|---|---|---|
| Domain | required | pending: persist runtime roles, ownership and compatibility constraints in the Build cycle |
| Behavior | required | pending: retain the scenarios above and precise failure cases |
| Spec | required | pending: define the minimal workflow/fixture change |
| Contract | required | pending: enforce runtime selection and unchanged protections/pins |
| Test-driven implementation | required | pending: focused regression, old/new runtimes and full candidate matrix |
| Refactor | required | pending: remove only justified duplication without expanding scope |
| Review/Integrate | required | pending: exact-head review, source publication and existing native checks |
| Release | not_applicable | No package, wheel, model or separately versioned release artifact is published |
| Deploy | not_applicable | Source/CI delivery only; no managed host, guest, SDK, service or tool activation |
| Operate | not_applicable | No live service/runtime operation or new availability commitment |
| Maintain/Retire | required | pending: monthly/urgent review policy, failed-qualification recovery and unchanged owner handoff |

The canonical [machine plan](../../../initiatives/python-runtime-qualification/SOURCE.plan.json)
is packaged by the [one-slice import handoff](../../../initiatives/python-runtime-qualification/README.md).
Build copies it into its Git-ignored `.dbsctr/plans/` directory after verifying
the committed profile. Discovery does not register a cycle or fabricate the
profile's commit identity.

Next task: one Build primary implements the hosted weekly/manual 3.15 addition,
explicit frozen interpreter selection and the demonstrated compatible fixture
repair, then owns all affected validation. No runtime owner upgrade is delegated.
Retain all Discovery artifacts in the implementation change; do not publish a
preliminary documentation-only PR merely to make registration possible.

The complete changed-document closure is this feature, distribution `PROFILE.md`
and `README.md`, `docs/UPDATES.md`, lifecycle `features/early-delivery-checks.md`,
and the one-slice import README, manifest and machine plan. The distribution
CHANGELOG and existing Product Intent were reviewed; their current content needs
no Discovery change.

Unmerged Discovery commits cannot be passed to ordinary `begin` as though they
were the approved remote base. Build preserves this authority, prepares one clean
code-only checkout through the existing Worktrunk template at a freshly fetched
approved base, and packages the complete closure through the existing Initiative
import route. That packaging retains one implementation context and the selected
scope; it does not create parallel context work or change product decisions.
Before registration, Build runs the existing publication authority, fresh
receipt and real preflight, presents the concrete scope/risk/target/launch digest,
and obtains exact chat approval before the native registration call. Discovery
does not supply terminal consent, bypass base checks, register a cycle or claim
that a shell directory change retargets a conversation.

Specification and one-slice import artifacts are ready for this scope. Fresh
receipt/preflight, launch feasibility and candidate runtime qualification remain
unverified until Build performs those native checks; this is not launch approval.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: Runtime and ownership boundary table separates root, advisory and isolated owners |
| Interaction | required: Behavior and compatibility contracts table orders review, qualification, failure and delivery |
| State | required: Current evidence and open risks transition table distinguishes proposed, prepared, failed, qualified and regressed targets |
| Data/trust | not_applicable: no credentials, private host inventory or consumer data crosses a new boundary; existing publication authority applies |
| Schema | not_applicable: no persistent schema or registry is added |
| Dependency/deployment | required: Runtime and ownership boundary table and selected scope define unchanged isolated deployments and hosted qualification |
| Quantitative | not_applicable: no speedup, capacity or cost comparison is claimed |

**Text Equivalent:** Distribution maintains root compatibility validation and
reviews every declared Python owner monthly or urgently on security intake. Root
3.15 remains a candidate until exact-source full qualification passes. PR/main
3.14, the 3.12 floor and isolated runtime constraints remain unchanged. Failed
qualification preserves evidence and returns bounded repairs; it cannot activate
an isolated runtime. Canonical sources: the three tables and acceptance above,
plus the existing CI cadence contract. Owner: distribution maintainers. Update
trigger: runtime ownership, support target, cadence, workflow authority, pin or
qualification-boundary changes.
