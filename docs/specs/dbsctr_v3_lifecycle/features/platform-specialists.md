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
When native catalog metadata is cached, selection can inspect the exact named
managed sibling relative to the known installed DBSCTR root, verify its name and
read its guidance. This does not register discovery, scan unrelated runtime homes
or install a replacement; actual discovery observations remain separate.

The inventory records complete upstream and packaged file sets, Git blob and
SHA-256 identities, immutable commit/source roots, license and adaptation notes,
patch hashes, retained source modes and declared installed modes. Repository-root licenses are copied
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

## Contracts and validation

- Existing user scope, native permissions, project tools/targets, DBSCTR and QA
  remain authoritative. Skill loading does not authorize tool installation,
  cluster/host mutation, role changes, publication or source/commit choreography.
- Target identity includes the applicable OS/release, shell/dialect, user versus
  system service scope, container ownership, cluster/namespace, cloud project and
  location, or SDK/channel/device. Use existing project facts before asking;
  unresolved material identity is not filled from an ambient default silently.
- Preserve original diagnostic failures, child exit status, missing capabilities
  and uncertainty. Rendering is not deployment; async command submission is not
  readiness; a plausible offline cause is not a verified root cause.
- Adapt upstream policy in supporting references/templates/helpers as well as
  entrypoints. Retain complete resources and exact license notices with reversible
  patches; no fetched content executes during acquisition or installation.
- Shell examples preserve supported versions, caller variables, child statuses,
  cleanup and signals. Strict mode is contextual; broad diagnostic suppression and
  an unconditional new shell/test framework are not acceptable shortcuts.
- Async guidance covers structured task ownership, cancellation propagation and
  draining, bounded work and resources, event-loop ownership and thread/process
  tradeoffs tied to the selected runtime. Retain safe SQL parameter binding and
  response/session lifetimes in supporting examples.
- Host/container guidance preserves SELinux, TCC, signing and service ownership;
  security weakening is not an automatic fix. Podman storage labels, UID mappings,
  user/system units and persistent data are explicit compatibility concerns.
- GCP/GKE guidance keeps credentials out of output, uses explicit target/identity,
  distinguishes IAM from Kubernetes RBAC, and proposes bounded fixes. Remove
  forced telemetry, universal quiet flags, fabricated RCA and competing PR flows.
- The Helm helper performs bounded local lint/render checks only, preserves real
  failures and has offline failure-path regression evidence. Library charts use
  explicit lint-only mode and require consumer-chart rendering for helper behavior;
  lint-only success does not claim rendering. It cannot infer
  cluster acceptance or install tools/charts merely because guidance is loaded.
- Mojo examples are conditional on the project SDK/channel and hardware. Preserve
  selected environment managers and pins; validate interop/ABI and GPU semantics
  with actual target evidence when required. No dynamic Python source assembly
  from untrusted interop values; absent SDK/GPU evidence remains a capability gap.
- Modernization review uses current primary version/migration sources and project
  support constraints. Classify mechanical, semantic and architectural findings;
  new features alone do not justify upgrades or broad refactoring.
- Validate new entrypoints with the original creator validator. Source contracts,
  provenance/resource/script checks and realistic independent routing cases are
  separate evidence; static size measurements are not token-savings claims.
- Deployment uses explicit selected source/machine configuration, scripts excluded,
  exact reviewed targets and verified prior state. New bundles/modules/references
  must match complete source file sets, bytes and declared projected modes; repeated apply
  has an empty diff and preserves unrelated installed skills.
- The source Helm helper retains its original executable mode. Chezmoi's normal
  resource projection installs it as a readable 0644 file, invoked explicitly
  through Bash as documented. Source/upstream modes and installed modes are
  separate inventory fields and validation claims; installation executes no helper.
- For an existing divergent installed entrypoint, preserve disjoint unrelated
  instructions through a reviewed three-way projection of prior source, current
  installed bytes and changed source. Keep that projection/preimages privately;
  verify intended routing hunks and retained live content independently. Do not
  adopt unrelated live policy into Git or claim canonical byte identity for the
  reconciled overlay. An overlapping unresolved change blocks that target.
- Recovery restores complete reviewed bundles and matching inventory/routing;
  retain prior installed preimages and reconcile divergent ownership. Do not
  remove unrelated skills, alter provider settings or execute target operations.

| Transfer | Guard and evidence |
|---|---|
| Upstream to managed source | Immutable commit and original blobs, retained license, reviewed adaptations and complete inventory |
| Task to specialist | Minimum decision-relevant context under current provider/scope; explicit target and relevant resources |
| Specialist to primary/QA | Bounded findings, actual evidence, remaining hypotheses and missing capabilities; existing artifacts/gates |
| Source to shared installation | Isolated exact-target validation; verified preimages and bytes/modes or explicit reconciled-overlay identity |

| Delivery dependency | Evidence |
|---|---|
| Source bundles | Valid entrypoints, resource closure, complete inventory and reversible patches |
| Bounded helper | Isolated Helm failure/status checks with a fake local tool; no live cluster operations |
| Router behavior | Positive/negative/mixed-layer independent cases and explicit sample limits |
| Isolated projection | Full selected file sets/modes, unrelated sentinel preserved, empty second diff |
| Shared projection | Prior-state review, exact-target preview/apply, complete verification and retained recovery bytes |
| Discovery | Current native catalog observation when available; filesystem state is a separate claim |

**Text Equivalent (trust and delivery):** Reviewed immutable upstream content enters
managed source with licenses and reversible provenance. The primary passes only
relevant authorized task context into selected guidance, then reconciles its
findings with QA. Isolated projection precedes shared deployment. Canonical source
bytes and preserved unrelated live overlays have distinct verification claims.
Owner: lifecycle/distribution maintainers; update with any represented boundary,
execution, target, provenance or recovery change.

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


## Native router qualification

### Domain and ownership

This follow-up qualifies actual automatic skill selection and token usage before
changing descriptions or removing duplicated routing. The native client remains
the selector; DBSCTR remains instruction-driven. The evaluation is a bounded,
explicitly invoked maintenance authority, not a new dispatcher, service, session
coordinator or universal coding gate. Python, ML/AI and Security modules apply.

| Value or owner | Responsibility |
|---|---|
| Task case | A synthetic repository, ordinary task request, independently declared expected/forbidden guidance and split |
| Guidance snapshot | Complete selected source bytes, metadata, native catalog and invocation configuration identities |
| Native observation | Actual catalog visibility, completed reads/tool events, final result and provider-reported usage for one fresh run |
| Paired comparison | Matched cases/repetitions and balanced order; quality and observed usage remain separate outcomes |
| Current primary and QA | Own evaluation execution, review, acceptance, lifecycle and delivery |
| Private cycle evidence | Retain raw native events, local identities, failed runs and recovery material outside public source |

Public fixtures contain only synthetic source and portable methodology. Existing
account credentials remain in their native owner; no copied authentication,
changed global configuration, new account, provider switch, model migration or
infrastructure mutation is part of qualification. The configured native model and
provider stay fixed across each comparison. Missing observations remain missing.
The existing source-only OpenCode compression fixture keeps its separate purpose
and unavailable usage/cost fields; native router evidence cannot relabel it.

### Native qualification behavior

| Given / when | Observable outcome |
|---|---|
| An ordinary synthetic task implicitly matches a specialist | Observe the native catalog and successful body/resource reads; naming a skill in the answer is insufficient |
| A task is adjacent but needs no specialist | Preserve the negative case; unrelated tracked loads are visible |
| A task crosses platform/language concerns | Select only justified techniques and retain project-selected tools and target boundaries |
| An existing property suite shrinks a counterexample | Evaluate the existing property and implementation without replacing the project test authority |
| A native catalog omits an unregistered but readable managed sibling | Test exact-sibling recovery separately; do not call this cache-staleness proof or override an explicit disable policy |
| Native output lacks usage, fails or times out | Retain the attempt and unavailable fields; do not infer tokens from characters, bytes, answer length or account percentages |
| Direct implicit selection bypasses DBSCTR references | Count its selection and end-to-end usage only; it cannot prove savings from module/reference deduplication |
| An explicit DBSCTR navigation control exercises the changed route | Label it separately from implicit-trigger results |
| Descriptions change after development observations | Freeze candidate bytes before revealing held-out cases and preserve the original baseline |
| Python routing is maintained | Keep one canonical six-technique table in the Python module; retain unique method/provenance notes in the reference |
| A qualified candidate is deployed | Preserve complete bundles, native default model/provider, unrelated live edits and existing gate/authorization semantics |

The predeclared case set separates four development tasks from eight held-out
tasks. Run both snapshots on identical synthetic inputs; keep expected skill and
quality decisions scorer-owned. The current native CLI exposes the two long Python
descriptions in full, so conversation-catalog shortening is not a proven native
selection failure. Native discovery, loading, instruction compliance and completed
validation remain distinct observations.
