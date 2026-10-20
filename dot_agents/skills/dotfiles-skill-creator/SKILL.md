---
name: dotfiles-skill-creator
description: Create or update dotfiles-ai managed portable skills in source and install them in the shared Desktop and CLI skill location.
---

# Dotfiles Skill Creator

Load the available `skill-creator` from the skill catalog. Delegate authoring,
resources, metadata conventions and validation to it; do not shadow, replace or
modify the built-in skill. If unavailable, report the missing dependency.

1. **Select source.** Author in the selected dotfiles-ai task checkout at
   `dot_agents/skills/<name>`; deploy to `~/.agents/skills/<name>` independently
   of `CODEX_HOME` or client. If already in that task checkout, use it rather
   than chezmoi's configured primary source. Otherwise discover the machine's
   dotfiles-ai source through `~/.config/dotfiles-ai/chezmoi.toml`, verify the
   project through local instructions, and follow its Worktrunk/native task-session
   routing and shared lifecycle. Keep primary checkouts stable. If the current
   session cannot be retargeted, give a precise handoff naming the selected
   checkout, native launch command and remaining work; a shell directory change
   does not retarget a session. Never infer unavailable identity or bypass gates.

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

4. **Validate and install.** Run the built-in creator's `quick_validate.py`.
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
