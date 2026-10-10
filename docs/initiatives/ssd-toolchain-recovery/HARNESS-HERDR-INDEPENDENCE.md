# Harness continuation independent of Herdr

## Scope

INT-047 requires Herdr presentation/integration state not to gate ordinary coding
harness continuation. Reuse `shell_auth_startup` and its Engineering Profile;
wrapper and explicit recovery routing are one bounded change. Risk: elevated,
because exact-session recovery and shared runtime admission must remain safe.
No native OpenCode/Herdr fork, service restart, database migration, authentication
relaxation, state-root relocation or hibernation activation.

## Behavior

- Given ordinary OpenCode/Codex or lifecycle work, when Herdr metadata is absent,
  stale, degraded or unavailable, the harness may continue under its own native
  permissions, storage, credential and service checks. Herdr is not lifecycle
  readiness authority.
- Given an ordinary OpenCode launch/resume inherits `HERDR_ENV`, when Host or
  restore helpers are unavailable, do not invoke those helpers as an admission
  dependency. Preserve requested conversation, cwd, options, shared-server
  authentication and explicit standalone/remote selection.
- Given explicit Herdr-managed restore, when pane/session ownership or actual
  storage-access evidence is missing, that recovery operation remains blocked.
  Its failure does not forbid unrelated ordinary harness work.
- Given explicit bulk restoration starts sessions, when starts are paced,
  recovery owns the existing lock, spacing, cancellation and deadline rules.
  Ordinary wrapper launches do not infer recovery ownership from environment.
- Given authoritative state storage or native service registration is unsafe,
  fail closed under the existing guard. Herdr independence is not permission to
  select another database, overwrite newer work or silently replace a service.

## Smallest implementation boundary

Remove Herdr Host preflight and automatic restore-helper pacing from ordinary
`dot_local/bin/executable_opencode.tmpl`. Retain existing environment routing,
state-root checks, native executable validation, authenticated shared-server
selection and Herdr-specific `--auto` behavior. Do not add a new bypass flag,
general fallback or parallel launcher.

Move pacing ownership to the explicit session-launch command assembled by
`dot_local/bin/executable_herdr-opencode-restore`: invoke its existing
`--pace-start` mode around the unchanged wrapper/session arguments. Preserve
capture/watch/restore admission, exact identity checks, durable pending mappings,
host preflight and occupied/working/blocked/unknown-pane exclusions. The move must
not double-pace or recursively wrap the pacing helper.

Codex and `dbsctrctl begin` have no equivalent Herdr gate in inspected source;
verify that fact and leave them unchanged. Optional integration reporting must
not become execution authority. Do not remove genuine operation-specific
preservation checks or bypass Herdr's current caller-context requirement.

## Validation and delivery

Affected tests: `tests/test_herdr_launchagent.py`,
`tests/test_herdr_session_recovery.py` and relevant native OpenCode distribution
checks. Isolated fixtures cover ordinary commands/resume with and without Herdr
variables, missing/failing Host and restore helpers, unchanged native arguments,
unsafe authoritative storage, authenticated shared-server selection, and explicit
restore retaining pacing/host/identity safety. All changed paths must be read by
their existing authorities. Do not launch real conversations to qualify a shell
fixture; do not request repository-wide QA.

Review context README/OPERATION/CHANGELOG and update wrapper-versus-recovery
ownership truth in the same implementation PR. Deploy only targeted managed
wrapper/helper paths together after rendered preview, private preimages and
candidate checks. No live capture/restore, service restart or pane mutation is
implied. Qualify rollback of the pair; retain the prior compatible pacing owner.

Kernel, Review/Integrate, Deploy, Operate and Maintain/Retire required. Release
not applicable: managed local scripts, no independently published package.
Native preflight and separate digest-bound approval precede implementation.
Herdr presentation does not block that preflight; any live preservation evidence
is evaluated at the operation that needs it.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: implementation boundary above separates ordinary launcher from explicit recovery owner |
| Interaction | required: Text Equivalent below orders both routes |
| State | not_applicable: existing recovery state machine and host health transitions remain unchanged |
| Data/trust | not_applicable: no new persistence or transport; existing exact-session/privacy contracts remain authoritative |
| Schema | not_applicable: no schema change |
| Dependency/deployment | required: paired targeted deployment and rollback procedure above |
| Quantitative | not_applicable: existing pacing bounds remain unchanged; no comparative claim |

**Text Equivalent:** Ordinary launch validates native state/service safety and
starts the requested harness without consulting Herdr Host or recovery helpers.
Explicit recovery first validates its own Host and pane/session authority, then
uses existing pacing to start the same wrapper and exact session arguments.
Optional presentation metadata never authorizes or blocks coding. Shell-auth
owner maintains this boundary when launch, recovery or paired delivery changes.
