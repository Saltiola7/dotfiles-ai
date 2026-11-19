# rdev-workspace-import

Import the company remote-development (rdev) working set — the rdev session
cluster and its triaged worktrees — from the retired macOS host into the Try
Omarchy VM's standardized project space, so the operator resumes the paused
work from the VM with one authentication step.

Status: discovery complete; slices ready. Delivery tracked in
[MANIFEST.json](MANIFEST.json).

## Background

The macOS workstation retired (see
[macos-workstation-retirement](../macos-workstation-retirement/README.md));
the company workspace state remains on that host's external volume while the
Try Omarchy VM is now the sole workstation. The operator paused rdev work
(remote-development environment strategy, workspace dotfiles integration)
mid-stream in open sessions and wants to continue exactly where they left
off, from the VM.

Verified during discovery (read-only):

- The rdev work lives in the company workspace repository on the host: rdev
  branches under `dbsctr/remote_development/*` and `dbsctr/gke_platform/*`
  with linked-worktree checkouts, plus workspace-dotfiles topic branches.
- The rdev session cluster is identifiable in the host's 91 GB opencode store
  by title (remote-development strategy sessions including tab forks, the
  dotfiles-integration sessions, and the repository-LOC review fork). The two
  operator-named session identifiers matched no row in any inspected store;
  the final set is enumerated from titles and confirmed with the operator at
  build triage before any import.
- The host's herdr server is retired (no live layout to read); session
  identity comes from the store, not the pane mapping.
- Nothing required lives on the cloud company VM; the export source is the
  macOS host only. gcloud is provided by the workspace repository's mise
  tooling after import; the operator authenticates once post-migration.

## Scope

1. **Sessions** — row-scoped export of the confirmed session cluster from the
   host store into the VM's live opencode store, re-homed to the migrated
   project paths (established transplant machinery; no whole-store copy).
2. **Worktrees** — full-copy migration of the triaged rdev worktree set into
   `~/Projects` on the VM. Each unit is self-contained: a full clone checked
   out on its branch with uncommitted state carried as patches and stashes.
   Dangling linked-worktree copies are not migrated.
3. **Main clone** — the company workspace repository as a full clone under
   `~/Projects` with its relevant branch inventory documented.
4. **Handoff** — a note recording the old-to-new path map, the carried WIP
   per unit, and the remaining operator steps (mise install, one gcloud
   authentication, resume the imported sessions).

## Naming convention

`~/Projects` is the established VM project root (existing entries are flat
kebab-case). Migrated units keep their source slugs: the main clone takes the
repository's short name; each worktree unit keeps its `<repo>-<topic>-<date>`
(or rdev task) slug, lowercased and kebab-cased where needed.

## Non-goals

- No cloud company VM access, no gcloud authentication inside this
  initiative (operator-gated, post-migration).
- No bulk migration of the historical worktree sprawl beyond the triaged
  rdev set; the host volume remains the deep backup.
- No new managed tooling in this repository; no changes to the retired
  darwin stack.
- No company content (session bodies, repository names, organization names,
  identifiers) enters this public repository.

## Risks

- Session-identity mismatch (the operator-named identifiers were not found
  verbatim): mitigated by title-candidate enumeration and operator
  confirmation at build start; a wrong import is reversible by row deletion.
- Host store is 91 GB: exports are row-scoped and size-checked per session.
- Dirty-state carry may not re-apply bit-for-bit onto fresh clones: patches
  and stashes are exported separately and verified by status parity.
