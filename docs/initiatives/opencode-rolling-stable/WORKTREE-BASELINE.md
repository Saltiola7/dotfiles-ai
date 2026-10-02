# Approved native-worktree baseline

## Decision

The operator approved evaluating and adopting Worktrunk-managed sibling worktree
containers, repository-scoped external DVC caches, code-only creation and targeted
reflink materialization. Root-level sessions serve navigation and coordination;
implementation sessions belong to explicit native worktrees. Preserve skills,
specification/test gates and reviewed PR delivery. Do not preserve transparent
root-session routing merely to make conversations discoverable.

This reopens control-plane implementation readiness. Neither a permission API
fork nor an MCP rewrite is selected. Review dependent contracts before retiring
the current continuation system; existing enforcement remains active meanwhile.

The subsequent operator clarification is authoritative: Worktrunk replaces the
DBSCTR allocator, not an optional side path. DBSCTR registers and validates an
already-selected native checkout. No permanent legacy allocator, manual-creation
fallback, duplicate navigation registry or transparent root-session redirection
is part of the target. A cycle's recorded checkout/commit is provenance, not
allocation authority. Missing Worktrunk must be visible, never trigger custom
Git allocation. Existing records are retained as historical evidence; preserving
them does not authorize keeping a second allocation engine.

## Approved clarification: CLI, both runtimes and in-place adoption

Subsequent operator decision (INT-031): Initiative registration requires
interactive CLI confirmation of the fresh launch digest. Agents prepare the
preflight and operator command, then resume the registered cycle. Noninteractive
registration refuses; agents cannot simulate an operator terminal or supply
confirmation on the operator's behalf. This replaces the wrapper's exact
Initiative consent checkpoint without claiming native permission-policy or actor
authentication. Ordinary non-Initiative cycle registration remains unchanged by
this additional approval boundary. See the shared lifecycle contract for the
confirmation interface, rechecks, provenance and failure semantics.

The operator selected all four recommendations after implementation exposed
incomplete discovery. These decisions supersede incompatible earlier adapter
assumptions; they do not grant a failed gate exception or approve live migration.

1. Agents invoke `dbsctrctl` through native shell tools and their permission and
   sandbox policies. Retire redundant custom DBSCTR tool wrappers, not the skills
   or CLI validators. Native message/call attribution unavailable to plain CLI
   execution remains explicitly unavailable; neither arguments nor environment
   variables supplied by an agent become authenticated harness identity.
2. Replace task-worktree orchestration for both OpenCode and Codex CLI. Preserve
   native provider selection, session storage, credentials, approval and sandbox
   behavior. Codex Desktop remains outside the managed Codex CLI scope. Disposable
   internal validation worktrees are distinct from persistent agent task worktrees.
3. Pause existing writers and adopt task worktrees in place, continuing their
   original cycles. Preserve IDs, failed gates, evidence, commits, dirty work and
   existing paths. New tasks use the sibling layout. Directory relocation and
   cache consolidation are separately inventoried operations, not implicit parts
   of adoption. Do not create replacement production cycles or claim unfinished
   operations succeeded to make the old ledger disappear.
4. Add a small launch-time busy check with explicit operator override. It prevents
   accidental concurrent managed launches, not all subsequent writes. Do not
   recreate writer leases, per-tool admission or ownership-transfer protocols.
   Direct launches, in-UI session switching and work surviving a client exit can
   bypass launch-only coverage; native permissions remain the security boundary.

Implementation readiness is reopened. Preserve the unfinished implementation
worktree and original launch receipt. Its 12 focused passing checks and the 15
failing start/begin regressions are partial evidence, not completion. Reconcile
current specifications and obtain supported renewed authority before further
implementation; never modify private receipt rows to force agreement.

## Target organization

- Keep primary checkout locations stable.
- Allocate siblings in `<repository>.worktrees/<task>` with deterministic,
  collision-checked names, outside the primary checkout.
- Store one local cache per repository outside all checkouts, in the managed
  external state/cache hierarchy. Machine-specific paths belong in local config.
- Keep each worktree's DVC temporary/state/lock files separate; only the
  content-addressed cache is shared.
- No automatic full DVC pull or checkout on worktree creation; no copying of DVC
  caches or outputs through generic ignored-file bootstrap hooks.
- Materialize explicitly selected targets. Require reflink support for the
  large-data baseline; expose unsupported filesystems rather than silently copy.
- Reflinks isolate edits, but unique generated outputs still consume real space.
- Shared-cache garbage collection is a coordinated maintenance operation, not a
  worktree-removal hook. Preserve retained worktrees, refs, experiments and
  uncommitted DVC metadata; verify remote durability where required.

## Agent behavior

- One active writer per task worktree; no branch switching beneath active work.
- Primary checkout stays on its designated main/master branch.
- Discover current worktrees through Git/Worktrunk, not a second mutable registry.
- Broad-root sessions select repositories before searching. A short workspace
  guide identifies canonical repositories and alternate-checkout containers.
- Scope searches explicitly; broad-root exclusions are convenience, not access
  controls. Implementation uses a native session in its selected worktree.
- Worktrunk directory switching does not retarget an already-running OpenCode
  conversation. Selecting a conversation must preserve its native location.
- Retain the existing PR delivery flow; do not enable automatic local merge,
  branch deletion, full data hydration or cleanup hooks implicitly.

## Native qualification evidence

Disposable Git repository with main and two linked task worktrees, synthetic data
only, on the external volume. No production cache, outputs or remote were used.

### DVC 3.67.1

Passed: both worktrees began without DVC outputs; both resolved to the same
external cache; `cache.type=reflink` checked out only the selected 4-MiB target;
the unselected target remained absent. The primary and both workspace files had
different inodes. Editing one workspace left the sibling, primary and cache
content hashes unchanged. Primary branch remained main.

This is functional reflink evidence, not a physical-storage benchmark. APFS extent
sharing and actual allocated-space growth still need measurement with an
appropriate representative dataset and quiet-volume baseline. Summed directory
sizes are not physical-consumption evidence.

### OpenCode 2.0.21

Checksum-verified candidate, isolated home/config/data/service port and loopback
scripted provider. Created one native session per task worktree. Both had the
same project identity and appeared in the unfiltered session-list API invoked
from the primary checkout. Prompting session A from B wrote only into A;
prompting B from the primary wrote only into B. Primary checkout received neither
marker. No continuation plugins were loaded.

The upstream TUI session picker uses this API and supports an all-projects scope;
the actual TUI and Desktop interactions were not exercised. This evidence does
not qualify history migration, deleted-worktree resume or full deployment.

### Worktrunk 0.80.0

Installed the selected host dependency with Homebrew, suppressing automatic
Homebrew updates and cleanup. No shell integration or production Worktrunk
configuration was changed. Native executable reported `wt v0.80.0`.

In the disposable DVC repository, an isolated config used
`{{ repo_path }}.worktrees/{{ branch | sanitize }}`. Native Worktrunk created a
task worktree in that sibling container. Creation invoked from that linked
worktree still used the primary repository's container, not nested containers.
The data outputs stayed absent. A second branch name mapping to an occupied
sanitized path was refused without changing the existing worktree's branch.
Native list returned an inventory. `switch --execute` launched the fixture
command in the intended worktree, while the primary branch remained main.

These assertions qualify host allocation, naming collision refusal, inventory,
code-only creation and execution cwd. They do not qualify production hooks,
destructive cleanup, shell integration or guest installation. No custom
allocation helper was required for the proof.

## Remaining readiness work

### Existing ownership conflict confirmed

The current lifecycle allocator in `dot_local/bin/executable_dbsctrctl` creates
worktrees directly with Git, selects a hashed state-root parent, configures DVC
against the primary checkout's effective cache and writes `reflink,copy` into
local configuration. It then records registry-relative location and allocation
ownership in the cycle record. Switching only the directory template or adding
Worktrunk hooks would leave two competing allocation/bootstrap owners.

The replacement must give Worktrunk responsibility for prospective worktree
creation and navigation, while adapting cycle registration to the explicit
existing checkout. Preserve gate evidence and PR delivery separately from
allocation. Existing registry-based records need a compatibility path until their
cycles are completed or individually migrated, not rewritten en masse.

| Existing component | Proposed disposition | Required proof |
| --- | --- | --- |
| Lifecycle worktree allocator and DVC bootstrap | Replace prospective allocation with Worktrunk and explicit cache setup | One allocator; no duplicate bootstrap or implicit data checkout |
| Continuation path rewriting and root-target selection | Retire after native session qualification | Reads/writes remain in selected native worktree |
| Agent recovery/handover tools | Retire; use explicit operator-controlled in-place adoption | No abandoned process or uncertain operation is silently marked completed |
| Custom DBSCTR tool wrappers | Retire in favor of CLI through native shell permissions | Retained CLI gates work without fabricated message/call attribution |
| Codex task continuation bridge | Retire orchestration with the OpenCode counterpart | Native Codex sandbox, auth, storage and unrelated history hooks remain supported |
| Launch-time busy check | Add only bounded accident prevention with operator override | Concurrent managed launch refusal, no stale PID ownership, truthful coverage limitations |
| Cycle gates, evidence, commits and PR delivery | Keep, decoupled from allocator | Native-worktree cycles still pass required gates |
| Registry-based historical cycle paths | Preserve compatibility during transition | Existing dirty/active work remains addressable |
| Shared-cache maintenance | Keep explicit and repository-scoped | All retained data references preserved before GC |
| Workspace-root guidance | Add concise navigation/search boundaries | Repo selection precedes implementation and broad search |

1. Persist the qualified Worktrunk host dependency and configuration through the
   managed distribution. Existing host package home is Brewfile; shell integration
   and guest provisioning require their own supported implementation and checks.
2. Measure storage growth and inspect current effective cache/link configuration
   without interpreting missing local config as proof of private cache use.
3. Inventory lifecycle allocator, source bootstrap, continuation, cleanup,
   session recovery and DVC bootstrap consumers. Assign keep/replace/retire
   dispositions before changing their contracts.
4. Reconcile active-worktree-relocation scope; its unfinished artifacts and active
   cycle authority must not be overwritten or implicitly superseded.
5. First implementation should be a prospective worktree/cache baseline. Live
   dirty worktrees, private caches and active conversations migrate separately
   after preservation, process and ownership checks. No mass move or cache GC.

## Delivery boundary

Approval establishes this direction and disposable qualification. Worktrunk
0.80.0 is now installed on the host. No live worktree was relocated, existing
cache reconfigured, continuation guard disabled or recovery archive removed.
Implementation slices still need
fresh specifications, validated applicability and exact launch receipts.
