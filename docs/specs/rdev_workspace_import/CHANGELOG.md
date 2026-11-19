# Changelog — rdev Workspace Import

## 2026-11-19 — rdev workspace imported (DAI-036)

- Initiative: rdev-workstation-import slice `import-rdev-sessions` delivered
  together with `migrate-rdev-worktrees` and `handoff-and-resume` in one
  operational pass (release group `rdev-import`).
- The five-session remote-development cluster exported row-scoped from the
  retired macOS host store (152 MB) and imported into the VM live store,
  re-homed to the migrated project directory; 3,218 messages verified.
- Worktrees migrated as full self-contained clones under the VM project root
  (naming: source slugs, kebab-cased) with dirty-state parity (4/1/1 files)
  and untracked content restored; the main workspace clone carries all
  branches; stash WIP preserved as patches with one no-op already contained.
- Validation: identifier-neutrality publication test; per-unit status parity;
  message-count parity per session; import verified by listing.
- Deployment: VM-side import executed (this is the deploy evidence); the
  operator's remaining steps are documented in the VM-local handoff note.
- Gate Exceptions: none. Intended Final Push: `origin/main` (draft PR).
