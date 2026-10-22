---
name: dotfiles-ai-update
description: Check dotfiles-ai dependency health and guide explicit tool updates through their existing installer owners and update runbook.
---

# dotfiles-ai Update

Make the requested dependency maintenance easy without replacing native installers.
Use this for dotfiles-ai dependency checks, post-upgrade compatibility review, or
an explicitly requested update. A check does not authorize installation or restart.

## Select the source

Use an explicitly selected dotfiles-ai checkout. Otherwise resolve the configured
source with `chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml source-path` when that
machine config exists. Verify its Git repository and instructions. If the current
checkout belongs to the same Git common directory, keep that task checkout rather
than redirecting to the primary. From another repository, read the selected source
without treating the caller's project as the maintenance target. If configuration
or source is unavailable, ask for the source; do not guess a machine path or clone.

Read `docs/UPDATES.md` there. It is the canonical owner/procedure inventory; do not
copy it into this skill or rely on version numbers remembered from another session.
For a check, use its inventory and verification guidance only; its pull, backup,
apply and update sequence is not a read-only check procedure.
For source changes, follow that repository's Discovery/DBSCTR and native checkout
rules. Loading this skill does not change agent mode or bypass native permissions.

## Check

Default to the requested environment and tools. “All dependencies” means the
source-declared manifests, installers, plugins, runtime locks, CI fixtures and
optional profiles, with transitive packages attributed to their existing locks.
It does not mean every package on the machine or every project's virtual environment.

For each relevant family, establish:

- Actual executable/installer owner and applicable platform/profile.
- Source pin or supported range, installed version, and running-service version
  where a qualified read-only check exists. Keep these observations separate.
- Applicable non-mutating health check, result and missing evidence. Mark disabled
  features, unavailable environments and retained legacy routes explicitly.
- Required next action: no change, qualification, targeted update or scoped repair.

Read effective local overrides privately; never print credentials, whole config,
session content or host inventories into public artifacts. Prefer bounded version
and health metadata. A version response is not complete health, and being newer
than a CI fixture is not automatically incompatible. Some diagnostic commands
start services: verify their behavior before invoking them. Checks never boot
guests, refresh authentication, run installers or create fallback state.

## Update

Use the selected family's existing procedure in `docs/UPDATES.md`: assess the exact
candidate, reconcile affected source, qualify that combination, preserve recovery inputs,
preview exact targets, then obtain approval for environment changes. Respect any
existing operational hold. Stop if the candidate, scope, source or destination
changes; a blanket “update everything” does not select an exact live deployment.

For Worktrunk, inspect Brew pin, supported native version and activation together.
Native template creation stays default. An operator's custom `--path` exception
is not an automatically qualified agent route. Never relax a version guard,
rewrite activation to pretend qualification, fake version output or skip hooks to
unblock the repair. Use only the runbook's explicitly approved recovery route.

Preserve native ownership for OpenCode/Codex and source/lock ownership for the
other families. Update only requested environments; install, service restart,
state migration, credentials and cleanup are separate operations. On failure,
retain evidence and report actual state rather than claim automatic rollback.

Finish with changed tool/source versions, checks and their limits, installation
versus running state, remaining blockers, and the next concrete action. Keep
source delivery and live activation distinct. No new updater, daemon or automatic
upgrade-all is needed for this workflow.
