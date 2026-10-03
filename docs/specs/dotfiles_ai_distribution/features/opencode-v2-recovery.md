# One-time V2 staging, recovery and admission

Status: Discovery contract; downstream readiness remains blocked on control-plane
implementation and remaining platform/service qualification. Risk: critical.
Owner: project maintainers. Profile: ../PROFILE.md; Product Intent: ../PRODUCT.md.
Modules: Python, Security, Cloud, Data, ML/AI. Authority: Initiative INT-010–018,
INT-022–030 and INT-033–034; V2-MIGRATION.md owns the fleet sequence.

## Outcome and exclusions

Move the inventoried managed installation to the latest official stable OpenCode
V2 selected at staging. Reuse existing managed installation, projection and recovery
mechanisms plus native conversion; do not build a replacement history converter,
fork OpenCode, add hourly scheduling or redesign Codex updates. A new release
does not silently replace an in-flight candidate. Native-workspace source is
delivered by PR 193; deployment is a separate obligation.

## Candidate and coherent generation

Candidate authority binds the official release metadata, exact platform package,
published integrity, verified archive bytes, extracted executable digest and
observed version. V2's official npm distribution is a qualified acquisition
candidate: verify its published SHA-512 integrity before extraction, validate
package identity/platform and archive members, then bind derived SHA-256 values
to those verified bytes. Do not describe derived hashes as publisher SHA-256
sidecars or claim registry-signature verification unless performed. No lifecycle
install hook or fallback artifact may run implicitly during staging.

Qualify the actual host and each claimed guest platform. Consumption of one host
artifact does not qualify Linux. Keep credentials and history in each boundary.
Inventory CLI and Desktop executable/service owners, state roots and version
selection before activation. Unavailable targets remain explicit; this one-time
scope does not inherit the deferred independent rolling-update policy.

Binary, configuration, managed launcher/package lock, service and data generation
form the recovery unit. The V1-only updater/validator must not reject a legitimately
activated V2 generation, overwrite its managed lock, or downgrade it. Existing
full-apply/start paths must recognize the verified transition boundary or hold the
unsupported update operation truthfully. No future update scheduler is required.
Unknown generations fail closed; no forged V1-shaped release lock is acceptable.

## History and admission

- Establish a fresh consistent native backup and verify integrity and identity.
  Keep the approved original read-only. Rehearse on a separate copy-on-write clone;
  refuse unavailable reflinks rather than silently creating another large copy.
- Bound native rehearsal time, process memory, output and disk consumption. Stop
  only owned isolated processes and preserve incomplete copies and failure records.
  Native checkpoint recovery must survive interruption without replacing the source.
- Use isolated homes/configuration and deny provider use during real-history
  conversion/reconciliation. Surface only bounded aggregate results. Do not send
  message bodies, identifiers, paths or credentials to hosted providers or public Git.
- Inventory opencode.db and any opencode-next.db. The observed 2.0.22 converter
  can overwrite previously imported V2 messages on overlapping V1 session IDs.
  Recheck under quiescence. Empty/disjoint prior-V2 history needs verified identity
  and reconciliation; overlapping histories block the native route until a safe
  disposition is qualified. Never silently choose one history or drop newer work.
- Native completion alone is insufficient. Reconcile session IDs, directories,
  projects, parents, message transformations, user/assistant text, reasoning,
  tool identities/inputs/outputs/errors, inline files and split synthetic content.
  Report the precise checked scope and any unverified metadata.
- The operator accepted the documented native incomplete-compaction and malformed
  record omissions, with full originals retained, and external-reference placeholders
  with available regular files archived separately. Current referenced-file snapshots
  are recovery aids, not proof of their historical bytes. Missing referenced files
  cannot be reconstructed from a database that never contained them.
- Unexpected omissions, mismatches or new transformation classes block admission.
  The accepted 2.0.22 report is not a blanket exception for arbitrary future loss.
- Existing worktrees are adopted in place only after their actual writers/jobs are
  quiescent and exact preimages match. Keep original cycle IDs, dirty files, failed
  gates and uncertain-operation evidence. Do not infer quiescence from a snapshot,
  empty pane or a completed tool response.

## Activation and recovery

Use the existing ordered migration sequence: inventory, stage and qualify,
maintenance window, writer quiescence, fresh backup, native conversion,
reconciliation, exact conversation resume, fleet verification, active-route
retirement. Missing external storage must refuse startup instead of creating an
internal fallback database. Desktop must obey the same qualified state boundary.

Before normal work resumes, a failed transition recovers the compatible prior
binary/configuration/service/data generation using retained evidence. After V2
work exists, preserve that new generation and recover forward or through an
explicitly qualified path; never restore an older snapshot over new work.
Retirement removes only owned stale executable/configuration routes. Archives,
dirty worktrees, attachment recovery files and shared DVC caches are not cleanup
targets. Updating services must not silently retarget native sessions or providers.

## Validation and gates

Use existing pytest, Bun, chezmoi rendering, shell/launchd checks, native CLI/API
probes and platform smokes. Candidate staging/lock compatibility needs success,
digest/metadata drift, unavailable-target and interrupted-activation cases. Real
history needs its bounded local transformation report; operator UI observations
remain separate from API success. Measure maintenance requirements from actual
rehearsal, including bootstrap, reconciliation and recovery, not small fixtures.

Kernel, Refactor, Review/Integrate, Deploy, Operate and Maintain/Retire are required
for live delivery, results pending. Release is not applicable: consume upstream
artifacts without publishing a new package. A source-only implementation slice
may use a separate profile-bound plan, but cannot claim live gate completion.
There are no Gate Exceptions.

## Visual Evidence

Boundary, interaction, state, data/trust and dependency/deployment: reuse the
canonical V2-MIGRATION.md flow and native-workspace adoption tables. Owner:
distribution maintainer; update on changed admission, recovery or target ordering.
Schema: not applicable; canonical native schemas and generation manifests are
the authority. Quantitative: not applicable; retained single-host rehearsal
observations are not a cross-platform performance guarantee. Text equivalent:
stage one exact candidate, preserve original boundary-local history, convert only
after quiescence, reconcile before admission, and retain both generations if new
V2 work makes rollback unsafe.
