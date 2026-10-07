# Native updates with preserved external state

Status: Discovery contract; implementation readiness remains open.
Successor policy and historical-requirement precedence:
[native platform-local updates](../../specs/dotfiles_ai_distribution/features/native-platform-updates.md).
Context: dotfiles_ai_distribution, with Codex/OpenCode control-plane interfaces.
Profiles: docs/specs/dotfiles_ai_distribution/PROFILE.md and
docs/specs/codex_control_plane/PROFILE.md. Product Intent:
docs/specs/dotfiles_ai_distribution/PRODUCT.md. Risk: elevated (live runtime and
state migration). Requirements: INT-003, INT-013 through INT-015.

## Accepted outcome

INT-024 subsequently defers guest activation and guest qualification work. Current
live transition scope is macOS ARM64 only; retain existing guest and x86_64 routes.
Prior Fedora isolated evidence remains valid historical evidence, not deployment.

Native installers own executables. Chezmoi owns installation declarations,
configuration, external-state routing and missing-volume protection. OpenCode
/update operates on the invoked platform only. Codex likewise uses a supported
per-platform installation/update method. There is one executable owner per tool
and platform, with no fleet transaction dependency and no silent downgrade on apply.
Latest means official stable; report package-manager lag rather than introducing
a competing installation. Use the native notification/manual-update flow; automatic
installation was not requested. Do not invent an idle-session restart controller.

Operator decision INT-023 limits this activation to macOS ARM64 and Fedora ARM64.
Linux x86_64 native activation is deferred; retain its existing installation and
launch route until separately qualified. Shared template changes must prove that
the deferred platform does not accidentally select the new native route. Lack of
x86_64 runtime evidence no longer blocks ARM64 readiness, but must stay explicit.

State remains at the existing machine-configured external root. OpenCode uses its
existing XDG paths; Codex retains its existing CODEX_HOME. CLI and desktop state
remain separate where already separate. Native updating is not data relocation.

## Behavior and failure contracts

| Given | When | Then |
|---|---|---|
| Existing healthy installation | Native update is invoked | Only that platform changes; existing state stays in place |
| Updated executable | Client and background service restart | Same state paths, configuration, credentials and exact conversations resolve |
| Native update newer than installation baseline | Chezmoi reapplies | New version remains selected; no old wrapper or lock rejects it |
| External volume unavailable | Any supported launch path runs | Refuse clearly; never silently create a second empty local profile |
| Download or installation fails | Operator retries | Existing state survives; report actual executable/service state before recovery |
| Current work exists after an update | Recovery is needed | Never restore an old database over current work; inspect schema compatibility before binary rollback |

## Qualification sequence

1. Inventory actual binary resolution, installer ownership, wrappers, service
   environment and package/admission records without exposing credentials/history.
2. Select one upstream-supported installer per platform. Inspect its PATH edits,
   self-update target, symlink handling and service activation semantics. Do not
   assume a native updater will preserve a same-name wrapper.
3. Rehearse bootstrap and a real version-to-version update using disposable state.
   Exercise native /update behavior, not only a mocked download or --version.
4. Verify fresh interactive/noninteractive shells, Herdr launch, and background
   services all select the new executable and intended state. Validate the absent-
   volume path using isolated configuration, not by unmounting the live volume.
5. Reapply targeted chezmoi declarations twice; prove no downgrade, no conflicting
   executable and no state-path drift. Preserve unrelated user configuration.
6. Perform boundary-local live checks and operator UI resumption after the approved
   restart. Preserve a private pre-change inventory and exact session identifiers.
7. Retire redundant updater hooks/locks only after qualification. Retain historical
   migration evidence and recovery archives. Never use data-purging uninstall flags.

## Sources and concrete affected interfaces

- OpenCode V2 config documentation: native notify/auto/disable; automatic install
  does not itself restart the server. CLI debug paths is read-only path evidence.
- Codex advanced configuration: CODEX_HOME controls CLI state location.
- dot_local/bin/executable_opencode.tmpl and executable_codex.tmpl: launch routing.
- dot_local/bin/executable_opencode-update-all, executable_codex-update-all and
  executable_codex-project: package locks, recovery and executable validation.
- run_after_update-{opencode,codex}.sh.tmpl and installation scripts: chezmoi ownership.
- Distribution PRODUCT.md journeys 2/3 and profiles now reference the approved
  native platform-local successor. Its precedence map supersedes original
  opencode-rolling-stable INT-001/003/005 for future maintenance, preserving the
  original manifest and registered migration authority as history.

Read-only evidence establishes native external-state support, not installer
transition success. Remaining research: exact installer paths and native update
semantics on each platform; service environment persistence; lossless removal of
digest-gated launch dependencies; restart/resumption and fresh provisioning.

## Gates and readiness

Kernel, Review/Integrate, Deploy, Operate and Maintain/Retire are required.
Release is not applicable: no independently published package. A committed
applicability plan and exact file ownership must be produced after installer
qualification; no launch receipt is issued from this draft contract.
Project-selected authorities: affected pytest/rendering suites, shell syntax,
native installer/CLI probes, resolved paths, service checks and operator UI evidence.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: installer/chezmoi/state responsibilities are explicit above |
| Interaction | required: qualification sequence above |
| State | required: behavior/failure transition table above |
| Data/trust | not_applicable: data remains boundary-local; no transfer is introduced |
| Schema | not_applicable: no new persistent data schema |
| Dependency/deployment | not_applicable: workstream dependency table is canonical |
| Quantitative | not_applicable: no quantitative claim |

**Text Equivalent:** inventory and isolate first, qualify native installation and
update, prove state and service continuity, then retire redundant updater ownership.
Failure must preserve current state and cannot justify snapshot replacement.
Canonical source: this contract. Owner: distribution maintainer. Update trigger:
installer ownership, activation semantics or state-location contract changes.
