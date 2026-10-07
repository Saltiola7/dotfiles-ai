# Retired host source reconciliation

Home: Saltiola7/dotfiles, host_tool_maintenance; existing PROFILE.md applies.
Requirements: INT-002, INT-003, INT-012, INT-018, INT-021. Elevated risk because
chezmoi can otherwise recreate a retired service. Draft PR and targeted deployment.

## Evidence and ownership

The primary Brewfile has uncommitted removals of Colima, Docker, docker-buildx,
docker-compose, docker-credential-helper, Loop and Shortcat. These match the
approved retirement direction. The separate opencode-desktop removal belongs to
native-runtime work and must remain untouched by this slice.

The host reports no dev.dotfiles.colima-atuin service, no deployed matching plist,
and no deployed start-colima-atuin wrapper. Source still includes all three of
the launcher, plist and bootstrap hook. Current tests explicitly require those
retired sources and must be reconciled with the new non-reintroduction contract.

## Behavior contract

| Given | When managed source is evaluated | Required outcome |
|---|---|---|
| Retired Colima/Docker packages | Brewfile is read | None of the five retired formulae is declared |
| Intentionally absent Loop/Shortcat | Brewfile is read | Neither cask is declared; preferences remain intact |
| Retired Colima launch service | Chezmoi renders/plans | No script, plist or wrapper recreates or starts it |
| Retained VM, archive, credentials and app preferences | Source retirement occurs | Leave all retained data untouched |
| Other host/guest runtimes and Atuin state | Source retirement occurs | No guest, container, service, runtime or history operation |
| Unexpected live retirement target appears during implementation | Deployment is considered | Stop and reassess; do not silently remove or stop it |

Remove the three obsolete source files and their dead mac-mini .chezmoiignore
entries. No replacement retirement daemon, script or registry is needed because
live targets are absent. Keep historical shell variables and optional SSH includes
that support manual rollback; they do not install or start Colima. Do not add broad
.chezmoiremove entries or purge archives. No package uninstall is part of this slice.

Writable files: Brewfile, .chezmoiignore,
run_onchange_after_bootstrap-colima-atuin.sh.tmpl,
private_Library/LaunchAgents/dev.dotfiles.colima-atuin.plist.tmpl,
dot_local/bin/executable_start-colima-atuin, tests/test_terminal_environment.py,
and host_tool_maintenance completion documentation. Preserve unrelated primary
changes and all dated recovery hooks. Native runtime scope is separate.

## Validation and deployment

Establish a failing non-reintroduction regression; replace only retired-service
tests, retaining runtime-state and external-volume tests. Run affected terminal,
AI ownership, uv and SDK tests; validate Brewfile Ruby syntax. Inspect the rendered
managed target inventory and script plans without running a full apply or brew
bundle, since other unfinished lanes still own broader provisioning conflicts.

Deploy by reconciling only these owned source changes in the configured primary,
after retaining source preimages. Recheck absent live targets and service. Verify
unrelated source hunks are retained. No active runtime restart or removal is needed.
Rollback is a reviewed source revert; never replay retired bootstrap merely to
demonstrate rollback. Kernel/review/deploy/operate/maintain required; release not
applicable. No unresolved decision remains for this bounded source reconciliation.

## Visual Evidence

State: required; canonical table above. Boundary, interaction, data/trust, schema,
dependency/deployment and quantitative: not_applicable; ownership, absence checks
and retention order are explicit without new topology or data movement.

**Text Equivalent:** remove declarations capable of restoring retired software;
preserve data and unrelated owners; stop if an assumed-absent live target appears.
Owner: dotfiles maintainer. Update this contract when retirement scope or observed
live state changes.
