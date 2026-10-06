# Native platform-local tool updates

Status: approved successor policy; implementation and live transition pending.
Authority: SSD recovery Initiative INT-003 and INT-013 through INT-015.
Profile: ../PROFILE.md. Product Intent: ../PRODUCT.md. Risk: elevated.

## Policy and precedence

For future OpenCode and Codex maintenance, this contract supersedes fleet-wide
update-on-apply, fixed package-lock launch authority, and custom updater ownership
in `opencode-rolling-stable.md` and `codex-rolling-stable.md`. It does not declare
their deployed implementations removed or reclassify their historical results.
Registered cycles retain their committed authority. Completed V2 conversion and
its archives, admissions, failed attempts and post-cutover work remain preserved.

The original rolling-stable Initiative's INT-001/003/005 fleet-convergence policy
is superseded for future maintenance. INT-002's artifact-owner choice and INT-008's
custom rejection-digest mechanism become historical implementation choices.
INT-004's no-implicit-restart outcome remains: binary installation and explicit
service restart are distinct. INT-006 state isolation, INT-007 compatibility
validation and INT-009 preservation of legacy rollback evidence remain obligations,
adapted to native ownership. INT-032's deferred periodic/idle automation is not
activated by this successor. One-time V2 migration/retirement obligations remain.

## Ownership and behavior

One upstream-supported installer owns each tool's executable on each platform.
Chezmoi owns bootstrap declarations, configuration, state routing and missing-volume
guards. Native installer targets must be distinct from managed guard paths.
No cross-platform transaction or host/guest version equality is required.

| Given | When | Required result |
|---|---|---|
| Existing native installation | Chezmoi reapplies | Preserve selected current executable; no pinned downgrade or competing owner |
| Missing installation and available state root | Bootstrap runs | Install a supported stable release; report failure if no healthy executable exists |
| Local native update requested | Installer runs | Only invoked platform changes; unrelated platform availability is irrelevant |
| New OpenCode binary with old running service | Installation finishes | Service continues until explicit restart; report installed and running versions separately |
| Missing or wrong external volume | Supported launch/bootstrap runs | Refuse before creating fallback state or package directories |
| Interrupted update or incompatible candidate | Recovery is considered | Preserve current state; diagnose actual binary/service state, never overwrite current database with old snapshot |
| Historical package lock | Qualified ownership transition completes | Lock no longer gates future native launches; historical evidence remains retained |

OpenCode uses native notify/manual-update policy, including local `/update`.
Automatic installation, periodic fleet polling and idle-session restarts are not
requested. Codex uses a supported explicit native update interface; any native
automatic-update marker or daemon behavior must be qualified before selection.
Package-manager lag is reported rather than hidden by adding a second installer.

Retain existing XDG and CODEX_HOME locations, credential boundaries, config
projection, exact-session selection, Herdr health/pacing and guest sandbox checks.
Maintenance subcommands must receive their native arguments without interactive-only
flags appended by wrappers. Direct service startup must use the same state policy.

## Transition and validation

Prove isolated installation, real version-to-version native update, service restart,
exact synthetic session persistence, guarded launch, absent-volume refusal and twice
repeated targeted chezmoi apply before live ownership retirement. Follow with
boundary-local authenticated and operator UI recovery checks. Preserve an exact
private pre-change inventory. Historical V2 admission does not qualify native updates.

Current evidence lives in the SSD recovery `findings/native-updates.md`: native
updates on macOS/Fedora ARM64 and synthetic session persistence pass. Linux requires
`which` for the inspected OpenCode installer. x86_64 runtime, native interactive
update, complete wrapper/service integration and managed reapply remain pending.

Kernel, Review/Integrate, Deploy, Operate and Maintain/Retire apply. Release is not
applicable because no independent package is published. No gate is passed by this
policy document. Concrete writable paths, dependencies, committed applicability plan
and fresh operator-confirmed registration are required before implementation.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: installer/chezmoi/platform ownership is explicit in prose |
| Interaction | required: transition and validation sequence above |
| State | required: behavior table above |
| Data/trust | not_applicable: state stays in place within existing boundaries |
| Schema | not_applicable: no new persistent schema selected |
| Dependency/deployment | not_applicable: local-only mutation and serialized transition are explicit |
| Quantitative | not_applicable: no comparative measurement claimed |

**Text Equivalent:** bootstrap and update use one native owner per platform while
managed guards retain state boundaries. Installation does not implicitly restart
OpenCode. Qualification precedes live retirement; failures preserve current data.
Canonical source: this contract. Owner: distribution maintainer. Update trigger:
installer, launch, state, activation or recovery semantics change.
