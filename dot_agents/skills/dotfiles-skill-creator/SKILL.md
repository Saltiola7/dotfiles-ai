---
name: dotfiles-skill-creator
description: Create or update dotfiles-ai managed portable skills in source and install them in the shared Desktop and CLI skill location.
---

# Dotfiles Skill Creator

Load `skill-creator` from the current skill catalog when available. If the client
does not expose it there, resolve an existing original installation instead:
use an explicitly supplied creator path, the current `CODEX_HOME`, the managed
Codex CLI home resolved from the machine's dotfiles-ai configuration, or Codex's
default `~/.codex` home, in that order. For a runtime home, inspect
`skills/.system/skill-creator/SKILL.md`. Resolve the managed home through the
selected source's Codex configuration/launcher; do not guess a machine path or
scan unrelated runtime state. Read the original skill and its needed resources
in place. Catalog absence alone does not mean the dependency is uninstalled.

Delegate authoring, resources, metadata conventions and validation to that
original; do not copy, shadow, replace or modify the built-in skill. Its helpers
run from their original installation with the explicit selected source destination.
If no original installation is readable, report the missing dependency rather
than inventing a substitute or silently installing one.

1. **Select source.** Author in the selected dotfiles-ai task checkout at
   `dot_agents/skills/<name>`; deploy to `~/.agents/skills/<name>` independently
   of `CODEX_HOME` or client. If already in that task checkout, use it rather
   than chezmoi's configured primary source. Otherwise discover the machine's
   dotfiles-ai source through `~/.config/dotfiles-ai/chezmoi.toml`, verify the
   project through local instructions, and follow its Worktrunk ownership and
   shared lifecycle. Keep primary checkouts stable. Codex CLI and Desktop may
   retain the current conversation and target the selected task checkout through
   explicit command working directories and absolute file paths. Attachment or
   conversation relocation is not required; a shell directory change does not
   retarget or authenticate a session. If native tools cannot access the checkout,
   retain work and report the actual capability gap. Never infer unavailable
   identity or bypass gates.

2. **Check ownership.** Inspect same-name source, shared target, catalog and
   existing runtime-home copies before editing. Limit collision checks to those
   relevant locations. Preserve and reconcile divergent deployed edits; do not
   overwrite them or adopt unknown live files. Migrate only user-authorized
   skills; do not auto-sync system, plugin or repository skills. This public
   source must contain portable instructions/resources, without private source
   artifacts, credentials, account details, machine identities or private
   employer/client evidence. Keep those inputs in approved private storage and
   refer to them without copying them into this source.

3. **Author in source.** Pass the explicit task-checkout destination to
   `skill-creator`, overriding its runtime-home default. Preserve the complete
   bundle and relevant dependencies/resources. Edit source, never generated
   installed copies. Keep normal automatic discovery unless the user explicitly
   requests otherwise. Avoid hardcoded user identity, machine paths, repository
   URLs or task branches in portable output.

4. **Validate and install.** Run the selected original creator's
   `scripts/quick_validate.py` using a compatible existing Python environment.
   Report missing validator dependencies without claiming validation succeeded.
   Where useful, render the exact bundle and dependencies into an isolated
   destination and check file sets, bytes, references and second-apply/diff
   idempotency. Preview and apply with explicit selected `--source` and the
   machine config, `--exclude scripts`, and exact bundle-file targets only.
   Proceed within existing installation authorization and native permissions;
   ask only for actually missing material information or authority.

5. **Verify discovery.** Compare the complete installed file set and bytes with
   source; preserve and report unexpected installed resources. Check that only
   the intended same-name discovery copy remains. An identical
   legacy copy may be preserved outside discovery only within an authorized
   migration; reconcile divergent copies first. Never delete originals or move
   unrelated state. If the live selector cannot be queried, report filesystem
   validation and any possible client refresh/restart without claiming live
   discovery success.

Report source location, affected targets, validation and installation state.
Creating/installing a skill does not authorize publishing commits, pushing or
merging, changing provider authentication, or executing mutations the new skill
describes.
