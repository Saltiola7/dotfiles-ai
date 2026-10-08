# Recovery Discovery workstreams and delegation handoff

## Scope and ownership

All previously requested maintenance remains in scope except explicitly deferred
hibernation, which must be surfaced after the rest completes. Upgrade all installed
managed packages/apps and latest constraint-compatible Python dependencies,
including allowed dependency majors. Exclude enterprise-seo-tools
and production environments, preserve Python minor pins, preserve SDS GKE/shared
production inputs, and retain intentional PPC DVC omissions. Scope approval does
not authorize deletion of unknown worktrees, archives, histories or failed evidence.

These are independent research assignments, not claims that agents were launched.
Native delegation is explicitly requested. Use it only through exposed capabilities
and the selected coordinator's permissions. Delegates do not commit, activate live
services, alter lifecycle records or change another lane's contracts. Primary owns
integration, final QA and serialized deployment. Preserve provider affinity.

All lane outputs live under this directory's `findings/`. Each lane may create or
update only its named finding file during Discovery. Source inspection is read-only;
the coordinator alone edits MANIFEST.json and normative contracts. This avoids
concurrent edits to shared updater, launcher, guest and shell files.

| Lane / finding file | Read scope | Required result |
|---|---|---|
| native-updates.md | dotfiles-ai installer/updater/launcher sources and supported upstream interfaces | Installer selection, real update probe, keep/replace/retire map, state/service contract and affected tests |
| host-tools.md | dotfiles chezmoi declarations, host package/interpreter inventory; HOST-TOOLS.md | All current/outdated/held managed packages, retired-source reconciliation, patch-only Python plan and consumer boundaries |
| external-state.md | State-root declarations, auth/service and Git/DVC metadata; EXTERNAL-STATE.md | Bounded complete consumer coverage with intentional omissions, failures and exact repair ownership |
| herdr-host.md | shell_auth_startup specs, Herdr Host implementation and official integration; HERDR-RECOVERY.md | Signed replacement-volume registration route, unchanged ownership mode, exact-session preservation |
| guests.md | sandbox-vm, guest templates, native Lima metadata and bounded runtime checks | Mount/service/provision drift, credential/state boundaries, source/deployed comparison and fresh-machine probe |
| python.md | Personal/client project manifests and linked checkouts, excluding enterprise-seo-tools | Per-environment interpreter, pin, dirty status, production consumers, dependency health, isolated candidate checks and owning context |
| lifecycle-closure.md | Existing cycle status, Git/Worktrunk inventory, matching specs/changelogs | Original V2 cycle closure plan, missing-worktree diagnosis, stale authority reconciliation, preserved failure evidence and draft delivery ordering |

## Acceptance and qualification by lane

- **Host tools:** prove functional state access as well as versions. Reconcile
  installed tools into their existing chezmoi owner. Keep exact-minor Python pins.
  A newer installer is not evidence that every linked virtual environment works.
- **Herdr Host:** verify signature, volume identity, registration and live health
  probe; preserve pane layout and conversations. Use a supported promotion route.
- **Hibernation:** paused, not an active assignment. HIBERNATION.md retains
  acceptance criteria; surface it after the rest completes. No current fork/repair scope.
- **Guests:** prove mounts, boundary marker, required services and successful boot
  provisioning. Compare content drift before apply; never blanket-force unknown
  changes. No host credential/history copy into guest state.
- **Python:** resolve and runtime-test isolated candidates before activation.
  Dependency resolution alone is insufficient. SDS base/dev changes must preserve
  shared production constraints. Produce separate project-owned slices after
  classifying consumers; no aggregate upgrade across unknown environments.
- **Lifecycle:** existing completed migration is evidence, not an instruction to
  replay it. Reconcile original cycle and fresh provisioning separately. Report
  missing/uncertain paths without pruning. New runtime ownership must be reconciled
  with original fleet-update contracts before source retirement or delivery.

Every finding states facts with source locations, assumptions, unknowns, proposed
exact write paths, profile reference, risk, commands/checks, and readiness status.
Private identities, credentials, raw transcripts and local recovery inventories
stay out of these public artifacts. Report bounded metadata only.

## Dependency and deployment ordering

Research lanes may run concurrently; the following concerns serialize activation.

| Work | Must precede activation | Shared ownership boundary |
|---|---|---|
| Native updates | Installer rehearsal and reconciliation of old fleet contracts | One owner for both updater hooks, launcher locks and host package declarations |
| Guest repair/provision | Native-update ownership decision for tool installation changes | Coordinate all guest installers with native-update owner |
| Hibernation (deferred) | Rest of work completed and explicit resumption; Herdr Host repair and final launcher/update behavior | No active writer; retain future session-recovery ownership boundary |
| Python activation | Consumer classification and isolated candidate runtime tests | Per-project disjoint environments; serialize shared interpreter changes |
| Final lifecycle closure | Actual deployed evidence from affected lanes | Primary owns gates, commits and draft delivery |

These are activation dependencies, not reasons to serialize independent research.
Before Build, convert the qualified decisions into explicit manifest slice
dependencies and committed applicability plans; readiness receipts bind that DAG.

## Readiness and compaction checkpoint

| State | Meaning | Next action |
|---|---|---|
| Preferences registered/implemented | Native keys/MCP defaults deployed; operator confirmed agent cycling and autocomplete | Finish existing cycle evidence/artifact review and delivery |
| Remaining intent settled | Native local updates plus all prior maintenance accepted | Complete source-backed research findings |
| Discovering | Native installer behavior, hibernation recovery and Python consumers not fully qualified | Resolve evidence gaps; do not claim Build readiness |
| Ready | Contracts, profiles, ownership, dependencies and validation complete | Fresh receipt and Build preflight |
| Launch approved | Operator confirmed exact BEGIN digest | Implement in native checkout under the declared owner |

After compaction, re-read MANIFEST.json, README.md, this file, GATES.md,
each assigned context contract from the README coverage table, applicable findings
and referenced context artifacts; validate with
`dbsctrctl initiative-check --manifest docs/initiatives/ssd-toolchain-recovery/MANIFEST.json --json`.
Inspect native cycle status before resuming implementation. Do not derive readiness
from this prose or session summaries. Preserve the active preferences slice's
imported authority; the new updater direction belongs to separate Discovery.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: lane ownership table |
| Interaction | not_applicable: primary/delegate responsibilities are explicit |
| State | required: readiness transition table |
| Data/trust | not_applicable: private data stays local; output exclusions are explicit |
| Schema | not_applicable: no new persistent entities |
| Dependency/deployment | required: activation dependency table |
| Quantitative | not_applicable: no performance forecasts or measurements |

**Text Equivalent:** research outputs are disjoint and source is read-only for
delegates. Native updater ownership precedes affected guest installers; Herdr
repair and launcher qualification precede hibernation; consumer classification
precedes Python activation. Primary integrates and validates before delivery.
Settled intent is not Build readiness. Canonical source: tables above. Owner:
Discovery coordinator. Update trigger: ownership, dependency or readiness changes.
