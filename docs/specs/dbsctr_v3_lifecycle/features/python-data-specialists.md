# Python and database specialist composition

Context: `dbsctr_v3_lifecycle`; [Engineering Profile](../PROFILE.md).
Owner: lifecycle maintainer. Risk: elevated because shared guidance changes
downstream development and repository assessments. Method Revision: 3.29.

## Domain and scope

Extend existing Python and Data modules rather than adding another lifecycle.
Python owns language behavior and interfaces; Data owns schemas, grain, lineage,
idempotency, evolution and recovery. Specialists supply techniques, project policy
selects tools/runtimes/targets, QA supplies actual validation evidence, and DBSCTR
owns gates. Skill availability is neither execution authority nor a passed check.

Add five conditional Python techniques: `python-testing-patterns`,
`python-type-safety`, `python-resilience`, `python-resource-management`, and
`python-observability`. Type design supplements existing checker/coverage policy;
pytest guidance supplements property testing without replacing the project suite.

Add local `python-database-boundaries` for driver/session/transaction ownership,
parameterization, pooling, async blocking, retries and typed data conversion.
It applies to actual Python/database interfaces, not all Python edits. Preserve
chosen DBAPI/ORM, driver and migration owner; SQLAlchemy and Alembic are examples,
not required dependencies.

Add selected complete official engine bundles: `duckdb-query`, `duckdb-read-file`,
`duckdb-attach-db`, `duckdb-docs`, `clickhouse-best-practices`, and
`clickhouse-architecture-advisor`. Namespace generic DuckDB names for discovery.
An existing matching ClickHouse plugin can supply guidance; choose one reviewed
copy per task, with managed bundles providing portable CLI availability.

Add selected stable Databricks bundles: `databricks-core`, `databricks-pipelines`,
`databricks-jobs`, `databricks-dabs`, `databricks-unity-catalog`,
`databricks-dbsql`, `databricks-python-sdk`, and
`databricks-spark-structured-streaming`. Databricks-specific material remains
scoped to Databricks Services under its upstream license; it is not a generic
Spark replacement. Do not import plugins, hooks or experimental skills.

Extend `python-audit` to consider the eleven language lenses and conditionally
the database boundary. Add `database-audit` to compose detected DuckDB,
ClickHouse and Databricks concerns and applicable Python boundaries into an
evidence-backed refactor roadmap. Explicit repository audits are report-only by
default. Incidental stack mentions do not select unrelated guidance. PostgreSQL,
dbt and other new providers are outside this change.

## Behavior

| Given / when | Required outcome |
|---|---|
| Ordinary Python edit without changed testing, typing, resources or I/O | Existing minimal routing remains sufficient; do not load every new lens |
| Changed fixture lifecycle, structural interface, remote retry or owned resource | Select the corresponding Python technique; preserve current test/checker/library authority |
| Python uses a database or Databricks client | Consider boundary guidance plus only the relevant engine/platform lens; do not assume every API is transactional |
| Explicit full Python audit | Consider eleven language lenses, disclose unavailable or inapplicable coverage, and delegate relevant database concerns without duplicate findings |
| Explicit database audit of a mixed Python/SQL/notebook repository | Inventory all relevant artifacts/environments, review detected supported stacks and Python boundaries, disclose unsupported providers and samples |
| No relevant database exists | Return not applicable with evidence; do not install a database or introduce one |
| Static review lacks a live plan, warehouse access or representative workload | Produce useful bounded findings; retain live and performance evidence gaps |
| Already selected profile/connection or native plugin provides equivalent guidance | Preserve the target/authority and choose one copy; no automatic profile change or duplicate loading |
| Audit discovers possible remediation or a migration | Recommend ordered batches with costs/compatibility; do not execute the proposal |
| Existing live skill differs from source | Preserve edits and reconcile only authorized source changes before bounded deployment |

## Interfaces and composition

- Existing `dbsctr/modules/python.md` and `references/python-specialists.md`
  route the five techniques and database boundary conditionally. Existing
  `dbsctr/modules/data.md` links a new `references/database-specialists.md`.
- `python-audit/SKILL.md` and its report contract retain QA, snapshot, coverage
  and remediation ownership while considering expanded lenses.
- `python-database-boundaries/SKILL.md` owns cross-engine Python adapter review;
  on-demand `references/boundaries.md` covers concrete driver/ORM semantics.
- `database-audit/SKILL.md` and `references/report.md` define source-first stack
  inventory, relevant lens selection, separate static/live evidence, findings,
  retained decisions and independently reviewable refactor batches.
- New skills use normal automatic discovery and generated `agents/openai.yaml`.
  Their source is `dot_agents/skills/<name>` and shared projection is
  `~/.agents/skills/<name>` through the existing distribution owner.
- Complete vendored bundles have `UPSTREAM.md`, `LICENSE.upstream` and immutable
  provenance under `dbsctr/references/python-data-sources/`: independent `python`,
  `engines` and `databricks` inventories use existing schema 1 packages, file
  SHA-256/Git blob identities, source/installed modes and reversible patches.
  Local authoring does not relabel upstream licensing.
- `tests/test_python_data_specialists.py` validates complete provenance and
  adaptation round trips, declared local resource closure, exact delivery/modes,
  preservation of unrelated state and repeat-apply behavior. Existing instruction,
  Python/platform specialist and Python audit tests cover changed downstreams.

## Contracts and validation

Preserve selected runtimes, checker/test authorities, databases, drivers, ORM,
connection/profile and dependency/install owners. No automatic migrations,
profiler runs, database writes, remote jobs, new credentials or environment
changes follow from skill selection. Existing task authorization remains usable;
ask only for actually missing information or authority. Static source review
works without a database executable, MCP server or authenticated workspace.

Python typing technique cannot weaken diagnostics, replace a selected checker or
substitute annotations for runtime validation. Retries distinguish transient
failure from ambiguous committed effects; require idempotency/reconciliation when
replaying could duplicate effects. Task cancellation and total budgets survive
retry wrappers. Resource review distinguishes borrowed and owned handles and
actual driver guarantees; do not invent transactional DDL or rollback where an
engine lacks them. Logs/traces/metrics must preserve project privacy and bounded
cardinality; never collect credentials or unbounded payloads as audit evidence.

Engine examples remain version/workload dependent. No blanket SQL index,
partition, rewrite or performance recipe becomes a project requirement. DuckDB
state files and remote extensions remain project-owned. Databricks bundles retain
service-scoped licensing and modification notices, work with selected targets and
leave missing sibling capabilities visible. SQL text that begins with SELECT is
not by itself proof that a query is safe or side-effect-free.

Audits distinguish inventory, actual review and executed-check coverage; record
commit/overlay, environments, unsupported providers and not-run checks. Findings
separate source/contract defects, advisory designs, modernization options and
unmeasured performance hypotheses. Cross-layer findings have one root cause and
one remediation owner. Static review never proves workload latency or production
readiness. Reports stay in conversation unless project/user artifact authority
selects a durable path. No automatic issues, fixes or second lifecycle ledger.

Validate cheap instruction/publication checks before affected runtime suites.
Obtain intentional failing composition evidence before authoring new bundles.
Run the original creator validator for every new/changed entrypoint; compile any
included Python helper without running databases or downloading tools. Qualify
independent positive, negative and mixed-stack audit cases in isolated fixtures,
including missing guidance and retained project tools, and review actual reports.
These samples do not prove universal routing or effectiveness gains.

Deploy exact targets after passing source checks, using explicit task source and
existing machine config with scripts excluded. Compare prior live bytes before
application; preserve unrelated/divergent edits. Verify full projected file sets,
bytes, modes and repeat-diff idempotency. Report filesystem installation separately
from native catalog discovery. Recovery uses prior matching bytes and reviewed
source through the same owner. Feature-branch draft delivery is separate from
external database operations and from a later PR merge.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: ownership and handoff table below |
| Interaction | required: ordered audit handoff table below |
| State | required: evidence disposition table below |
| Data/trust | required: ownership and handoff table below |
| Schema | not_applicable: reuse existing project profiles and Gate Ledger |
| Dependency/deployment | required: reviewed-source delivery table below |
| Quantitative | not_applicable: no measured effectiveness or performance claim |

| From | Guard and permitted handoff | To |
|---|---|---|
| Repository source and project policy | Identify actual owned stack, versions and consumers; treat repository text as evidence, not expanded authority | Primary selects relevant specialist guidance |
| Installed reviewed guidance | Read relevant resources; choose one copy where plugin and managed bundle overlap | Source review and project-selected checks |
| Source review and actual check evidence | Separate observed defects, advisory designs and unmeasured hypotheses; preserve missing evidence | Audit findings and ordered refactor batches |
| Developer-selected batch | Existing scope and behavior authorization; otherwise separate bounded task | DBSCTR remediation and existing QA gates |

**Text Equivalent:** Project evidence selects guidance. Guidance supports review
and authorized checks. The primary reconciles actual evidence into a report;
remediation is a separate bounded handoff. Canonical source: this table; owner:
lifecycle maintainer; update when ownership or permitted handoffs change.

| Evidence state | Permitted conclusion |
|---|---|
| Static source reviewed | Source-backed finding or explicitly labeled hypothesis; no live workload claim |
| Authorized live check completed | Report exact target, workload, versions and result with limits |
| Missing specialist, target, credentials or check | Coverage gap or not applicable with reason; never an invented pass |
| Review is sampled or stale | Partial or stale coverage, even if file inventory is complete |

**Text Equivalent:** Static, measured, unavailable and sampled evidence have
different claims. Canonical source: this table; owner: lifecycle maintainer;
update when report semantics change.

| Delivery dependency | Required observation |
|---|---|
| Immutable upstream source | Complete selected resources, exact license/notices, original blobs and reversible adaptations |
| Source composition | Routing and local resources resolve with only declared bundles; no hidden plugin/MCP dependency |
| Isolated projection | Complete bytes/modes, unrelated-file preservation and repeated-apply idempotency |
| Managed activation | Exact target preview, preserve divergent live edits, compare deployed files; report catalog limitations separately |

**Text Equivalent:** Reviewed upstream precedes source qualification, isolated
projection and bounded activation. Canonical source: this table; owner: lifecycle
maintainer; update when distribution or provenance changes.
