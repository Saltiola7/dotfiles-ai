# Conditional Platform and Language Specialists

## Domain and scope

The existing lifecycle Engineering Profile applies. This elevated-risk feature
extends the established conditional Python-specialist pattern to shell reliability,
host operations, Podman/Quadlet, Kubernetes, Google Cloud, async Python,
modernization review and the explicitly requested official Modular Mojo skills.
The bounded context remains `dbsctr_v3_lifecycle`; distribution owns installation.
Applicable modules are Python, Cloud, Security and ML/AI. Shell and Mojo are new
thin language modules, implemented within this feature.

| Owner | Responsibility |
|---|---|
| Native client catalog | Expose names/descriptions and available skill locations |
| DBSCTR core and primary | Select applicable modules, preserve lifecycle/authorization and reconcile findings |
| Language/platform module | Recognize task evidence and select the smallest useful specialist set |
| Project profile | Select runtimes, tools, environments, target identities and acceptance authorities |
| Specialist | Supply bounded methods and relevant supporting resources |
| QA | Execute configured validation and report real evidence and gaps |
| Distribution maintainer | Review pins/licenses/adaptations, validate full bundles, deploy and recover |

Selected upstream skills are `bash-defensive-patterns`, `bats-testing-patterns`,
`async-python-patterns`, `k8s-manifest-generator`, `helm-chart-scaffolding`,
`gcloud`, `google-cloud-recipe-auth`, `gke-workload-troubleshooting`,
`gke-workload-identity`, `mojo-syntax`, `mojo-gpu-fundamentals`,
`mojo-python-interop` and `new-modular-project`.

Locally maintained specialists are `linux-host-diagnostics`, `macos-operations`,
`podman-quadlet` and `python-modernization-review`. Existing Python specialists
and externally owned macOS app-development skills retain their ownership.

Terraform is excluded by user instruction. Pulumi, Hetzner, Dagger and Django
are research candidates for operator consideration, not automatic installation.
MAX model-lifecycle bundles, tool/SDK installation, target infrastructure changes,
provider authentication changes and a new router service are outside this slice.

## Router model and efficiency

Selection is model-driven progressive disclosure, not a deterministic runtime
dispatcher. Catalog metadata supports initial selection; the selected DBSCTR
module supplies short evidence triggers; a selected skill supplies its method;
only relevant resources are then read. Presence of a platform or file alone does
not justify every specialist associated with it. Task intent and changed scope
distinguish authoring, diagnosis, migration and deployment.

Keep one primary and existing gate ownership. Names/descriptions should discriminate
tasks cheaply; modules hold compact routing tables and short obligations; long
examples and mode-specific detail belong in linked resources. Runtime prompt
caching or compaction behavior remains client-owned and is not guaranteed here.
Skill loading is guidance availability, not proof of execution or acceptance.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: ownership table above |
| Interaction | required: progressive-disclosure table below |
| State | not_applicable: no new dispatcher state; existing lifecycle remains canonical |
| Data/trust | required: source and target transfer table added with contracts |
| Schema | not_applicable: reuse the existing provenance inventory schema |
| Dependency/deployment | required: bundle projection table added with contracts |
| Quantitative | not_applicable: no token-saving or effectiveness claim without measured evidence |

| Selection stage | Input | Loaded detail |
|---|---|---|
| Catalog | Task and available names/descriptions | Metadata supplied by the native client |
| Module | Actual language/platform/operation evidence | Applicable language/platform obligations and compact triggers |
| Specialist | A concrete task concern | One or a small applicable set of skill entrypoints |
| Resource | A specific question or operation | Only relevant references/assets/helpers, inspected before execution |
| Return | Findings, evidence and limitations | Existing artifacts and QA/gate decisions owned by the primary |

**Text Equivalent:** The native catalog describes available skills. The primary
uses current task evidence to select DBSCTR modules, then bounded specialists,
then needed resources. Results return to the existing primary and QA; no stage
creates another coordinator or grants permission. Canonical source: this feature
and module routing tables. Owner: lifecycle maintainer. Update when selection,
authority, loading or delivery boundaries change.
