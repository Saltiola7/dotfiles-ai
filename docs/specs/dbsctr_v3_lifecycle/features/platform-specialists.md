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

## Behavior

| Given / when | Required outcome |
|---|---|
| Shell behavior changes | Load shell obligations and relevant reliability guidance; preserve selected dialect/version, exit status, signals and test authority |
| Bash 3.2 or POSIX sh is selected | Do not copy unsupported Bash features or install another shell to make an example work |
| Project tests shell through pytest/subprocess | Preserve that authority; Bats guidance is conditional on Bats being selected |
| A Linux host problem is investigated | Establish distro/release and user/system scope; diagnose with bounded facts before proposing changes |
| A macOS agent works in Terminal but fails under launchd | Inspect launch domain, environment, identity, logs and TCC context; preserve security mechanisms and existing grants |
| Rootless Podman/Quadlet changes | Resolve user namespace, unit ownership, storage labels/network and persistent data; distinguish generated units from authored source |
| Kubernetes manifests or Helm charts change | Load the corresponding authoring specialist; rendering/linting is not cluster admission or rollout evidence |
| GCP/GKE diagnosis is requested | Resolve explicit project/location/cluster/namespace and identity from existing authority; inspect bounded evidence and preserve uncertainty |
| A GKE identity check is proposed | Use non-secret identity/permission evidence; never print bearer tokens as connectivity proof |
| Required target evidence is unavailable | Preserve the missing capability; offline hypotheses are not an established root cause or a passing gate |
| Concurrent Python code changes | Load async guidance for task ownership, cancellation, bounded concurrency, cleanup and sync/async boundaries |
| A Python support-floor or modernization audit is requested | Compare target-version evidence with project constraints; classify findings before bounded remediation |
| Mojo source or a Mojo/Python boundary changes | Load Mojo obligations and selected official guidance, bound to the project SDK/channel, ABI and target |
| Mojo GPU code changes | Select GPU guidance only with an actual device concern; require supported target and equivalent synchronized correctness/performance evidence |
| A new Modular project is explicitly requested | Preserve selected environment manager and SDK pins; setup authorization does not follow from loading a skill |
| A task merely mentions a platform or makes a trivial text edit | Avoid loading unrelated specialists or entire upstream repositories |
| Guidance is absent or new evidence changes the concern | Use equivalent guidance when sufficient or revise selection in the existing cycle; no new coordinator or invented gate |
| A reviewed bundle is deployed | Exact-target projection preserves complete resources and unrelated live files; bytes/file sets and repeated application are verified |

## Interfaces and selection

| Concern | Routing surface | Preferred skill |
|---|---|---|
| Changed shell execution semantics | Core selects `modules/shell.md` | `bash-defensive-patterns`; Bats only when selected |
| Async correctness or explicit version/debt review | Existing Python module/reference | `async-python-patterns`, `python-modernization-review` |
| Linux/macOS host diagnosis and operation | Existing Cloud module plus platform reference | `linux-host-diagnostics`, `macos-operations` |
| Podman rootless/user-unit/container lifecycle | Existing Cloud module plus platform reference | `podman-quadlet` |
| Generic Kubernetes manifests or Helm chart work | Existing Cloud module plus platform reference | `k8s-manifest-generator`, `helm-chart-scaffolding` |
| Actual GCP CLI or identity selection | Existing Cloud module plus platform reference | `gcloud`, `google-cloud-recipe-auth` |
| GKE workload failure or workload identity | Existing Cloud module plus platform reference | `gke-workload-troubleshooting`, `gke-workload-identity` |
| Mojo source, GPU code, interop or selected setup | Core selects `modules/mojo.md` | Corresponding selected Modular skill |

`references/specialist-selection.md` holds the common loading/return contract.
`references/platform-specialists.md` holds host/container/cloud selection detail;
the Python reference retains Python-specific decisions. Modules keep only useful
triggers and obligations. Existing plugin-owned macOS app skills are resolved by
catalog capability when relevant, without copying their implementations.

All selected skills remain independently discoverable sibling directories under
`dot_agents/skills/`. New vendored packages use the existing schema-1 provenance
shape in `dbsctr/references/specialist-sources/sources.lock.json`, with reversible
patches beside it. Existing Python provenance stays in its current owner. No new
package resolver or updater runs during ordinary skill selection.

The inventory records complete upstream and packaged file sets, Git blob and
SHA-256 identities, immutable commit/source roots, license and adaptation notes,
patch hashes and retained executable modes. Repository-root licenses are copied
verbatim per bundle; complete supporting references/assets/helpers are preserved.
Original sources are pinned to wshobson/agents `7e2fb559cf4b824b27f1fec49fe88f7511066d26`,
google/skills `bb9b3f464aae37af360d079c1d863524955b0363` and modular/skills
`1b2cc565ca7e0a8b66d96b4ee78fdfb7ec443a88`. Modular's exact composite license
notice, including LLVM exceptions and legacy terms, remains intact.

Validation extends existing lifecycle/publication/distribution authorities with
complete inventory drift and reverse/reapply checks, selected-resource closure,
exact-target isolated delivery and an offline regression of the Helm helper.
Independent task cases evaluate positive, negative and mixed-layer selection,
project policy, unavailable evidence and resource restraint. Static entrypoint and
metadata sizes describe packaging footprint only; they do not measure runtime
context, model reliability or token savings.

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
