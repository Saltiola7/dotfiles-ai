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
| Immutable pointer and original-flags receipt | Trusted host controller; exact synthetic file identity | No receipt access or host flag-restoration interface |
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

The reviewed worker budget is four virtual CPUs, eight GiB of RAM and a
20 GiB virtual disk. Admit at most one qualification workload at a time, capped
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

### Aggregate storage admission before further experiments

Retaining stopped workers and their separate download/conversion caches caused
host storage pressure. The operator authorized their retirement and requires disk
and cache limits before any further VM starts. Historical evidence and compact
fixtures remain retained; retired resources cannot be resumed or represented as
current native evidence. This changes preparation admission, not socket exclusion
or the default-off agent route.

| Resource | Ceiling or required margin | Enforcement owner |
|---|---|---|
| Retained trial VM | One total, including stopped or partially created instances | Exclusive trusted preparation admission; a second instance refuses |
| Worker virtual disk | 20 GiB | Exact native Lima configuration and disk identity |
| Aggregate disposable runtime storage | One disk image with at most 24 GiB usable capacity | Native image capacity; all VM disks, container layers, controller state and temporary files stay inside it |
| Download and conversion cache | 2 GiB allocated data | Dedicated native APFS volume quota inside the image; no unbounded fallback cache |
| Image-format overhead allowance | At most 1 GiB additional parent allocation | Admission allowance; unsupported or unbounded image format refuses |
| Host application reserve | At least 20 GiB after worst-case remaining image growth and bounded external retention | Fresh parent-filesystem free-space observation before allocation/start and during operation |
| External compact retention | At most 1 GiB total fixtures, inputs, receipts and diagnostics; diagnostics also retain their existing 100 MiB ceiling | Bounded inventory; no automatic evidence deletion |

**Text Equivalent:** One disposable image bounds the runtime and contains the
separately quota-limited cache. Stopped VMs count against the single-instance
limit. The parent filesystem retains a 20 GiB application margin after accounting
for remaining possible growth, image overhead and external retention. Native
image/quota proof is mandatory; byte counting alone is not that proof. Canonical
source: this storage contract. Owner: distribution maintainers. Change trigger:
capacity, storage topology, accounting or admission changes.

On macOS, Lima uses `HOME/Library/Caches/lima`; changing `XDG_CACHE_HOME` alone
does not contain it. The original download and converted raw image both count.
See [Lima's storage layout](https://lima-vm.io/docs/dev/internals/).
The cache quota must cover that actual path, independently verified through
native volume identity. A quota failure retains work and refuses preparation;
it never retries in the ordinary home, system temporary directory or another
volume. The existing physical SSD container is not repartitioned or given a new
shared volume by this contract. The bounded image is a directory-local candidate
whose native format, quota and Lima compatibility still require qualification.

`inspect_storage(root) -> StorageInventory` is read-only. It reports allocated
bytes separately from logical file lengths, counts all retained runs and caches,
and refuses unsafe ownership, unsupported accounting or inventory bounds. Tiny
synthetic fixture aliases are inventoried without following them; aliases cannot
redirect storage authority. `admit_storage(inventory) -> StorageAdmission`
requires the remaining full budget, not merely the previous 12 GiB threshold.
A fresh empty store needs 46 GiB available: 24 GiB image, 1 GiB overhead,
1 GiB external retention and 20 GiB reserve. No reserve credit is inferred from
sparse length, APFS clone sharing or a caller-written receipt.

The first source increment supplies inspection and a fail-closed gate before
the runner can invoke Lima. Until an independent native image/quota verifier is
implemented and qualified, creation, start and other potentially allocating
Lima operations remain refused even when capacity is sufficient. Read-only native
inventory and exact stop/delete remain available for recovery. A JSON field
claiming a quota is not admission authority. Existing private preparation scripts
are superseded; their calls through the runner are refused. This guard governs
trusted pilot preparation and is not a security boundary against an operator
who invokes host tools independently.

Required behaviors include refusal before downloader or native VM execution on
low reserve, a second retained VM, cache overflow, external-retention overflow,
ambiguous ownership or missing native quota proof. Inspecting a missing store
must not create it. An exclusive operation lock must span fresh admission and any
future allocating operation. Native quota exhaustion must be demonstrated with
a bounded disposable fixture before the actual VM topology is admitted; portable
tests cannot establish kernel enforcement. No live trial is authorized by a
passing source-only storage check.

The image/quota ceilings bound OpenShell allocation. The free-space margin is
an admission and monitoring rule, not reserved space against unrelated apps.
Low free space stops new work; preservation and exact native stop take priority.
Neither stopped workers nor caches are kept indefinitely to start successive
experiments. Their explicit disposition precedes replacement; compact failure
evidence remains available independently.

#### Native storage binding and operation admission

The next increment separates trusted native collection from pure validation.
`NativeStorageSelection` contains only the private pilot/run roots, selected
image path and file identity, expected container/volume UUIDs and exact mount
locations. These are comparison targets, not proof that a quota exists. It cannot
carry native commands, arbitrary environment values or an admission override.
`collect_native_storage(selection) -> NativeStorageObservation` invokes fixed,
bounded read-only native commands and observes the backing file and mounts itself.
`validate_native_storage(selection, observation, operation) -> StorageAdmission`
rejects missing, ambiguous, stale or contradictory observations. Neither function
accepts a stored success receipt as a substitute for current native evidence.

Mount the selected runtime APFS volume at `run/lima`, retaining the existing
short `LIMA_HOME/q` path. Set the dedicated controller home to
`run/lima/_controller`; place its temporary and XDG state inside that volume.
Mount the cache volume exactly at `HOME/Library/Caches/lima`. Lima 2.2.1 excludes
underscore-prefixed directories from instance discovery; see its
[instance inventory](https://github.com/lima-vm/lima/blob/v2.2.1/pkg/store/store.go#L47-L70).
Fixtures, inputs, receipts and evidence remain outside the disposable image.
This topology requires revised environment construction and native qualification;
the previous `run/controller` layout cannot be relabeled as bounded storage.

The native collector is initially inspection-only: a validated topology report
does not enable Lima allocation. Use fixed profiles for the 768 MiB mechanism
fixture with a 32 MiB cache quota and the 24 GiB pilot image with a 2 GiB quota.
The mechanism profile cannot admit a pilot worker. Selection parsing is closed,
rejects duplicate/unknown fields and aliases, and never executes caller-supplied
commands. Native calls use minimal environments, bounded output and deadlines.

The implemented inspection entrypoint is
`tests/probe_openshell_storage_native.py --selection PRIVATE_JSON`.
Its schema version 1 accepts exactly `profile`, `pilot_root`, `run_root`,
`image_path`, `image_device`, `image_inode`, `container_uuid`, `runtime_uuid`
and `cache_uuid`, in addition to `schema_version`. Image device and inode are
filesystem identity integers; native disk identifiers come from independent
collection. Mount locations derive from the fixed profile, never caller-selected
paths. Only `--operation inspect` is accepted. Exit zero means the observed
topology passed inspection; `allocation_enabled` remains false and
`inventory_qualification` remains `not_run`. This increment does not qualify
aggregate retained-VM counting, external retention or a running worker.

| Binding | Independent observation required |
|---|---|
| Image and attachment | Private single-link backing file identity; exact native `image-path`, `owner-uid`, writable state and `blockcount * blocksize`; one matching attachment and no shadow layer |
| Attached device and container | Normalize the native device spelling, including attach output without `/dev/`; bind `system-entities` device entries to the APFS container's sole `PhysicalStores` entry; reject foreign stores |
| Capacity and volumes | Selected image capacity no greater than 24 GiB; matching `APFSContainerUUID`, `APFSVolumeUUID` and `CapacityCeiling`; cache `CapacityQuota` exactly 2 GiB |
| Effective filesystem routing | Exact mountpoints and observed device/volume identities for `LIMA_HOME`, HOME, temporary/XDG state and the actual Lima cache; all required mounts present and writable |
| Host availability and ownership | Underlying host-volume free space, backing-image allocation, bounded external retention and every retained VM, including stopped or partially created instances |

**Text Equivalent:** The trusted collector binds an owned backing file through
its actual attachment and sole physical store to the selected APFS container,
runtime volume and quota-limited cache volume. Effective process paths must use
those mounted devices. The underlying host volume supplies the free-space
observation. A successful inspection reports verified topology while allocation
remains disabled; aggregate inventory and the separate operation guard must be
qualified before that state can change. Canonical source: this native-binding contract and the aggregate
ceilings above. Owner: distribution maintainers. Change trigger: native schema,
image format, mount layout, device identity, accounting or operation changes.

Native schema adapters must preserve the distinction between attachment device
names and device paths rather than assuming they have identical spelling. Read
cache quota from the independently observed APFS volume's `CapacityQuota`; absent,
zero, oversized or contradictory quota data refuses admission. Unknown native
formats and unavailable attachment or mount proof remain unavailable capability.
The inventory may cross only the two independently proved runtime/cache mounts;
all other mount crossings remain refused. Count backing allocation once rather
than adding the same bytes again through mounted contents. Keep the conservative
46 GiB fresh-admission requirement until remaining-growth accounting is qualified.

The future `qualified_allocation_guard(selection, operation)` owns the exclusive pilot lock from fresh
collection through the exact admitted operation and post-operation identity
checks. Operation descriptors are closed: `create` requires zero retained VMs;
`start` requires the one exact selected `q`; `workload_exec` requires that same
running worker and qualified generation. Each checks the 20 GiB virtual-disk
ceiling and applicable resource identity. Unknown operations, clone, resize and
arbitrary native arguments remain refused after quota support is implemented.
Read-only inventory and exact stop/delete retain their separate recovery route.
Keep the existing legacy `allocation_guard(root)` unconditionally refusing;
qualifying the new mounted layout cannot enable historical preparation scripts.

The next read-only implementation is
`collect_native_inventory(selection) -> NativeInventory`, with
`validate_native_inventory(selection, inventory) -> StorageAdmission` and
`tests/probe_openshell_storage_inventory.py --selection PRIVATE_JSON`.
Collection holds the exclusive private pilot-root lock while obtaining fresh
native topology observations before and after a bounded, descriptor-based scan.
Validation never loads a stored passing receipt. Its result may verify inventory
but always leaves allocation disabled and running-worker compatibility `not_run`.

`RetainedWorker` records run identifier, name, directory device/inode, presence
of configuration and observed disk file identities. Absence of configuration
does not erase a partially created worker. `NativeInventory` records those
workers, both native observations, external allocation, backing-image allocation,
runtime/cache use, maximum logical VM-disk size, scan/socket/fixture-alias counts
and underlying-host free space. Scan limits retain the existing entry/depth
bounds. Every owned qualification run requires its closed owner marker.
The exact `qualification/.DS_Store` Finder metadata file may be counted as
external retention when it is a regular single-link file owned by the current
user and no larger than 64 KiB. It is never interpreted as a run or parsed for
authority. A directory, alias, foreign owner or oversized file at that name
refuses inspection. Other unknown qualification entries remain refused.

Every immediate directory below a run's Lima home counts as a retained worker
except the exact `_controller`, `_config` and `_networks` directories. Unexpected
reserved names, `_disk`/`_disks`, additional backing images and unknown mounts
refuse inspection; an unmounted image cannot prove absence of retained workers.
Only the selected, independently verified runtime and cache mounts may be crossed.
Count backing-image allocation once and keep mounted usage separate, using native
APFS observations instead of double-counting the same physical bytes. Conservatively
count external fixture aliases under the existing narrow no-follow rules.

Inspect regular single-link `disk`, `image`, `basedisk` and `diffdisk` candidates,
including partial state, against the 20 GiB logical-size ceiling. This inventory
keeps `disk_format_qualification: not_run`: a filename and logical file size
cannot qualify raw format or QCOW2/ASIF virtual capacity. Allocation requires
independent format/capacity evidence. Unknown runtime aliases or sockets refuse;
native socket names/locations require separate source
and live qualification before metadata-only inspection is allowed. No socket is
opened or connected by storage inspection.

The allocating route must derive `XDG_CACHE_HOME` and `TMPDIR` as the private
`_xdg` and `_tmp` children of `HOME/Library/Caches/lima`, on the same cache-volume
device. The old home-level cache/tmp directories are not active routes. Lima's
download partials and converted cached images remain under its native cache;
conversion temporaries created beside VM-disk destinations remain under the
24 GiB runtime ceiling. See the pinned
[downloader](https://github.com/lima-vm/lima/blob/v2.2.1/pkg/downloader/downloader.go)
and [image conversion](https://github.com/lima-vm/lima/blob/v2.2.1/pkg/imgutil/nativeimgutil/nativeimgutil.go).
The earlier topology proof does not qualify these additional routes.
Require historical controller cache/tmp locations and the selected controller's
unused home-level cache/tmp directories to be empty. Counting such leftovers as
external or runtime storage does not establish the shared 2 GiB cache ceiling.
Unknown data is refused and retained, never automatically deleted by inspection.

The first allocating interface will be a closed, create-only operation:
`create_worker(selection) -> PreparedWorkerObservation`. It derives the exact
Linux/VZ/aarch64/raw/20 GiB recipe from reviewed source, forbids global default,
override or base templates and additional disks, and invokes only the pinned
Lima `create --tty=false --name=q` command for that exact input. The Linux create
path prepares disks without booting a VM; other guest operating systems are not
admitted. The pilot lock spans fresh complete inventory, creation and native
postchecks. Any partial worker remains counted after failure. Legacy allocating
scripts stay refused.

Before any later start, independently inspect the exact regular single-link
`lima/q/disk` and its unchanged identity on the runtime volume. Require native
Apple image format `RAW`, exactly 20 GiB virtual capacity, no encryption or backing
file, and matching raw file length and pinned QEMU image-info observations.
QEMU automatic probing alone is insufficient: the installed verifier reports an
ASIF file as raw, while native Apple inspection correctly identifies ASIF and its
virtual capacity. Tiny unused raw/ASIF/QCOW2 fixtures established this distinction
and were removed; they do not qualify a prepared VM disk.

Native Lima inventory must identify the exact stopped `q`, no errors or active
host-agent/driver PID, the reviewed effective configuration and unchanged source
and executable identities. The top-level Lima disk field is configuration data,
not independent capacity proof. Keep `start_worker` refused until that preparation
path qualifies: native start can create a missing worker and repeat disk resizing.
Never enable boot from a stored success report or missing-worker fallback.

The create-only native qualification subsequently prepared one stopped worker
under the full-size image and cache quota. Independent Apple and QEMU inspection
agreed on the raw 20 GiB disk. A second create refused with the retained worker
present, and the start interface remained refused. The private Cycle Record owns
the measured allocation and exact identities. This establishes stopped-worker
preparation, not VM boot, running inventory, OpenShell isolation or agent readiness.

The separate interface is a closed boot-and-stop qualification, not a
general session launcher. `qualify_boot(selection) -> BootObservation` must hold
the pilot lock across fresh stopped-worker admission, one native start, running
observations, exact stop and independently confirmed stopped state. Recollect
source, executable, effective configuration, raw-disk and native quota evidence;
never authorize from the earlier creation report. Require exactly the selected
existing worker and no autostart LaunchAgent. Keep `create_worker` and the legacy
allocation routes unchanged; neither acquires implicit boot or workload authority.

The fixed start is `start --tty=false --timeout 10m q`, with a 15-minute overall
qualification deadline and at least 90 seconds reserved for bounded shutdown
and verification. First boot may run only the existing reviewed system package
provisioning. No agent, OpenShell workload, provider, extra mount or real checkout
is admitted. Any start failure or timeout still requires explicit exact-worker
stop and independent status verification: Lima's host agent uses a separate
process group and can outlive its launch client. Do not detach or delete storage
when shutdown is uncertain. Equal VZ driver and host-agent PIDs are valid because
the VZ driver can run inside the host-agent process.

Running storage observations must preserve stable image, attachment, store,
volume, mount, worker, configuration and disk identities while taking conservative
usage maxima and host-free-space minima. Native capacity and quota ceilings stay
unchanged. File allocation, directory size, non-anchor runtime/cache file lengths
(such as logs) and native usage may change during boot. Image/disk lengths and
configuration bytes remain fixed; external retention stays independently bounded.
Such changes cannot erase accounting, admit replacement identities or hide
another worker. Preserve bounded no-follow traversal and all external-retention,
ownership, alias, cache-routing and single-worker checks. Unknown sockets remain
refused. The only source-derived VZ socket candidates for this exact no-mount
profile are `q/ha.sock`, `q/default_ep.sock`, `q/default_fd.sock` and `q/ssh.sock`;
qualify their exact owned locations through metadata without opening them.
Native Lima status may separately contact its trusted host-agent socket. This
does not relax workload access to OpenShell's internal sockets.

After stop, recheck the same worker, source, effective configuration, disk length
and native caps. Run Apple/QEMU format inspection only while independently
stopped, never force-share a live disk. Missing or contradictory observations
preserve failure and partial state. There is no automatic second start, recreation,
fallback, quota increase, forced detach or unbounded diagnostic output.

The native boot-and-stop qualification subsequently completed on the selected
capped worker. Fresh admission verified its existing raw disk and native quotas;
running observations bound the selected worker and owned host-agent process;
native stop completed and independent observations confirmed both stopped status
and process exit before disk-format reinspection. Compact private evidence owns
the identities, timings and measured usage. The worker remains stopped. This
qualifies the observed storage lifecycle only. It does not qualify guest build
cache limits, a patched OpenShell binary, workload isolation or either agent, and
it does not enable ordinary session launchers.

Required inventory scenarios include zero workers, empty partial workers,
stopped workers in another run, a second worker, hidden/additional-disk state,
missing cache mounts, cache children on another device, ambiguous image ownership,
external overflow, unknown sockets, traversal limits and lock release on failure.
Current strict native snapshot equality can safely refuse during active writes.
Before supporting a running worker, separate stable identity/ceiling comparisons
from conservative usage maxima and free-space minima; do not omit changing usage
from accounting or label this inspection increment running-state qualification.

Validation must cover replaced backing files or mounts, foreign physical stores,
duplicate attachments, shadow layers, invalid quotas, escaped controller paths,
missing cache mounts, low host reserve, a stopped VM followed by another create,
native observation timeout/malformed output and lock release after failure. A
missing cache mount must refuse before a write can reach its underlying directory.
The bounded tiny-image exercise must demonstrate native quota denial while the
runtime sentinel stays writable, then retire only its exact owned attachment.
That result does not qualify the real-size topology, Lima behavior or socket
exclusion. The current runner continues refusing allocations until the native
collector, real-size bindings and required compatibility evidence are qualified.

The small native mechanism exercise established a compatibility constraint:
the initial 256 MiB image refused a second APFS volume without changing its
single-volume inventory. Apple defines the maximum volume count from container
size divided by 512 MiB, rounded up; see the
[Apple File System Reference](https://developer.apple.com/support/downloads/Apple-File-System-Reference.pdf).
That image was detached and retired with failure evidence retained. A separately
identified 768 MiB image admitted two volumes. Its 32 MiB cache quota produced
`ENOSPC` after 30 MiB of writes while a runtime-volume write still succeeded.
After cache unmount, native identity checks refused a write to the underlying
directory and its sentinel remained unchanged. The fixture was detached and
retired; private evidence owns exact identities and observations. This qualifies
the tested quota mechanism only; it does not itself qualify the collector, real-size topology,
VM startup or OpenShell socket exclusion.

A separately identified 24 GiB image then established the full-size runtime and
2 GiB cache layout with the read-only collector. The cache mount command timed
out; independent fresh native observations subsequently confirmed the exact
intended attachment, volumes and mounts without retrying that mutation. The
timeout remains retained as unavailable command evidence. After cache unmount,
the collector refused inspection before any write to the underlying directory;
that directory remained unchanged. The runtime volume was unmounted, the exact
image detached and the disposable image removed with compact evidence retained.
No VM was created or started. This proves the observed storage layout and
missing-mount refusal, while allocation admission, Lima compatibility and the
runtime security matrix remain unqualified.

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
9. **Host pointer guard.** Given a fresh native linked fixture whose exact Git
   pointer has a recorded host-owned immutable flag, when the guest requests flag
   removal or metadata changes through an actual alias, then host observations
   must show unchanged flags, identity, contents and protected Git metadata.
   Writable source remains usable. Invalid guard receipts refuse execution;
   missing host flag observation is unavailable. Earlier failed fixtures remain
   unchanged and retained.

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
name is the fixed `q` inside that run's private Lima home, avoiding macOS Unix
socket path-length limits without sharing instance ownership. The workload name
is `q-` followed by the same twelve hexadecimal characters, within OpenShell's
nineteen-character limit. The Lima home, fixture main repository, linked
task checkout and evidence directory are fixed children of that root. A private
owner marker is created during exclusive preparation; no existing root is
implicitly adopted. The runner's only initial executable operation is the fixed
pointer-boundary probe. Later matrix operations require their own implemented
and reviewed controls; they remain unperformed until then.

The direct fixture mount uses `/work`, with its pointer mounted read-only at
`/work/.git`. OpenShell reserves the image's configured working directory against
replacement by a driver mount, so the image's empty `/sandbox/work` working
directory remains separate and receives no writable filesystem-policy grant.
`include_workdir: false` prevents an implicit grant to that directory. Fixed
probe programs address `/work` explicitly.

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

Runtime identity includes accepted policy admission, policy hash and version,
configuration and provider-environment revisions, and native process/container
identity. A hot policy change invalidates the observation even if the process
continues. Preparation errors do not count as denied target operations. Host
protected-state observations still run when execution fails or returns malformed
output; an observed protected mutation remains failed.

The first live boundary probe attempts overwrite, append, unlink, rename and
replacement of the Git pointer, including case variants on case-insensitive
host filesystems. It uses only a disposable synthetic native Worktrunk checkout.
A read-only bind at the exact `.git` spelling is a candidate control, not a proven
barrier to aliases. Host observations compare pointer bytes, inode, registered
membership and protected metadata with their pre-probe identities. A successful
protected mutation stops the experiment immediately and retains the corrupted
synthetic fixture; it is not repaired and relabeled as passing.

The exact-spelling read-only bind is not a qualified guard for case-insensitive
host shares: a case alias can reach the same writable host inode through the
parent mount. Runtime readiness is reopened for an alias-independent protection
mechanism. The selected next candidate is a host-owned immutable flag on a fresh synthetic
pointer, subject to proof that the guest cannot clear it. It is not an accepted
control or permission to change a real checkout. That candidate must bind host
file flags and inode identity, preserve original flags, exercise guest flag and
metadata operations, and define stopped restoration before later Git integration.
The failed fixture and its evidence remain retained independently.

#### Immutable-pointer experiment contract

`immutable_pointer_probe(Selection) -> dict` uses the same bounded controller and
native identity observations as the original pointer probe. The internal CLI
selects it with `--probe immutable-pointer`; `--probe pointer` remains the default
for the original candidate. The new report identifier is `immutable_git_pointer`.
Neither mode claims overall runtime qualification.

Before any native command or workload effect, the new mode validates the private
owner-only `guard.json` receipt. Its exact fields are integer `schema_version: 1`,
`device`, `inode`, `uid`, `link_count`, `size`, `mode`, `mtime_ns`,
`original_flags`, `protected_flags`, and lowercase hexadecimal `sha256`.
Booleans are not integers. Device is nonnegative, inode and modification time
are positive, UID is the current host owner, link count is one, size is between
one and 4096 bytes, and mode describes the exact regular file. This fresh-fixture
variant requires original flags zero and protected flags `UF_IMMUTABLE` only
(value two). Unknown fields, missing flags, aliases and identity mismatches refuse
admission. The receipt is written before changing the flag so original state
survives an interrupted preparation. Flag application uses the verified open
file descriptor before guest exposure; the observation runner never sets or
clears host flags.

The host snapshot binds device, inode, owner, link count, mode, size, modification
time, flags and content hash across a bounded descriptor read. It is compared
before and after every guest operation, including transport errors. The complete
protected Git metadata snapshot and native runtime/policy identity checks remain.

After the positive source edit, fixed guest operations attempt `setflags_clear`,
`fssetxattr_clear`, `xattr_set` and `chmod` through each actual case alias. For the
selected Linux aarch64 ABI, zero-filled SETFLAGS and FSSETXATTR requests use
request numbers `0x40086602` and `0x401c5820`, with eight- and twenty-eight-byte
buffers respectively. Zero-filled requests are limited to this zero-original-
flags synthetic fixture; they do not infer a GET result. The sole xattr is
`user.openshell_qualification` with bounded value `probe`; mode change requests
`0600`. Preparation failures do not establish target denial.

`EACCES`, `EPERM` and `EROFS` identify denial of the attempted operation.
`ENOTTY`, `EOPNOTSUPP` and `ENOSYS` identify an unsupported exact ioctl/xattr
interface, never a generic authorization denial. Invalid arguments or unknown
errors remain unavailable. A successful request whose host guard remains intact
is recorded as `succeeded_guard_intact`; observed protection changes always fail.
These classifications permit further bounded observation without claiming that
every possible flag-removal route was tested. The original pointer-mutation
matrix still requires denial, including writable-open attempts. A passed result
covers only this fixed candidate matrix; the remaining runtime controls retain
their independent evidence requirements.

| Guard state | Required observation | Permitted next action |
|---|---|---|
| Recorded | Exact fresh pointer, zero original flags, private receipt durable | Apply only the immutable flag through the verified descriptor |
| Protected | Host flags and complete identity match the receipt | Admit the exact bounded workload and observe fixed probes |
| Failed or uncertain | Changed protection, failed required observation or identity drift | Stop new attempts; retain fixture, flag and evidence |
| Stopped and retained | Exact workload and supervisor stopped; original identity revalidated | Restore recorded flags only under exact restoration authorization |

**Text Equivalent:** Record original identity before setting protection. Guest
exposure requires the protected identity to match. Failure preserves the flag and
fixture. Restoration requires confirmed stop, identity revalidation and explicit
authorization. Canonical source: immutable-pointer experiment contract. Owner:
distribution maintainers. Change trigger: guard admission or restoration changes.

#### Bounded containment observations

The next fixed operation is `containment_probe(Selection) -> dict`, selected by
`--probe containment`. It reuses the verified immutable pointer, native runtime
identity and protected Git observations. Its private `containment.json` contains
only integer `schema_version: 1` and lowercase SHA256 `marker_sha256`. Before any
native command, the controller validates the owner-only receipt and the private
`input/host-sentinel` file containing exactly
`openshell-nonfunctional-host-marker` followed by a newline. Preparation places
the nonfunctional environment marker `OPENSHELL_QUALIFICATION_SENTINEL` only in
the trusted create-command environment; it is never passed as workload `--env`.
Guest username, home and IDs come from native passwd identity, not the basename
of the home directory. Native rootless UID/GID mappings are checked before image
admission.

This operation shares the existing experiment window. The host-owned preparation
receipt's modification time starts the conservative fifteen-minute deadline;
expired or future-dated preparation refuses execution. Each native call or probe
remains bounded to sixty seconds. Starting another operation never resets the
experiment budget.

Fixed workload code creates `.openshell-containment` with exact UTF-8 text,
the byte sequence zero through 255, a temporary file, and a small executable-mode
file containing `#!/bin/sh` and `exit 0` lines. The executable is not run. The host
independently verifies bytes, ownership, single-link regular-file identity and
mode `0755`; it observes the temporary file before a separate deletion step and
then verifies absence. Pre-existing output refuses admission; source results and
diagnostics remain retained.

Exclusion checks cover the known host sentinel, the controller home, the selected
guest user's actual Podman socket, the fixed environment marker, and internal
`/.openshell/channel/control` and
`/.openshell/channel/sandbox/bootstrap.json` paths. The trusted guest controller
first verifies its marker file and actual socket. Workload probes attempt bounded
opens or directory enumeration without returning contents. Mere `stat` visibility
is not evidence of administrative access. Observed access fails; absent or denied
access is recorded for that exact surface. Other errors remain unavailable.
These selected observations do not replace the separate network and complete
control-plane qualification rows.

For resource observations, the exact native container PID selects its actual
cgroup-v2 and mount records. Kernel values must be finite and positive: CPU quota
at most twice its period, memory at most two GiB, process limit at most 256 with
current usage within that limit, and a writable `/scratch` tmpfs at most 256 MiB.
A small scratch write provides a positive control. Missing native reads remain
unavailable; configuration declarations cannot substitute for observed kernel
state. This step makes no pressure, OOM, fork-exhaustion or performance claim.

Host guard, protected metadata and native policy/process identity are checked
around every attempt, including errors. The report uses `probe: containment`,
separate fixed check results and observed resources, with overall
`runtime_qualification: not_run`. The implementation cannot promote unperformed
network, pause/resume or recovery checks.

#### Shared generation and retention admission

Every mode requires a private `generation.json` written by trusted preparation
after native workload readiness. Its exact keys are integer `schema_version: 1`
and `identity`. The identity object contains `sandbox_id`,
`main_process_instance_id`, `main_process_started_at_ms`, `container_id`, `pid`,
`container_started_at`, `policy_hash`, `policy_version`, `config_revision`,
`provider_env_revision`, and `current_policy_version`. The sandbox and container
identifiers must match `prepared.json`; the sandbox identifier is a canonical
UUID and the container and policy hashes are lowercase 64-character hexadecimal
strings. Process timestamps, PID and revisions are positive integers, excluding
booleans. Process-instance and container-start strings are nonempty, bounded to
256 characters and contain no control characters. Current policy version must
equal admitted policy version. Unknown or duplicate fields refuse admission.

Validate the receipt before native calls. Every ordinary runtime observation
must equal this recorded identity; a mode cannot establish a replacement
baseline. Reports retain the SHA256 of the canonical generation receipt, allowing
independent modes to prove that they observed the same prepared generation.
Missing receipts invalidate new observations; retained earlier experiments are
not rewritten. Pause and recovery require their own explicit observers and do
not weaken ordinary Ready/running identity requirements.

Diagnostic limits apply to the sum of retained evidence, not each report:
ten MiB in the selected run and one hundred MiB across owned `openshell-q-`
experiment directories in the private qualification parent. Inspect only
matching owned run directories, verify their owner markers and evidence
ownership, and reject unsafe entries or unavailable accounting. Check capacity
before effects and before each exclusive evidence write. Reserve 256 KiB for a
fixed pointer or containment invocation; each serialized report is at most
64 KiB. Earlier evidence is never removed to reclaim capacity. A transport output
limit records truncation explicitly; an inability to retain a final report is
reported to the caller and never becomes a pass.

| Private artifact | Trusted producer | Binding checked by observations |
|---|---|---|
| `owner.json` and selection | Host preparation | Exact private experiment root and selected host executable |
| `prepared.json` | Native workload admission | Exact sandbox and container IDs; original experiment deadline |
| `guard.json` | Host fixture preparation | Exact native Git-pointer inode, bytes and original/protected flags |
| `generation.json` | Native readiness observations | Prepared IDs plus process, container and accepted policy generation |
| `runtime-artifact.json` | Verified image inspection | Runtime executable bytes and independently built workload image |
| `worker-config.json` | Initial native worker configuration review | Original private worker configuration checksum for controlled restart |
| `network.json` | Native listener preparation | Exact address, listener process/start identity and reviewed source |
| `boundaries.json` | Native Git fixture inventory | Six existing protected metadata roles in the common Git directory |
| Private probe reports | Host observation runner | Canonical generation digest, independent observations and retained outcomes |

**Text Equivalent:** Host preparation selects resources and records native
identities. The generation receipt links prepared workload IDs with its actual
process and policy. Independent guard, artifact, listener and metadata receipts
bind their respective resources. Probe reports refer to the same canonical
generation digest; workload output cannot create or replace these identities.
Canonical source: the qualification interface and admission contracts. Owner:
distribution maintainers. Change trigger: receipt fields, producers or binding
relationships change.

#### Fixed network observation contract

`network_probe(Selection) -> dict`, selected by `--probe network`, operates only
on a fully prepared generation. Its private `network.json` binds integer schema
version one, the selected guest's canonical RFC1918 IPv4 `address`, positive
integer `listener_pid` and `listener_start_ticks`, and lowercase SHA256
`listener_source_sha256`. Ports are fixed at 18080 and 18081; no caller selects
another destination or executable. Preparation verifies the exact image's
`/usr/local/bin/python3.13` executable and starts one trusted, bounded listener
process from the reviewed fixture source. Its private records remain outside
workload mounts, under the native guest controller's
`openshell-qualification/network-records` home directory. Both ports bind only
the observed guest address, serve fixed
bytes, reject queries and upgrades, and expose no files or forwarding.

The initial policy permits only that exact address and `/32`, port 18080,
the observed Python executable, and enforced REST `GET /probe`. It remains fixed
through pointer, containment, network and pause observations. Port 18081 remains
denied. The static policy explicitly adds `/app`, `/var/log`, `/tmp` and
`/dev/null` as read-only, preventing the network baseline from adding implicit
writable paths. Only `/work` and `/scratch` remain writable. No caller supplies
an alternative policy body. Before effects, compare complete native full policy with the reviewed
policy, including provider and global contributions; a base-only policy view
cannot establish absence of additional access. Native policy hash, version and
configuration revision must match the shared generation receipt. An authored
file checksum is not a substitute for the native policy identity.

Native guest observations verify the address, listener owner, PID/start time,
source checksum, listening socket inodes, and bounded private record identity.
The trusted controller independently reaches both listeners before and after
workload attempts. The allowed request must return exact fixed bytes and produce
the corresponding trusted listener record. Denied method, denied path and denied
port attempts must produce no corresponding listener arrival. Test the denied
port through a proxy-aware client, with proxy variables removed and a proxy-free
client, and through a direct socket. A fixture's own rejection cannot count as
OpenShell enforcement. Ambiguous timeout or EOF remains unavailable.

Every attempt preserves host guard, protected Git metadata and the shared native
generation, including errors. A failed control stops later attempts and retains
all observations. A successful network report qualifies only its named checks;
it cannot pass unperformed administration, pause or recovery rows.

#### Whole-workload pause observation contract

`pause_resume_probe(Selection) -> dict`, selected by `--probe pause-resume`,
requires successful pointer, containment and network evidence with the same
canonical generation digest. It admits no new workload and changes no policy.
Its fixed fixture starts three bounded roles inside the existing workload: a
parent, its child, and a separate background descendant. Each records its role,
PID/start identity, a shared random session nonce and monotonically increasing
counter in `.openshell-pause`; each performs only fixed bounded source writes and
acknowledged requests to the already qualified allowed listener. The fixture
expires after at most 55 seconds and cannot accept arbitrary code or endpoints.

The host verifies all three roles progressing, then writes a fixed hold marker
and waits for every role to acknowledge that no request remains in flight.
Native guest observations independently bind the exact container, its cgroup,
member PID/start identities and current CPU usage. Pause uses native Podman
`pause` with the recorded full workload container ID only. After acknowledgement,
require native paused state and the cgroup freezer's `frozen 1` observation.
Release the fixture's hold marker only after that observation. Two observations
at least one second apart must show unchanged role counters, source bytes,
cgroup membership/PID identities and CPU usage, with no new listener arrivals.
The authenticated gateway must respond during the frozen interval.

Unpause only the same full container ID. Require the original ordinary runtime
generation, unchanged role PID/start/session identities, retained acknowledged
source bytes, and renewed counters and listener arrivals from every role.
A restarted or substituted process cannot pass resume. Use a dedicated frozen
observer; ordinary identity validation continues to reject paused or non-Ready
workloads. The whole observation is bounded to sixty seconds and the original
experiment deadline, including waits and native calls.

Any failed observation stops further qualification. If an error occurs while
paused, retain that state for the trusted exact-owner stop procedure; the probe
does not silently unpause or recreate the workload. Host guard and protected Git
metadata observations still run on errors. The report records separate pause,
gateway and resume outcomes, shared generation digest and retained evidence,
with overall runtime qualification still `not_run`.

#### Protected metadata and native control observations

`protected_boundaries_probe(Selection) -> dict`, selected by `--probe boundaries`,
uses the same generation, guard, deadline and evidence rules. Trusted preparation
adds one native Worktrunk sibling checkout and nonfunctional hook/lifecycle
sentinels to the synthetic repository. A private `boundaries.json` has exact keys
`schema_version: 1` and `metadata_targets`. That object maps the six fixed names
`config`, `object`, `ref`, `hook`, `sibling_index`, and `lifecycle` to canonical
relative paths inside the native common Git directory. Validate every selected
regular, single-link, owner-controlled file and its native role before effects.
Missing host targets do not count as protected. Workload write-open attempts
against their exact host paths must be denied or inaccessible, and the complete
host Git metadata snapshot must remain unchanged after each attempt. Any
successful writable open fails even if no bytes were written.

The selected source layout excludes symlinks and multiply linked files at
admission. Prepare separate, unmounted synthetic symlink and hardlink specimens
and exercise the same admission checker against them; preserve the specimens
after refusal. Case spellings that resolve to the Git pointer remain covered by
the immutable-pointer matrix; a distinct conflicting pointer entry is refused.
Attempt a valid rename of `/work` to an absent root-level sibling and replacement
of `/work` with a new empty scratch directory. Require a boundary-related denial
and unchanged host directory, pointer and native membership. Invalid-operation
errors do not establish protection. No specimen receives host credentials or
unrelated filesystem contents.

The trusted controller records native rootless Podman state, separate user
namespace mappings without host root, exactly one owned workload container,
nonprivileged capability-free execution and the selected immutable runtime
image. A private `runtime-artifact.json` has exact keys integer `schema_version: 1`,
lowercase 64-character hexadecimal `runtime_binary_sha256`, and
`workload_image_id` containing `sha256:` followed by 64 lowercase hexadecimal
characters. Trusted preparation obtains the binary checksum from the verified
runtime image filesystem and verifies the independently built workload image ID.
Native observations compare the running runtime executable and workload image
with this receipt, and compare the runtime image manifest/config with the pinned
version manifest. Manifest and binary hashes are different identities.

Kernel qualification uses an explicitly identified startup attestation: the
pinned runtime calls active kernel qualification before opening its boundary;
the backend validates its native Linux audit before allowing workload launch.
An exact verified runtime, accepted native generation and successful bounded
workload execution therefore provide source-backed evidence of that mandatory
startup path. This is an inference from verified runtime and execution evidence,
not an exported measurement of every audit field. Record that distinction and
leave unexported per-field values unobserved. Do not repeat `capability-probe`
inside a running boundary: its DNS-port probe can conflict with the active
service. Ordinary workload filesystem, network, capability and namespace
observations retain their separate requirements.

Discover the actual gateway listener and the selected channel socket from native
container/volume inventory. Confirm their existence and controller access before
workload connection attempts; guessed paths cannot qualify a missing surface.
Workload transport to gateway administration, the Podman socket and the actual
internal control socket must remain inaccessible. The exact `policy.local`
routes `/v1/policy/current` and `/v1/proposals` must return the source-verified
disabled-feature response, with policy, provider and resource identities unchanged.
Read attempts against available bootstrap or supervisor authentication state must
fail; absent state is recorded separately. No credential or state contents enter
diagnostics, and no real administrative mutation is submitted with credentials.

Record each boundary separately. Unavailable native inventories or unsupported
operations leave that check unavailable. The function cannot promote other
runtime matrix rows or infer physical-storage recovery from these observations.

#### Compatibility finding: internal Unix control transport

The pinned v0.1.6 Podman candidate does not satisfy the transport-exclusion
contract above. A credential-free workload connected to the independently
observed internal control socket after gateway and Podman connection-denial
checks passed. The source-bound probe stopped at that operation. Direct source
edits, the immutable Git pointer and protected Git metadata remained preserved
after the owned workload and worker stopped. Private lifecycle evidence retains
the exact generation and observations; this finding does not promote later
network, pause or recovery checks.

The distinction is material: a denied directory read does not prove that a Unix
socket beneath that directory is unreachable. Upstream mounts the control volume
into the workload/runtime container, creates its control directory with mode
`1777`, and binds the socket with mode `0666`. Unix socket creation and connection
remain kernel-driven in the pinned network broker. See the upstream
[control-volume layout](https://github.com/NVIDIA/OpenShell/blob/v0.1.6/crates/openshell-driver-podman/src/isolation.rs),
[listener](https://github.com/NVIDIA/OpenShell/blob/v0.1.6/crates/openshell-sandbox-backend/src/runtime_initiated.rs),
and [network broker](https://github.com/NVIDIA/OpenShell/blob/v0.1.6/crates/openshell-sandbox/src/network_broker.rs).

A successful connection establishes reachability, not an authentication bypass
or acquired administrative authority. The upstream listener authenticates its
protocol after accepting a connection. That protection is separate from the
approved socket-exclusion requirement associated with INT-008. No stock policy
setting has been qualified to make this internal socket unreachable while the
trusted runtime retains its required connection.

The operator selected strict socket exclusion and investigation of an additional
isolation boundary. Authentication after connection is not an accepted substitute
for transport exclusion. Gateway and Podman exclusion remain required. The
mechanism is still unqualified; this decision preserves INT-008 rather than
waiving it. Do not weaken the existing assertion, accept risk, admit providers or
real checkouts, or repeat the same unchanged topology as though another run would
establish the missing boundary.

This work supports an optional trial route. Successful runtime qualification does
not change normal Codex or OpenCode launches, enroll existing sessions or make
OpenShell the default. The separate explicit entrypoint and per-session selection
belong to the dependent [activation contract](openshell-pilot-activation.md).

#### Additional isolation investigation

The smallest source-change candidate is a workload-only extension of OpenShell's
existing child seccomp filter that denies creation of `AF_UNIX` sockets and socket
pairs. Trusted runtime processes retain their control transport. Upstream initial
launch and both native-exec paths install child hardening before the final filter;
the final filter prevents a later ordinary wrapper from installing its own filter.
See the pinned [child hardening](https://github.com/NVIDIA/OpenShell/blob/v0.1.6/crates/openshell-sandbox/src/linux/child_seccomp.rs),
[initial launch](https://github.com/NVIDIA/OpenShell/blob/v0.1.6/crates/openshell-sandbox/src/process.rs)
and [native exec](https://github.com/NVIDIA/OpenShell/blob/v0.1.6/crates/openshell-sandbox/src/boundary_exec.rs).
The operator selected this small workload-only patch for the next optional
credential-free trial, including compatibility testing. This is not a stock
setting or qualified image. Selection authorizes preparation of the experimental
patch; VM startup still requires completed storage admission, and agent or real
checkout activation remains in its dependent slice.

The source-only review proposes two conditional denials in
`child_seccomp::prepare`: use the existing `append_argument_equal_deny` helper
for `libc::SYS_socket` and `libc::SYS_socketpair`, with argument zero equal to
`libc::AF_UNIX`, returning `EPERM`. Update the module contract that currently
says mediated networking calls are left alone. Keep all existing hardening and
the descriptor close-on-exec sweep. The trusted runtime must not receive these
new workload rules. A resulting image needs its own source, patch, build and
artifact identities; it cannot claim to be an unchanged upstream release.

Keep the source-only patch under `tests/fixtures/openshell_runtime/patches/` with
an explanatory README and `source.json` binding the upstream repository, tag,
full commit, original file blob/SHA256 and patch SHA256. The first source delta
uses the existing v0.1.6 baseline for comparison; the build baseline must still
undergo the release review below. Tests must distinguish exact patch application
and source provenance from real Linux filter execution. Add isolated upstream
Rust syscall tests for Unix denial and unaffected Internet socket creation where
the existing test harness supports them. Host source checks cannot stand in for
the complete native launch/descriptor matrix. Missing toolchains remain explicit;
do not install a substitute or build outside the capped trial scope.

The November 3 upstream [v0.1.7 release](https://github.com/NVIDIA/OpenShell/releases/tag/v0.1.7)
does not remove this decision. Its
[child filter](https://github.com/NVIDIA/OpenShell/blob/v0.1.7/crates/openshell-sandbox/src/linux/child_seccomp.rs),
[network broker](https://github.com/NVIDIA/OpenShell/blob/v0.1.7/crates/openshell-sandbox/src/network_broker.rs)
and [control listener](https://github.com/NVIDIA/OpenShell/blob/v0.1.7/crates/openshell-sandbox-backend/src/runtime_initiated.rs)
retain the relevant behavior from v0.1.6. A version upgrade alone is therefore
not evidence of strict transport exclusion. The release also updates vulnerable
dependencies; select and review the actual build baseline before any new native
trial instead of silently changing the pinned qualification generation.

The reviewed actual-build candidate is v0.1.7 commit
`5d25211b25a8fc887e8d5c606d57d6ab22f1d76c`. Its child-filter preimage and patched
output are byte-identical to the v0.1.6 comparison, while launch environment and
logging changes still require the complete native regression matrix. Keep new
application listeners and agent trace relay disabled. Update experimental source
identity before building; never silently mix component generations. The smallest
candidate builds only `openshell-sandbox`, with the upstream Rust 1.95.0 toolchain,
locked dependencies and `aarch64-unknown-linux-musl`, retaining the default crypto
backend and matching v0.1.7 control components. This does not establish that a cold
build fits the existing disk, cache or preparation deadline. Qualify build routes
and measured capacity first; no larger quota, host build or alternate backend is
authorized by a failed build. See the pinned
[build workflow](https://github.com/NVIDIA/OpenShell/blob/5d25211b25a8fc887e8d5c606d57d6ab22f1d76c/.github/workflows/build-binaries.yml)
and [toolchain](https://github.com/NVIDIA/OpenShell/blob/5d25211b25a8fc887e8d5c606d57d6ab22f1d76c/rust-toolchain.toml).

Required proof covers every initial/native-exec route with and without a PTY,
descendants, descriptor inheritance and acquisition, restart and reconnect.
Descriptors above standard input/output/error must not survive exec; those three
must be verified pipes or PTYs rather than inherited Unix sockets. Test all Unix
socket types and creation flags, pathname and abstract destinations, `socketpair`,
descriptor passing and cross-process acquisition attempts. Independently prove
trusted controller access before and after denials. Preserve existing networking,
source-editing, subprocess, pause and recovery positive controls.

Broad Unix-socket denial may break legitimate client IPC. Both actual agents
must later pass their complete compatibility matrix; a synthetic result cannot
waive it. A more selective alternative is a mandatory child Landlock policy with
pathname Unix-socket mediation on a compatible kernel. The baseline policy uses
ABI3, so a kernel upgrade alone is insufficient. Child mount masking also needs
launch-lifecycle changes because the supervisor already forbids later mounts.
These alternatives remain research; the selected experiment uses the workload
patch, with no kernel upgrade or relaxed policy. Keep the experimental runtime
separate from normal session launchers. Storage admission remains a prerequisite
to every further VM experiment.

#### Bounded recovery observations

`recovery_probe(Selection) -> dict`, selected by `--probe recovery`, runs last,
after same-generation pointer, containment, protected-boundary, network and
pause/resume evidence passes. It uses fixed synthetic files and exact owned
services only. Every recovery case has a maximum sixty-second observation window
within the original experiment deadline. Stop on an unexpected outcome; retain
all earlier evidence and native state. Recovery never clears the pointer guard,
resets Git, replaces the workload or switches to another worker.

First create fixed text and binary checkpoint files under `.openshell-recovery`,
fsync them and independently verify exact host bytes and identities. Separately
create a bounded marker without an explicit fsync and label its durability
unacknowledged. Capture native service/container identities before interruption.
Stop only the private guest's `openshell-gateway` user service, confirm that it
is inactive, then explicitly start that same service and require authenticated
readiness plus the original workload generation. Observe source checkpoint
preservation independently of gateway recovery.

For storage-object unavailability, set only a dedicated newly created fixture
file's permission to zero through its verified host descriptor, observe that a
fixed workload open is denied, and restore only its recorded original mode.
Require successful access and unchanged contents after restoration. Keep this
case explicitly classified as synthetic object-permission denial; it proves
neither VirtioFS withdrawal nor physical-drive loss. Restoration is part of this
fixed recovery case and does not authorize changing any pointer flag or unrelated
file. If the observed object identity changes, retain it without restoration.

Finally stop and start only the selected private Lima worker, using its native
owner and original configuration. A private `worker-config.json` contains only
integer `schema_version: 1` and lowercase 64-character hexadecimal `sha256` for
the reviewed `lima/q/lima.yaml`, recorded after initial preparation and before
workload admission. Validate that binding before native recovery effects and
before/after restart; do not adopt the current file as a new baseline.
Record changed boot/process identities as a
restart, never a successful resume. Observe the fsynced checkpoints and retained
evidence before and after restart; record whether the unacknowledged marker is
present without claiming a durability guarantee. Do not recreate or start a
replacement agent workload after restart. A final deliberately refused source
operation may demonstrate terminal failure preservation, after which only
exact-owner stop and preservation inventory are permitted.

The report distinguishes controlled gateway interruption, synthetic storage
denial, worker restart, acknowledged source preservation and unacknowledged state.
It explicitly retains `physical_storage_loss: not_run` and
`abrupt_host_power_loss: not_run`. Scope reconciliation against approved Initiative
requirements INT-010, INT-026 and INT-028 selects bounded gateway interruption,
synthetic storage-object unavailability and worker restart with retained evidence
and separate acknowledged/unacknowledged state observations. Those requirements
do not specify physical disk removal or abrupt Mac power loss. Actual passing
observations can satisfy these selected recovery cases; they establish neither
physical-storage durability nor a power-loss guarantee. The unperformed physical
cases remain `not_run`, not accepted risk, and no broader guarantee is promoted.

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
| Interaction | required: ordered qualification table, read-only native inspection followed by separate operation admission, and Text Equivalents | What must be verified before execution and recovery? |
| State | required: ordered qualification and guard-state tables with Text Equivalents | Which observations distinguish admission, failure, restoration, pause, resume and restart? |
| Data/trust | required: ownership table and Text Equivalent | Can workloads obtain host authority or alter evidence? |
| Schema | required: private-artifact and native-storage binding tables with Text Equivalents | Which independently produced identities must match before results can be combined? |
| Dependency/deployment | required: ownership, native-storage binding and ordered qualification tables | Where do Mac, guest, runtime and workload controls apply? |
| Quantitative | not_applicable: no performance, capacity or savings claim is made | Probe bounds and pass/fail observations are not forecasts |

The tables are the editable canonical visuals. Their adjacent Text Equivalents
preserve every decision-relevant boundary and ordering without rendering.
