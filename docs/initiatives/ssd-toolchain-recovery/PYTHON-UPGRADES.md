# Non-production Python runtime and dependency upgrades

**Paused by INT-032 (2026-10-07):** no further environment updates or live
activation in this session. Preserve completed deliveries, current environments
and rollback evidence. Remaining work belongs to a separate operator session.

Coordinator: python_maintenance_discovery in dotfiles-ai. Each owning project
provides its implementation context/profile and lockfiles. This coordinator cannot
authorize writes to all repositories through one aggregate Build slice.
Risk: elevated until production coupling and shared interpreter consumers are known.

## Approved version policy

Upgrade Python patch versions within each existing minor pin. Upgrade project
dependencies to latest stable releases allowed by existing constraints, including
major dependency versions when permitted. Explicit upper bounds and exact pins
remain authoritative. Widening a constraint or changing a Python minor returns to
Discovery. Resolve conflicts and runtime incompatibilities before activation.

Exclude the designated private project entirely and all production environments.
For other private projects, only explicitly classified development environments
are in scope; production and shared production inputs remain protected.
No project code changes, installs or environment syncs occur during inventory.

INT-028 defers content-evidence-workbench and search-taxonomy-lab upgrades until
needed. Retain isolated candidate evidence; do not activate those candidates or
continue their upgrade work as a prerequisite for the remaining maintenance.

## Inventory record and candidate selection

Expanded linked-checkout and tool-environment observations:
[maintenance follow-up](findings/maintenance-follow-up.md). The bounded scan is
not a production classification or blanket environment upgrade authorization.

For every primary, linked checkout, tool and guest environment, privately record:
owning repository/context; interpreter path/version/minor pin; environment manager;
manifest/lock paths; working-tree changes; direct/shared production consumers;
classification (development, production, shared, recovery archive, unknown);
installed-dependency health; proposed candidate; available validation; activation
and recovery method. Inventory retained clones, but never treat archives as live
upgrade targets merely because a .venv exists. Unknown/shared consumers block
activation until classified. Do not overwrite another writer's dirty environment.

Existing preliminary inventory covers content-evidence-workbench, search-taxonomy-lab,
dotfiles, dotfiles-ai and several private project environments; it is not exhaustive.
Some private project environments were repaired by preserving interpreter identity,
not upgraded.
Fresh enumeration must include linked checkouts and guest/tool environments.

## Private project production boundaries

Keep exact private repository identities, dependency manifests, runtime versions,
production paths and project-specific validation commands in private inventory.
For each project, identify which development inputs are shared with production
before selecting an isolated candidate. Preserve every applicable version ceiling,
Python minor pin and production-owned manifest without copying their details here.

Read the selected project's own instructions and CI configuration for its test,
lint, type-checking and vulnerability authorities. Use credential-free mocks or
isolated runtime checks; never invoke production flows or write to live databases.
Historical dependency resolution is preliminary evidence, not current runtime
qualification. Source remains authoritative when generated metadata is stale.

## Behavior and validation

| Given | When | Required outcome |
|---|---|---|
| Classified development environment | Candidate resolves in isolation | Original environment, lock and uncommitted work unchanged |
| New dependency major allowed by constraints | Candidate is tested | Affected imports/API behavior/tests pass before activation |
| Python patch candidate | Existing minor pin checked | Same minor, working SSL/SQLite/imports and compatible installed dependencies |
| Failure or unclassified production consumer | Upgrade considered | Retain healthy original; report exact blocker |
| Qualified candidate | Activation occurs | Lock and environment agree; repeat frozen sync/check succeeds |
| Existing environment needed for recovery | New candidate fails | Retain original path/identity until rollback method is proven |

Use native manager commands appropriate to the project: dry-run resolution is
preliminary evidence; isolated environment installation plus uv pip check (or
equivalent), interpreter/SSL/SQLite smoke, critical imports and affected configured
tests are required. Record red baseline versus candidate failures distinctly.
Do not run production flows or acquire production datasets to validate development.
Use targeted DVC data only if explicitly required and available under existing rules.

Sequence each private project's minimal interpreter/dependency compatibility repair
first, then the broader allowed dependency refresh. Do not mistake a successful full lock solve for
safe activation. Shared interpreter patch installation is owned by host-tools;
per-project environment replacement is owned by the project slice.

## Promotion requirements

After inventory, create a slice per independently writable owning project/context,
with concrete environment/manifest paths, selected candidate versions, production
exclusions, profile, configured QA commands, rollback and explicit dependencies.
Kernel/review/deploy/operate/maintain required for behavior changes; pure dependency
maintenance may use the configured lighter path with equivalent checks. Release
N/A unless a project actually publishes a package. Do not fabricate profiles for
unknown repositories or issue a launch receipt from this umbrella.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: inventory classifications and protected private-input boundaries |
| Interaction | required: isolate, resolve, runtime-test, activate sequence |
| State | required: behavior table |
| Data/trust | not_applicable: no production data movement or calls authorized |
| Schema | not_applicable: native lock formats reused |
| Dependency/deployment | required: project/host ownership sequence above |
| Quantitative | not_applicable: historical counts are not coverage claims |

**Text Equivalent:** classify every consumer before touching its environment;
candidate checks happen in isolation, with Python minor pins and production inputs
preserved. Dependency majors may advance only within constraints and after runtime
qualification. Owner: each project maintainer; canonical source: this contract;
update when classification, version policy or protected consumers change.
