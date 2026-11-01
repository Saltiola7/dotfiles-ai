# OpenShell pilot runtime qualification

Status: specification for the first `runtime-qualification` delivery slice.
Owner: distribution maintainers. Engineering Profile: [../PROFILE.md](../PROFILE.md).
Product Intent: [../PRODUCT.md](../PRODUCT.md). Initiative authority:
[OpenShell pilot](../../../initiatives/openshell-pilot/README.md).
Specification readiness is not evidence of a working runtime or permission to
activate an existing workload.

## Outcome and slice boundary

Qualify a minimal Fedora 44 aarch64 Lima worker on Apple Silicon macOS, using
rootless Podman and OpenShell v0.1.6. The worker runs only synthetic fixtures in
this slice. It must expose one synthetic registered linked worktree for direct
source edits while denying unrelated filesystem, network and control-plane
access. Unsupported isolation remains an explicit failed or unavailable result.

The completed pilot must eventually preserve both Codex CLI subscription access
and OpenCode with Vertex Claude, the full supported Git workflow through a
restricted host helper, existing Worktrunk checkouts, and opt-in activation on
the selected Mac. Runtime qualification alone satisfies none of those dependent
acceptance claims. Provider bootstrap, authenticated agents, the host Git helper,
production installation and real-repository enrollment are separate slices.

Current-cycle overrides are elevated risk for disposable runtime qualification;
later host authorization work retains its separately classified risk. Applicable
modules are Python, Security and Cloud; embedded Bash preparation also applies
the Shell module. Delivery includes reviewed source and
deployment only into the explicitly selected disposable qualification worker.
It does not modify existing managed guests, host container ownership, native
agent launch paths, credentials, ongoing cycles or source checkout locations.

Source deliverables are reviewed runtime and image recipes, a bounded fixture
runner, and an operator runbook with recovery and retained-evidence instructions.
This slice introduces no production installer, public command contract, host
Git bridge, alternate worktree allocator or lifecycle engine.

## Runtime and ownership contract

| Resource | Owner and permitted role | Workload access |
|---|---|---|
| Mac qualification selection | Operator selects the disposable worker and fixture scope | No ability to choose or expand host scope |
| Lima worker and host shares | Existing distribution ownership; minimal explicit sharing | Only admitted fixture source content |
| Podman user runtime | Dedicated qualification user; rootless operation | No runtime socket, administration or sibling containers |
| OpenShell gateway and supervisor | Trusted qualification controller outside workload | No administrative credentials, configuration or policy writes |
| Workload image and policy | Reviewed immutable generation selected before execution | Read-only policy/configuration and bounded scratch space |
| Linked fixture checkout | Worktrunk creates native fixture membership; host controller verifies identity | Selected source files writable; Git pointer protected |
| Shared fixture Git metadata | Native Git and host controller | Only explicitly necessary reads; no writes or lifecycle evidence access |
| Evidence and retained work | Existing private qualification/evidence facilities | No ability to mark its own result verified or remove retained evidence |

**Text Equivalent:** The operator selects a disposable scope. Distribution owns
the worker, Podman and OpenShell configuration. Worktrunk and Git retain checkout
ownership. The untrusted workload can edit selected source files and use bounded
scratch space, but cannot administer the runtime, mutate shared Git metadata or
authorize its own qualification result. Canonical source: this contract. Owner:
distribution maintainers. Change trigger: ownership or mount-scope change.

No parent shell environment is copied wholesale. In particular, the workload
receives no host home, native agent state, reusable provider credential,
1Password token, SSH agent, container socket or gateway administration channel.
The fixture image needs no provider credentials and makes no model requests.
Build dependencies and image retrieval belong to the trusted preparation step;
they do not grant the running workload equivalent network access.

Resolve and verify immutable artifact identities before execution: OpenShell
gateway, supervisor, workload runtime, image manifests and selected architecture,
plus the qualified Podman and Lima generation. Record the reviewed versions,
digests and verification method privately. A version string alone is insufficient;
moving tags, missing integrity evidence and mixed incompatible components refuse
execution. Existing package ownership remains unchanged.

Bind mounts require explicit trusted gateway configuration. If the selected
OpenShell driver requires enabling bind mounts or disabling external-resource
admission, limit that choice to this isolated gateway and its controller-selected
fixture resources. Qualify that the workload cannot submit resource selections,
change policy or reach administrative APIs. Do not apply permissive settings to
another gateway, expose its control socket, or fall back to broad host sharing.
An inability to establish the restricted boundary blocks qualification.

Defaults are disabled management, disabled vendor telemetry at the gateway,
fixed operator-owned policy, and no automatic access approval. Runtime egress is
denied except for the exact synthetic destination needed by an individual probe.
Policy-denied work remains denied; discovery of an omitted endpoint is not an
authorization to add it.

## Qualification interface and observations

The runner consumes a private, reviewed selection of fixture identity, immutable
runtime/image generation, policy generation and requested probe set. It resolves
native Worktrunk/Git membership itself rather than trusting a workload-supplied
path or environment variable. No public CLI or portable machine-state schema is
established here; later adapters must reuse qualified native interfaces.

Each probe returns `passed`, `failed` or `unavailable`, with a stable reason,
observed component generation, and a reference to private bounded evidence.
Unperformed checks cannot be reported as passed. Public completion evidence
contains only sanitized outcomes and versions; omit machine paths, endpoints,
account identifiers, tokens, native session bodies and raw tool output.
Private evidence follows existing owner-only storage and retention authority.

| Ordered step | Required observation | Refusal or recovery |
|---|---|---|
| Prepare | Explicit disposable scope, verified artifacts, registered linked fixture, reviewed policy | Preserve existing systems; report missing capability |
| Admit | Rootless runtime and actual kernel isolation pass; exact mounts and protected Git pointer verified | Do not start fixture workload |
| Exercise | Direct-edit, denial, network and control-plane probes run within bounded time | Stop new work and retain failed fixture/evidence |
| Pause | Every workload process stops progressing while gateway remains responsive | Report unavailable if whole-workload suspension cannot be proved |
| Resume | Same workload generation and session marker continue with retained work | Never substitute a new process or session and call it resume |
| Restart/recover | Restart outcomes distinguish durable source edits from lost volatile state | Retain ambiguity; never silently recreate, delete or overwrite work |
| Finish | Complete probe matrix and preservation inventory are available | Retirement remains a separate explicit operation |

**Text Equivalent:** Verify preparation and admission before running probes.
Suspend the complete workload without stopping its gateway, then resume the
same generation. Restart is a distinct recovery operation and cannot be counted
as session-preserving resume. Failed or uncertain outcomes retain work and
evidence. Canonical source: this ordered qualification contract. Owner:
distribution maintainers. Change trigger: operation ordering or recovery change.

Whole-workload suspension includes children and background descendants, not
merely the foreground terminal. During the pause, synthetic progress counters,
file writes and outbound attempts stop; the gateway remains available to the
trusted controller. Resume must preserve the workload's process/session identity
and already written files. A credential-free fixture proves the mechanism only.
Both later agent slices must repeat it against their native session behavior
before claiming authenticated session preservation.

## Initial experiment ceilings

The initial reviewed worker budget is four virtual CPUs, eight GiB of RAM and a
40 GiB virtual disk. Admit at most one qualification workload at a time, capped
at two CPUs, two GiB memory and 256 processes through actual runtime controls.
Unenforceable required runtime limits produce unavailable, not a best-effort pass.
Private selection may reduce budgets; raising them requires a revised reviewed
qualification input and invalidates the prior resource identity.

Trusted preparation has a 30-minute deadline; the probe phase has a 15-minute
overall deadline and 60 seconds per probe. Recovery observation is bounded to
60 seconds. Timeouts retain failed evidence and the fixture rather than deleting
state or repeatedly restarting processes. No unbounded automatic retry.

Fixture admission is limited to 64 MiB and 4096 entries. Synthetic probe writes
have a declared bounded output set; scratch uses a 256 MiB size-limited temporary
filesystem. Retain at most 10 MiB of diagnostic output per run with explicit
truncation metadata and a 100 MiB aggregate private log budget. Reaching a log cap
stops new probes; never erase failed evidence to continue. Work retention follows
separate preservation rules and is not included in automatic log pruning.

These resource limits do not establish a byte quota on a live host bind mount.
Real-checkout activation must inspect available storage, bound its selected task
and monitor growth; it must report any unprovided hard filesystem quota honestly.
Authorized writes to the selected checkout remain capable of consuming that
volume's space. No claim of general host availability protection follows from
filesystem access isolation.

## Required behaviors

1. **Enforcement admission.** Given the selected worker, when qualification
   probes Landlock, seccomp, user namespaces and rootless Podman operation, then
   each required mechanism must work in the actual nested topology. Missing
   capability refuses workload admission without unconfined seccomp, privileged
   containers, added host capabilities or another runtime fallback.
2. **Direct editing.** Given a registered linked fixture checkout, when the
   workload changes selected text and binary files, creates and deletes allowed
   files, or changes executable modes, then native host observations see exactly
   those intended changes. Symlink leaves are classified explicitly; following
   them outside the admitted tree must fail. Do not rewrite fixture paths or
   claim that copied files prove direct-edit compatibility.
3. **Git identity protection.** Given writable source content, when a workload
   attempts to overwrite, unlink, rename or replace its Git pointer, then the
   operation fails and native registered identity remains unchanged. Shared Git
   configuration, objects, refs, hooks, sibling indexes and lifecycle state
   cannot be modified. Read-only child rules are not assumed to override a
   writable parent; prove the effective mount and kernel behavior.
4. **Alias resistance.** Given symlinks, hardlinks, alternate path spellings,
   case collisions or replaced parent entries in synthetic fixtures, when any
   alias could reach protected data, then admission or access fails without
   changing the protected object. Where an alias cannot be excluded or safely
   represented on the host filesystem, mark that layout unsupported.
5. **Egress enforcement.** Given a denied synthetic destination, when a process
   ignores or removes proxy environment variables and attempts direct access,
   then the request remains denied. The exact allowed fixture destination works
   only within its configured rule. A proxy error alone does not prove denial
   of an alternative direct route.
6. **Control-plane protection.** Given a running workload, when it attempts to
   change policy, attach resources, grant credentials, approve access or reach
   Podman/gateway administration, then access fails. Its environment and mounted
   files contain no control-plane credential or inherited reusable secret.
7. **Pause and resume.** Given a progressing workload with child processes,
   when the trusted controller pauses and resumes it while the gateway stays
   alive, then all workload activity stops and the same generation continues.
   A partial freeze, timeout or replacement process is failed or unavailable,
   not successful resume.
8. **Failure preservation.** Given a failed probe, gateway interruption, worker
   restart, storage unavailability or uncertain shutdown flush, when recovery is
   attempted, then known source edits and evidence remain retained. Report actual
   durability and native state separately. No automatic reset, cleanup, credential
   substitution, unsandboxed retry or return to an unrelated checkout occurs.

These are security-boundary probes, not an assertion that an arbitrary guest
kernel compromise is contained. Native Mac MicroVM replacement remains deferred;
its direct-sharing limitations require a separate decision and qualification.

## Validation and Gate Ledger

### Qualification implementation surfaces

The internal qualification assets live under `tests/fixtures/openshell_runtime/`;
they are excluded from chezmoi installation. `versions.json` records reviewed
release checksums and immutable ARM64 image identities. `lima.yaml`,
`gateway.toml`, `policy.yaml` and `Containerfile` declare the isolated topology.
Private preparation substitutes only exact owned fixture paths and the native
guest user/socket identity. It never imports an existing gateway, home, provider
store or VM. Missing substitutions or unverified image identities refuse use.

`tests/probe_openshell_runtime.py` is an internal observation runner, not an
installed launcher or alternate lifecycle owner. Its input is a bounded private
selection with schema version 1, an exact owned synthetic linked checkout and
an exact prepared worker. It resolves native Git/Worktrunk identity independently.
The closed operation set contains inspection, fixed boundary probes and selected
native pause/resume observations; no caller-supplied shell, program, environment,
policy body or arbitrary operation is accepted. Preparation remains separate
from workload execution and requires the reviewed native recipe.

The first implementation accepts only `schema_version` (integer 1), `run_root`
(an absolute canonical owner-only directory whose basename is `openshell-q-`
followed by twelve lowercase hexadecimal characters), and `lima_sha256` (the
reviewed native Lima executable's SHA256). The input is at most 64 KiB. The worker
name is the run-root basename; the Lima home, fixture main repository, linked
task checkout and evidence directory are fixed children of that root. A private
owner marker is created during exclusive preparation; no existing root is
implicitly adopted. The runner's only initial executable operation is the fixed
pointer-boundary probe. Later matrix operations require their own implemented
and reviewed controls; they remain unperformed until then.

Its pure `parse_selection(bytes) -> Selection` rejects malformed input without
effects. `validate_root(Selection)` checks preparation ownership and identity.
The internal `run_command` owns bounded child streams and process groups;
`pointer_probe(Selection)` executes fixed trusted fixture code and independently
checks host pointer and metadata observations after each attempt. Neither
selection nor workload output can supply a host command or a trusted verdict.

Inputs reject unknown/duplicate fields, noncanonical paths, aliases to another
root, unsupported versions, invalid component hashes and budgets above this
feature's ceilings before effects. Host binaries and prepared resources are
bound to recorded identities. Commands use fixed argument arrays and minimal
environments; local process cancellation is never reported as proof of remote
workload termination.

The first live boundary probe attempts overwrite, append, unlink, rename and
replacement of the Git pointer, including case variants on case-insensitive
host filesystems. It uses only a disposable synthetic native Worktrunk checkout.
A read-only bind at the exact `.git` spelling is a candidate control, not a proven
barrier to aliases. Host observations compare pointer bytes, inode, registered
membership and protected metadata with their pre-probe identities. A successful
protected mutation stops the experiment immediately and retains the corrupted
synthetic fixture; it is not repaired and relabeled as passing.

Each probe produces an allowlisted identifier and `passed`, `failed` or
`unavailable`, plus bounded private observations. Unperformed rows remain
`not_run` in the aggregate report. A successful early probe cannot mark the
whole runtime qualified. Overall qualification requires every required row in
the [runbook matrix](openshell-runtime-runbook.md) to pass against the same
reviewed component and policy generation. Failure at early admission blocks
later probes and reopens only the affected technical decision.

OpenShell v0.1.6's Podman driver does not implement its suspend RPC. The selected
candidate suspension mechanism is native Podman pause/unpause of the exact full
workload container ID. The controller must independently observe the paused
container, stable descendant counters and writes, responsive gateway, and
same-generation progress after unpause. The gateway's phase label alone is not
freeze evidence. No privileged container or relaxed seccomp fallback is allowed.

Use the existing rendered-configuration, shell, checksum, affected pytest and
publication/instruction authorities from the Engineering Profile. Runtime claims
require bounded probes on the selected Mac and disposable guest. Unit fixtures
and policy inspection alone cannot qualify kernel enforcement or mounted-file
behavior. Record absent tools or unavailable checks without installing a substitute
outside the reviewed preparation scope.

| Gate | Applicability | Initial result | Rationale or required evidence |
|---|---|---|---|
| Domain | required | not_run | Ownership, fixture identities and admission states |
| Behavior | required | not_run | Positive and negative behaviors above |
| Spec | required | not_run | Bounded runner/recipe interfaces and outcome contract |
| Contract | required | not_run | Artifact integrity, boundary and result validation |
| Test Driven Implementation | required | not_run | Red-first meaningful runner and boundary fixtures |
| Refactor | required | not_run | No duplicate lifecycle or allocator; retained compatibility |
| Review/Integrate | required | not_run | Independent review, publication checks and affected regressions |
| Release | not_applicable | not_run | No independently versioned package or release artifact is published |
| Deploy | required | not_run | Exact disposable-worker preparation and configuration verification |
| Operate | required | not_run | Actual denial, pause/resume, interruption and durability probes |
| Maintain/Retire | required | not_run | Update ownership, retained-state inventory and explicit retirement runbook |

No Gate Exceptions are approved. Source delivery does not prove operation, and a
successful disposable deployment does not authorize real-repository enrollment.
Readiness of the next slice requires the current qualification result and a fresh
Initiative receipt; failed feasibility reopens the affected design decision.

## Visual Evidence

| Concern | Decision | Review question |
|---|---|---|
| Boundary | required: ownership table and Text Equivalent | Which actor may control each resource? |
| Interaction | required: ordered qualification table and Text Equivalent | What must be verified before execution and recovery? |
| State | required: ordered qualification table and Text Equivalent | Which observations distinguish pause, resume and restart? |
| Data/trust | required: ownership table and Text Equivalent | Can workloads obtain host authority or alter evidence? |
| Schema | not_applicable: no new persistent public schema is introduced | Private fixture inputs reuse existing evidence authority |
| Dependency/deployment | required: ownership table and ordered qualification table | Where do Mac, guest, runtime and workload controls apply? |
| Quantitative | not_applicable: no performance, capacity or savings claim is made | Probe bounds and pass/fail observations are not forecasts |

The tables are the editable canonical visuals. Their adjacent Text Equivalents
preserve every decision-relevant boundary and ordering without rendering.
