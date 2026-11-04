# OpenShell runtime qualification runbook

Status: operator procedure for the first credential-free runtime slice. It is
subordinate to the [runtime qualification contract](openshell-pilot.md) and the
[OpenShell pilot Initiative](../../../initiatives/openshell-pilot/README.md).
Owner: distribution maintainers. This document defines observations and recovery
boundaries; it does not report completed probes or passed gates.

The target is one explicitly selected disposable Fedora 44 aarch64 Lima worker
on Apple Silicon macOS and rootless Podman. The historical comparison used
OpenShell v0.1.6; the next experimental build candidate is the separately pinned
v0.1.7 workload-only patch described in the runtime contract. Only synthetic
fixtures are admitted. No provider sign-in, model
request, native agent session, host Git bridge or real-repository enrollment
belongs to this procedure. Existing guests and host package ownership remain
unchanged.

Concrete command sequences must come from the selected source-verified native
interfaces and the reviewed runner/recipes. This runbook does not invent a new
public CLI or substitute guessed flags for missing native capability.

The source-only storage report is `python3 tests/probe_openshell_storage.py
--root PATH`, where `PATH` is the existing private pilot store. It performs no
allocation, prints all admission blockers and exits nonzero while native hard
limits remain unqualified. A low-space refusal does not authorize deleting other
application data or selecting another volume. The operator retained the current
external storage selection and will free capacity before native qualification.

For a separately prepared image, use the read-only native topology inspector:
`python3 tests/probe_openshell_storage_native.py --selection PRIVATE_JSON`.
The private selection contains the fixed profile, roots, backing-file identity
and expected container/volume UUIDs described in the runtime contract. This
command does not mount, resize, create or start anything. Exit zero and
`topology_verified: true` qualify only the observed image/mount bindings;
`allocation_enabled: false` and `inventory_qualification: not_run` remain explicit.
Never substitute that report for aggregate inventory or VM admission.

The next read-only aggregate report is
`python3 tests/probe_openshell_storage_inventory.py --selection PRIVATE_JSON`.
It must account for every retained or partially created worker across owned runs,
the single selected backing image and bounded external retention. A successful
report still cannot create or start a worker. Before enabling allocation, qualify
the cache-volume `_xdg` and `_tmp` routes and closed operation-specific admission.

The closed create-only interface is
`python3 tests/probe_openshell_storage_create.py --selection PRIVATE_JSON`.
Its selection adds source-recipe, Lima and QEMU SHA256 comparison targets to the
native storage selection. It recollects native evidence under the exclusive pilot
lock, checks the fixed reviewed Linux recipe and binaries, and refuses any
retained worker before invoking create. A passing result means one stopped worker
has a verified raw 20 GiB disk inside the capped image. It cannot boot a VM.
Failed creation retains partial state and counts it against the one-worker limit;
do not retry or adopt that state automatically.

Boot qualification is a separate closed operation on that same existing worker.
It must freshly inspect the stopped disk and current resource bindings, perform
one bounded start, observe running storage and always request exact-worker stop
after an attempted start. It reserves shutdown time inside the overall deadline.
Cancellation of the start client does not prove shutdown of Lima's separately
running host agent. Preserve uncertain state without detaching its disk image.
Running inspection permits changing usage only with stable identities and caps;
unknown sockets, workers or mount changes still refuse. Only source-reviewed
Lima control-socket metadata belongs to this storage proof. OpenShell workload
socket denial and trusted control access require their later distinct matrix.

Read-only guest build inventory is another closed operation on that worker:
`python3 tests/probe_openshell_guest_inventory.py --selection PRIVATE_JSON`.
It repeats fresh storage/worker admission, starts the selected worker, runs one
fixed isolated Python inventory, and verifies exact shutdown. The shell transport
explicitly disables automatic worker start. Its 15-minute deadline includes the
same shutdown reserve as boot qualification; no caller command, package list,
environment or uploaded script is accepted.

The inventory reports Fedora/architecture identity, installed package versions,
tool availability and filesystem capacity for `/` and `/var/lib`. Each directory
is bound through its own open descriptor, mount ID and inode. Btrfs device numbers
can differ from mountinfo, so both are retained and mount IDs establish the
relationship. Missing or conflicting evidence refuses the operation. Guest
inspection failures do not skip shutdown or erase earlier diagnostics.

Inventory success keeps `build_enabled: false` and `session_enabled: false`.
The host's 2 GiB Lima cache quota does not cap guest package downloads, toolchain
files or Cargo output separately. Before installing compilers or building the
patched runtime, qualify the guest build/cache boundary and account for the exact
package transaction, toolchain extraction and retained output inside existing
20 GiB guest and 24 GiB host-image ceilings. Missing tools never authorize a host
build, another VM, larger disk or fallback to an older OpenShell generation.

The closed guest build runner is
`python3 tests/probe_openshell_guest_build.py --selection PRIVATE_JSON --operation OPERATION`.
Only these closed operations are accepted:

- `prepare` qualifies the root-owned 8 GiB build/cache filesystem and a separate
  64 MiB exhaustion fixture, including outside-write and guest-socket exclusion.
- `bind-storage` explicitly establishes a current host/Btrfs binding for the
  exact retained store, preserving the original receipt. It writes only the
  exclusive root-owned `binding.json` sidecar after the feature's independent
  identity checks; it does not mount the image, download or compile.
- `inventory` reports actual free space and metadata-only retained-directory
  usage inside the already qualified build filesystem. It starts no build service
  and deletes nothing; usage estimates do not authorize cleanup.
- `kernel` prepares the pinned compiler and dependencies, then compiles and tests
  the exact patched child-filter module offline. Downloads, extraction, Cargo
  cache and outputs share the 8 GiB filesystem.
- `kernel-resume` revalidates retained signed packages, compiler/library inputs and
  dependency sources before the reviewed test-only musl portability correction.
  It preserves prior source and outputs and uses one fixed fresh target directory;
  it performs no downloads or reinstallations.
- `full-prepare` revalidates retained Rust, authenticates the complete pinned
  v0.1.7 source and private C compiler, and proves static C compilation. It creates
  `full-source-2` directly with the four reviewed changed files and requires at
  least 4 GiB available inside the existing build filesystem.
- `full-source-reprepare` verifies retained Rust and the private compiler offline,
  then verifies the retained source archive/index and complete `full-source-1`
  before preparing `full-source-2`. It uses the existing 2 GiB build-admission
  threshold, preserves generation 1 and performs no downloads or compilation.
- `full-fetch` revalidates prepared inputs, then fetches locked dependencies into
  one fresh dedicated Cargo cache. It requires at least 3 GiB available and does
  not compile project code. Automatic Cargo cache cleanup is disabled.
- `full-test` revalidates inputs and cache, then builds and tests the selected
  complete runtime offline. It requires at least 2 GiB available. The resulting
  static ARM64 binary must carry the exact experimental version and pass the
  socket-denial sentinel. Runtime launch and agent compatibility remain separate.

The fixed `full-test/cargo-test` unit alone enables its internal
`library_tests` flag, allowing `AF_NETLINK` in the private offline network
namespace for upstream loopback tests. Its service mask stays `0077`; only the
complete library-test subprocess uses mask `0066`, producing traversable `0711`
temporary directories and private `0600` regular files. `WORK` and `WORK/tmp`
remain `0700`. Builds, version checks and the separate filtered sentinel keep
their inherited mask. These settings are internal stage selections, not CLI
overrides. Require the full suite to pass; do not skip tests, change source,
chmod retained paths or relax the workload Unix-socket exclusion.

Full-build operations retain previous toolchains, extraction trees and evidence.
They share the same 8 GiB hard filesystem cap and 30-minute lifecycle deadline;
insufficient space, partial preparation or timeout preserves a failed attempt.
No automatic cleanup, retry, new target, larger disk or alternative host is part
of this interface. Review private results before explicitly selecting the next
operation. Historical v0.1.6 controls must not run a v0.1.7 experimental runtime.

Select `full-source-reprepare` explicitly for the library-test musl `msghdr`
compile defect. Generation 2 adds only the feature's hash-pinned test correction
in `network_broker.rs`: zero initialization, the same public-field assignments
and a checked control-length conversion; the `EOPNOTSUPP` assertion and production
code remain unchanged. Reuse only authenticated `full-source-inputs-1` archive/index
bytes; changed or missing inputs refuse without a fetch fallback. Preserve a
partial generation 2 on failure; the explicit repair requires generation 2 to be
absent and refuses a repeat instead of adopting or overwriting it. Verify both
complete generations before reporting.
Keep the `.2` experimental version, child patch, root manifest/lock, Cargo cache
and target identities. Subsequent `full-fetch`/`full-test` use generation 2. Check
the source result's exact generation/path, `changed_files: 4` and
`network_test_sha256: 3a3112b39af2499bc30603f5655d7425b6b265a3a69af9234ccf24805645ea84`
before proceeding. The source repair alone proves neither test compilation nor
runtime compatibility; those remain separate results.

Each operation repeats host storage admission and independently verifies worker
shutdown. The build service has a 2 CPU quota, 6 GiB memory ceiling, zero swap and
512-task ceiling. Ordinary sessions never invoke this runner. A passing module
kernel test does not enable OpenShell or qualify its complete launch, descriptor,
PTY, broker or agent compatibility matrix. Keep run results in private evidence,
and keep optional activation disabled until those separate gates pass.

### Binding retained guest storage across boots

If a retained Btrfs image fails only the legacy `st_dev` comparison, preserve the
failure and original `receipt.json`. A dynamically assigned subvolume device
number can change across boots. That explanation alone does not prove the image
is unchanged and never authorizes editing the receipt or ignoring a mismatch.
The legacy record contains no historical outer filesystem/subvolume UUID.

After the binding contract and source checks pass, explicitly select
`--operation bind-storage` on the same guest build runner and private selection.
Fresh host admission computes the feature's canonical host-binding digest; the
operator supplies no digest, guest path or replacement identity. The guest must
observe no mount or loop attachment, verify the six unchanged non-device image
fields, and read the exact inner ext4 UUID through the same held image FD. Image,
receipt, root and parent FDs must agree on the observed Btrfs filesystem UUID,
tree ID and subvolume UUID, with strict current FD/path/mount checks.

Successful binding creates and syncs only the exclusive root-owned 0600
`binding.json`. Confirm the original receipt bytes remain unchanged and the
worker is independently stopped. The result must report `storage_bound`,
`unmounted_verified: true`, `session_enabled: false` and
`historical_outer_identity_verified: false`, together with the closed digest and
size fields specified by the feature. Retain identifiers privately. Any existing
sidecar, partial publication, unsupported identity or mismatch refuses; do not
delete, overwrite, repair or retry it automatically.

Before resuming a build, perform one separate subsequent
`--operation inventory` boot/inspect/stop lifecycle. It must recompute the
fresh host digest, validate the same sidecar and unchanged legacy receipt, and
prove current storage and shutdown. Record whether device numbers changed;
do not claim renumbering was exercised when they stayed equal. Sidecar presence
always requires its complete validation, with no fallback to legacy admission.
Without a sidecar, ordinary callers retain the original strict seven-field check.
These observations establish current binding and reuse only; all storage caps,
build prerequisites, strict socket exclusion and disabled-session boundaries
remain unchanged.

After capacity is available, the next native storage proof uses an owned tiny
image before any VM: verify its attachment and physical-store chain, establish
a separate cache quota, demonstrate bounded quota exhaustion while the runtime
sentinel remains writable, and prove a missing cache mount refuses rather than
writing beneath it. Retain compact evidence and retire that exact test image.
Then qualify the real-size image, actual cache routing and Lima compatibility.
Do not infer image attachment schema, mount permissions or enforcement from
portable fixtures. Admission must observe free space on the underlying host
volume and include the requested operation: creating another VM when one is
retained refuses, even if that existing VM is stopped.

Use a 768 MiB image for the two-volume mechanism fixture, with a 32 MiB cache
quota and at most 40 MiB of attempted writes. A 256 MiB APFS container permits
only one volume and cannot establish this proof. Retire an unsuccessful fixture
under its original identity before a revised experiment; never resize it or
discard failure evidence to manufacture a passing result.

Use native image attachment output and independent image/APFS inventories to
bind the backing file, whole image device, sole physical store and container.
The current native attach output spells devices without `/dev/`, while image
inventory includes that prefix. Bind volume UUIDs and exact mountpoints before
adding quota or writing. Cache unmount can make path-based native inspection fail;
that is refusal, not permission to use the underlying directory. An unmounted
volume reports an empty `MountPoint`; do not invent a `Mounted` field.

Require a real `ENOSPC` or quota error before the write ceiling, then successfully
write and sync a runtime sentinel. For the missing-mount check, verify native
cache identity before any write and retain an unchanged underlay sentinel. Exact
volume unmounts precede `hdiutil detach` of the verified whole image device;
the current `diskutil image` command has no detach subcommand. Confirm attachment
absence and unchanged backing-file identity before removing the disposable image.
Never force detach or select the physical SSD container by a guessed disk number.

Preserve a timed-out mount command as unavailable even if a later observation
finds the intended mount present. Inspect exact file, attachment, container and
volume identities independently before further action; do not blindly retry or
interpret cancellation of the command as proof that the native operation stopped.
Storage-only qualification retires its owned image after positive and
missing-mount checks. It creates no worker and cannot reuse an earlier report to
admit a later attachment or worker generation.

## Prerequisites and artifact admission

Initial read-only host inventory reported Lima 2.2.1 and Podman 6.1.4, with
OpenShell absent. Those observations establish only inventory. Host Podman's
version does not prove the guest's rootless runtime, and an installed OpenShell
binary would not prove kernel enforcement, compatible components or direct mounts.
Recheck exact selected identities during trusted preparation; retain observations
privately and do not infer readiness from the inventory above.

Before any worker or workload operation:

0. Run the read-only aggregate storage inspection. Require the runtime feature's
   disk/cache ceilings, parent reserve and independent native hard-limit proof
   before any allocating command. Missing proof blocks creation/start even when
   free space is ample. Historical private preparation scripts are superseded;
   their old 12 GiB check and per-run caches cannot admit another worker. Keep
   inspection, exact stop and authorized deletion available for recovery.
1. Confirm the registered runtime slice, approved disposable scope and exact
   source revision. Use the committed feature and complete imported specification
   closure; a later edited document cannot silently broaden the current launch.
2. Select the worker, private evidence location and synthetic repository in the
   trusted host controller. Verify ownership, absence of aliases and separation
   from existing workers, agent state and real repositories. An existing resource
   with an unknown owner or conflicting configuration is not adopted or repaired.
3. Resolve every executable and image required by the reviewed recipe. Record
   the selected OpenShell gateway, supervisor, workload runtime and image
   manifests, architecture, release identity and integrity-verification method.
   Verify downloaded or imported artifacts before executing them. Verify exact
   image content identities rather than relying on moving tags or display names.
4. Bind the selected Lima/Podman generation, Fedora image identity, reviewed
   policy and runner/fixture source to the private qualification record. Reject
   missing checksums or other required integrity evidence, incompatible component
   generations, unexpected architecture and artifacts whose identity changes
   between admission and execution.
5. Inspect the effective configuration before boot or workload admission. Disable
   vendor telemetry, automatic access approval, host SSH-agent forwarding, broad
   home sharing, implicit credential discovery and workload access to control
   sockets. Native container provisioning and preparation network access belong
   to the trusted preparation step, not the workload's runtime policy.
6. If native bind mounting requires a permissive gateway setting, constrain it
   to this isolated gateway and controller-selected fixture resources. Record the
   exact setting and prove that workloads cannot submit or expand resource
   selections. Missing proof blocks admission; do not change another gateway.

Complete source review, affected tests and the concrete native admission procedure
before creating the selected worker. Preparation time is reserved for native
resource and artifact checks; it is not extended while source defects are fixed.
A stopped preparation that admitted no workload retains its original result and
clock. A later reviewed experiment receives a new private identity and explicitly
selected resources, subject to the same ceilings and retained-evidence capacity.

Trusted preparation is bounded to 30 minutes. Missing capability produces an
unavailable result. A contradictory identity or ownership observation produces a
failed result. Neither permits a privileged container, unconfined seccomp,
additional host capability, another backend or automatic package-owner change.

## Exact disposable scope

| Selected resource | Required boundary | Refusal condition |
|---|---|---|
| Worker | One retained disposable Lima worker, running or stopped, with at most four virtual CPUs, eight GiB memory and 20 GiB virtual disk; exact configuration recorded | Unknown owner, conflicting generation, a second retained worker or an existing agent worker |
| Runtime storage and cache | At most 24 GiB bounded image, 2 GiB native cache quota, 1 GiB format-overhead allowance and 1 GiB external retention; retain 20 GiB parent free space after remaining growth | Missing native quota proof, cache outside the bounded volume, overflow or insufficient reserve; a fresh store requires 46 GiB available |
| Workload | At most one qualification workload; two CPUs, two GiB memory and 256 processes enforced by actual runtime controls | Missing or ineffective resource enforcement |
| Synthetic repository | Newly prepared synthetic content and native Worktrunk-created linked fixture membership | A real working repository, copied checkout used as direct-edit evidence, custom allocator or unverified membership |
| Workload-visible source | Only selected fixture source is writable; Git pointer and protected metadata remain protected | Broad parent/home mount, writable shared Git metadata or an alias that expands access |
| Scratch | Size-limited temporary filesystem capped at 256 MiB | Unbounded scratch or substitution of a host directory |
| Network | Only the exact synthetic destination required by the current probe is allowed | Broad internet access, automatic endpoint approval or inherited preparation permissions |
| Evidence | Private controller-owned output outside workload write authority | Workload can rewrite results, remove logs or assert its own trusted verdict |

**Text Equivalent:** The trusted controller selects one disposable worker and one
bounded workload. Worktrunk creates the synthetic linked checkout. The workload
may edit selected source and bounded scratch, but not shared Git metadata, host
state or evidence. Network allowance is limited to the current synthetic probe.
Canonical source: the runtime feature's ownership and ceiling contracts. Owner:
distribution maintainers. Change trigger: resource, mount, network or evidence
ownership changes.

Create fixture membership through the selected native Worktrunk interface and
verify it independently with native Git inventory. Record the primary repository,
linked checkout, common Git directory, per-worktree metadata and Git-pointer
identities privately. Do not replace Worktrunk with direct worktree allocation or
rewrite pointers to make an unsupported mount layout appear functional.

Admit no more than 64 MiB and 4096 fixture entries. Include synthetic protected
sentinels, sibling-checkout metadata and bounded text, binary and executable-mode
cases. Alias probes target only those synthetic sentinels, never actual secrets
or unrelated host files. Classify existing hardlinks, symlinks, case aliases and
parent replacements before allowing access; unsupported layouts remain unavailable.

## Credential-free environment

Construct explicit minimal environments for trusted preparation and the workload;
do not inherit the parent shell wholesale. Workload state is private to this
experiment and contains no normal host home, native agent state, provider grant,
ADC file, 1Password bearer token, SSH agent or gateway/Podman administration socket.
Do not use a managed guest shell route that automatically loads or forwards a
1Password service-account token.

Use nonfunctional synthetic markers to test environment and file exclusion. The
controller may compare whether a marker crossed the boundary, but ordinary output
contains only the result class. Do not print complete process environments or
mounted-file contents. A successful absence check must cover the actual workload
environment and mounts, not merely the intended input configuration.

Preparation may retrieve verified public artifacts through its reviewed route.
Running probes inherit only their selected synthetic network allowance. If a tool
tries credential discovery or interactive login, stop and record unavailable;
do not satisfy the prompt with an existing host account.

## Ordered operation and evidence

The probe phase has a 15-minute overall deadline and 60 seconds per probe.
Recovery observation has a separate maximum of 60 seconds. Preserve earlier
results when a later deadline expires. No unbounded retry, automatic recreation
or repeatedly restarted experiment is permitted.

| Step | Required observation before advancing | On failure or uncertainty |
|---|---|---|
| Prepare | Exact private scope, native fixture membership, reviewed artifacts and policy are admitted | Do not boot or execute an unverified candidate; retain the disposition |
| Admit | Rootless Podman, Landlock, seccomp, user namespaces, resource controls and exact mount protection work in the selected topology | Do not admit the fixture workload under relaxed controls |
| Exercise | Direct edits are observed from the host; protected writes, aliases, egress bypass and administrative access are denied | Stop new probes and retain modified synthetic fixtures and bounded diagnostics |
| Pause | Every workload descendant stops progressing while the gateway remains responsive | Report failed or unavailable; terminal silence is insufficient |
| Resume | The same workload generation and process/session markers continue with prior edits intact | A replacement process is restart, never successful resume |
| Recover | Gateway interruption, worker restart and selected storage-object unavailability have bounded, separately classified durability and state observations | Preserve ambiguous state; do not reset, delete or adopt a substitute resource |
| Finish | Every required probe has a truthful outcome and the controller has recorded preservation inventory | Leave incomplete checks unavailable; cleanup remains separately authorized |

**Text Equivalent:** Preparation and enforcement admission precede workload
execution. Boundary probes precede pause/resume. Resume must continue the same
generation; restart and failure recovery have separate evidence. Any failure stops
new probes and preserves work. Completion records results without implying cleanup.
Canonical source: the runtime feature's ordered qualification contract. Owner:
distribution maintainers. Change trigger: ordering, admission, recovery or
completion semantics change.

The controller must verify observations itself. Workload messages are untrusted
probe data, not evidence that a boundary held. Record a stable probe identifier,
`passed`, `failed` or `unavailable`, an allowlisted reason, the observed component
generation and a private evidence reference. Do not upgrade missing observations
to passed because a command exited successfully.

### Reviewed runner order

The opt-in runner accepts an explicit private selection document. For this
candidate, invoke `immutable-pointer`, `containment`, `boundaries`, `network`,
`pause-resume`, then `recovery` through its `--probe` option. The original `pointer`
mode remains available for inspecting the earlier candidate; it is not a substitute
for immutable-pointer qualification. Stop at the first failed or unavailable result.
All six candidate modes must bind the same admitted generation. Recovery runs last
because a worker restart ends the original process generation.

Each mode has an independent result and retained evidence. The runner never
promotes an individual pass to overall runtime qualification. Recovery covers the
selected controlled interruptions and synthetic permission denial; physical disk
loss and abrupt host power loss remain explicitly unperformed.

### Full probe outcome matrix

| Probe | Evidence required for passed | Failed or unavailable disposition |
|---|---|---|
| Artifact integrity | All selected component, image, source and policy identities match the reviewed generation before execution | Mismatch fails; absent verification evidence is unavailable |
| Kernel and rootless admission | Actual nested probes demonstrate Landlock, seccomp, user namespaces and rootless Podman without relaxed isolation | Ineffective enforcement fails; missing mechanisms are unavailable |
| Resource admission | Runtime observations confirm CPU, memory, process and scratch limits, plus one-workload admission | Limit bypass fails; unenforceable controls are unavailable |
| Direct file editing | Host observations see the intended text/binary changes, create/delete operations and executable modes in the native linked fixture | Wrong target or unintended changes fail; unsupported filesystem behavior is unavailable |
| Git pointer protection | Overwrite, unlink, rename and replacement attempts fail; native membership and pointer identity remain unchanged | Any successful protected mutation fails; missing host verification is unavailable |
| Shared metadata protection | Config, objects, refs, hooks, sibling indexes and lifecycle sentinels remain unchanged after attempted writes | Protected changes fail; inability to observe the selected protected set is unavailable |
| Alias resistance | Symlink, hardlink, alternate spelling, case-collision and parent-replacement cases are denied or refused at admission without changing protected sentinels | Reachable protected data fails; layouts that cannot be safely represented or excluded are unavailable |
| Allowed network case | The exact synthetic destination works only under its reviewed rule | Excess scope fails; an unreachable fixture that prevents a positive control is unavailable |
| Denied network case | Denied destination stays inaccessible through proxy-aware and direct attempts after proxy variables are removed or ignored | Successful direct or alternate-route access fails; a proxy error without direct-route evidence is unavailable |
| Control-plane exclusion | Workload cannot change policy, attach resources, grant credentials, approve access or reach gateway/Podman administration | Any acquired administration authority fails; an unexercised interface is unavailable |
| Environment and state exclusion | Synthetic markers and selected observations show no inherited reusable secrets, host state or control channels | Marker or protected-state exposure fails; inspection gaps are unavailable |
| Whole-workload pause | All child and background progress, writes and outbound attempts stop; gateway remains responsive | Any continued workload activity fails; incomplete descendant observation is unavailable |
| Same-generation resume | Original workload/process/session markers resume and prior source edits remain present | Replacement identity or lost acknowledged source changes fail; ambiguous identity is unavailable |
| Failure preservation | Each selected failed-probe, gateway-interruption, worker-restart, storage-unavailability and uncertain-flush case retains evidence and reports actual source durability separately from volatile state | Lost required retained work, fallback or automatic destructive recovery fails; unobserved durability remains unavailable |
| Evidence bounds | Controller-owned logs preserve earlier results, record truncation and stop new probes at their cap without workload modification | Overwrite, secret output, exceeded cap or continued probing after exhaustion fails; uncertain log ownership is unavailable |

**Text Equivalent:** Each row has an independent observed pass condition. An
observed boundary violation is failed; a missing capability or observation is
unavailable. Positive controls do not replace negative tests. Kernel enforcement,
direct edits, Git and alias protection, network and control-plane exclusion,
resources, pause/resume, recovery and private evidence all require actual
observations. Canonical source: required behaviors and observation contract in the
runtime feature, expanded into operator checks here. Owner: distribution
maintainers. Change trigger: probe coverage, interpretation or acceptance changes.

### Proving whole-workload pause

Before pausing, establish live progress from a foreground fixture and separate
child/background descendants. Retain their native workload and process/session
identities, synthetic progress counters, bounded source-write observations and
requests observed by the allowed synthetic network destination. The trusted
controller observes the gateway independently.

Use the selected source-verified whole-workload suspension mechanism. After
native pause acknowledgement, compare at least two bounded observations while
paused. Every descendant's counter and write observation must remain stable,
and no new outbound attempt may progress. The gateway must remain responsive
during that same interval. Stopping only the terminal, an SSH client or the
foreground process does not establish this result.

Resume the exact native workload. Confirm original generation and process/session
markers, retained source edits and renewed progress from all fixture roles.
Keep gateway responsiveness evidence separate. Timeout, partial freeze or a new
process is not resume. A worker or gateway restart belongs to the independent
recovery probe and must describe any loss of volatile state honestly.

## Failure handling and retained work

At the first boundary violation, identity drift, unexpected credential prompt,
deadline expiry or log exhaustion, stop admitting new probes. Use only the
qualified native control for the exact owned workload to stop further activity.
If containment or termination is uncertain, report that uncertainty, preserve
ownership records and do not admit another workload to the same experiment.
Do not signal unrelated processes or infer guest termination from a terminated
host controller process.

Retain source edits, fixture membership, the selected configuration and artifact
identities, bounded failed diagnostics and the last known native workload state.
Observe whether acknowledged source writes survived, and distinguish them from
unflushed writes or volatile process state. A recovery attempt is bounded and
never resets the repository, removes the fixture, rewrites membership or switches
to an unrelated worker. Preserve the original failed observation even if a later
controlled experiment succeeds.

Diagnostic retention is capped at 10 MiB per run and 100 MiB in aggregate, with
explicit truncation metadata. Reaching a cap stops new probes; do not erase failed
evidence to make space. Work preservation is separate from diagnostic retention
and is not subject to automatic log pruning. Keep evidence owner-only and outside
workload write authority. Public summaries contain sanitized outcomes and versions,
not paths, endpoints, accounts, tokens, raw output or native session bodies.

## Review, rerun and explicit cleanup

Review the complete matrix and preservation inventory before deciding the next
action. Source checks and policy inspection do not establish live runtime
success. Every required runtime observation must pass before downstream slices
can rely on this generation; failed feasibility reopens only its affected design
decision. The existing lifecycle owner records gates and the Initiative owns
promotion. This runbook creates neither a gate result nor a readiness receipt.

A rerun uses a new privately identified experiment and explicitly selected owned
resources. Retain earlier failures. Requalify changed binaries, images, policy,
mounts, resource budgets or control interfaces; do not relabel stale evidence.
No source update implies a live worker change or package upgrade.

### Continuation after the pointer case-alias failure

Continue the registered runtime cycle in its existing source checkout. Preserve
the failed experiment, original approval and all evidence. Reconcile only the
pointer-protection decision and its dependent contracts; the five-context scope,
direct-edit requirement and existing Git approval rules remain unchanged.

The next candidate uses a host-owned `UF_IMMUTABLE` flag on a fresh synthetic
Git pointer. This is a hypothesis, not a qualified boundary. macOS permits the
file owner to clear this flag; guest-to-host filesystem translation must therefore
be tested rather than assumed safe. The workload must never receive an interface
that asks the host controller to clear the flag.

Before another live experiment, define and validate these observations:

1. Record the fresh pointer's device, inode, owner, link count, original flags,
   contents and native Worktrunk/Git membership in private host-owned state.
   Reject pre-existing or ambiguous ownership. The previous failed fixture is
   not modified, reset or reused.
2. Apply only the user immutable flag to that exact synthetic file, without
   privileged or recursive changes. Verify the resulting host flags and identity
   before exposure. Keep the exact-name read-only mount as an additional control.
3. Verify direct source edits still work. From the actual OpenShell workload,
   attempt pointer writes, replacement, unlink, rename, hardlinks and case aliases,
   plus relevant flag, ioctl, xattr and metadata operations. Host observations
   must show that the immutable flag, inode, pointer contents and protected Git
   metadata remain unchanged after each attempt, including command failures.
   Unsupported guest interfaces must be recorded explicitly; they do not prove
   that all flag-removal routes are denied.
4. Stop on the first successful protected operation, cleared flag, changed
   identity, timeout or uncertain observation. Retain the new fixture and guard.
   A passing pointer experiment proceeds to the remaining required runtime
   checks under the same verified generation and resource ceilings.
5. Define restoration before execution: stop the exact workload and supervisor,
   revalidate the original device/inode and ownership, and restore only the
   recorded flags when that exact restoration is authorized. Never clear flags
   automatically after failure or as a recursive cleanup shortcut. Later host
   Git integration must separately qualify any move, repair or removal operation
   that requires changing the pointer.

The source runner requires explicit support for host flag observations and the
new bounded guest attempts before this candidate can run. Existing passing unit
checks and the failed live experiment remain separate evidence. If this candidate
cannot satisfy the original boundary, keep direct editing unavailable and reopen
the storage/design choice; do not weaken the requirement silently.

### Continuation after internal control-socket reachability

Read the runtime feature's versioned internal Unix control-transport finding.
Keep the current exclusion requirement and failed evidence intact. A denied
filesystem read is insufficient evidence for a denied Unix socket connection;
exercise the exact existing socket with a trusted positive control.

Stop the selected workload and worker after the first unexpected successful
connection. Verify retained source bytes, executable modes, Git-pointer guard,
shared metadata and private diagnostics. A raw connection does not establish
administrative authority or an authentication bypass; do not claim either.

Resume technical qualification only after the affected boundary design is
resolved and its contracts, negative cases and validation plan are reviewable.
The operator selected strict socket exclusion. An additional isolation mechanism
needs its own compatibility and lifecycle proof; authentication after connection
does not satisfy this selection. Preserve gateway and Podman exclusion, existing
Git approvals and the remaining pilot context map. Keep this synthetic procedure
separate from normal agent startup. A future trial requires an explicit session
selection through the dependent activation route; neither installation nor a
passing probe enables automatic routing.

Cleanup is a separate, exact operation. Before requesting or performing it:

1. Inventory retained fixtures, native checkout membership, workload and worker
   ownership, source edits, diagnostics and recovery uncertainty.
2. Confirm the exact owned workload is stopped and no controller or descendant
   still uses the selected resources. Unknown consumers block removal.
3. Obtain the operator's disposition for retained work and private evidence, and
   exact authorization for the resources to remove. Experiment completion is not
   permission to delete them.
4. Use native Worktrunk removal with existing preservation checks for the fixture
   checkout. Use qualified native owners for the selected workload and disposable
   worker. Do not bypass hooks, force dirty removal, delete unrelated images or
   caches, or remove a worker whose identity no longer matches the receipt.
5. Verify only the selected resources were retired and record the retained
   evidence's disposition privately. If any step fails, preserve the remainder
   and report partial cleanup rather than retrying broadly.

Filesystem isolation does not impose a byte quota on writable host shares.
Declared fixture sizes and bounded writes limit this experiment; they are not
general protection against host-volume exhaustion or a guest-kernel compromise.
Later real-checkout activation requires its own storage and threat-boundary review.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | required: exact-disposable-scope table; which resources may the workload touch and who selects them? |
| Interaction | required: ordered-operation table and pause procedure; which observations must precede execution, suspension and recovery? |
| State | required: ordered-operation table and outcome matrix; what distinguishes admission, failure, pause, resume and completion? |
| Data/trust | required: scope and outcome tables; can workload data grant authority or modify trusted evidence? |
| Schema | not_applicable: this runbook defines no persistent public schema and reuses the feature's private evidence authority. |
| Dependency/deployment | required: scope and ordered-operation tables; where do host, Lima, rootless Podman, gateway and workload ownership apply? |
| Quantitative | not_applicable: resource and time ceilings are contractual limits, not measured performance or comparison evidence; a chart adds no evidence. |

All required tables have adjacent Text Equivalents and remain editable source.
The runtime feature is canonical for limits and behavior; maintain both documents
in the same change when those contracts change. The initial host inventory is
informative provenance only and never a substitute for current private runtime
evidence.
