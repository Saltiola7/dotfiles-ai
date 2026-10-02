# Native workspace distribution and transition

Status: reconciled target contract; rollout qualification remains open.
Owner: project maintainers. Profile: `../PROFILE.md`; retain its Product Intent.
Authority: the shared lifecycle native-workspaces specification and approved
Initiative INT-022–INT-030. Risk: critical for rollout and retained work/data.

## Managed configuration

- Declare Worktrunk in host dependency provisioning and project its native user
  configuration through chezmoi. Use the qualified sibling worktree template.
- Worktrunk 0.80.0 is the observed host baseline. Official release inventory also
  supplies aarch64 and x86_64 Linux musl archives with SHA-256 sidecars. Guest and
  remote-user provisioning must verify official artifacts and native version/config
  behavior before enabling task launches. Do not install the host executable in
  guests or add a custom worktree allocator when the dependency is unavailable.
- Shell integration uses Worktrunk's supported shell initialization. Keep native
  argument boundaries and current shell behavior; do not rewrite user startup
  files ad hoc or depend on changing an agent subprocess's parent directory.
- Worktrunk's `-x` invokes the bounded agent-worktree supervisor for managed task
  launches. Keep primary checkout paths stable and use native sessions in explicit
  worktrees. Broad Git-root sessions remain navigation/read-only coordination.
- A concise workspace-root guide identifies canonical repositories and the sibling
  container convention. Native Git/Worktrunk inventory replaces duplicate lists.
  Scope searches to selected repositories; ignore patterns do not grant permissions.
- Preserve protected-base PR delivery. Do not activate automated local merge,
  squash/rebase, branch deletion or broad ignored-file copying as defaults.
- Worktrunk 0.80.0 does not automatically configure an upstream for a differently
  named new feature branch. Establish the intended native Git tracking target
  before lifecycle preflight; missing or changed upstream remains a refusal.
  Do not publish early or weaken Final Push to compensate for missing tracking.
- Initiative setup includes the shared INT-031 interactive CLI confirmation.
  Expose its operator handoff in both harnesses. Headless automation cannot
  simulate that confirmation or claim a general shell grant is exact consent.

Use blocking managed **user** hooks for required preservation checks: Worktrunk
allows declined project-hook approval to skip project commands and continue.
The user pre-remove hook invokes the shared CLI eligibility checker; Worktrunk
alone removes the checkout. Agents must not use `--no-hooks` to bypass it.
The native `step promote`, `step push`, automatic merge/prune and experimental
relocate paths are not normal agent task operations. In particular, promotion
must not swap a task branch into the primary checkout. Later relocation can
evaluate Worktrunk's native experimental relocate command under a separate
qualification, rather than reviving the custom relocation engine.

## DVC policy

Configure one explicit repository-scoped cache outside all its checkouts and on
the target's intended storage boundary. Local absolute paths remain private local
configuration. Configure each worktree separately; do not share mutable DVC state
or locks. Bootstrap does not pull, checkout, copy datasets or collect garbage.

Use reflink-only materialization. Unsupported filesystems report a capability gap
rather than silently copying large outputs. A code-only worktree does not require
dataset materialization. Qualify host/guest data behavior on the actual target
filesystem before claiming support. Distinct newly generated data remains a real
storage cost; directory-size sums are not physical extent accounting.

Inventory existing effective cache directories and link types before consolidation.
Do not infer private caches merely from absent local config. Preserve unique cached
objects and dirty outputs; changing a config path is not migration. Cache moves and
garbage collection require their own reviewed inventory/approval and coverage of
retained refs, worktrees, experiments and uncommitted DVC metadata. Worktree removal
never implicitly collects the shared cache.

## Cutover sequence

1. Finish source integration and both-harness CLI/privacy/permission tests.
2. Render/stage managed dependencies, configuration and removal of stale adapters.
3. Inventory affected processes, native sessions, active cycles and DVC state.
4. Obtain the bounded maintenance approval; pause applicable writers/jobs and
   retain consistent native history/configuration and lifecycle recovery material.
5. Activate the coherent runtime/configuration/helper generation. Do not leave old
   cached plugins active beside the replacement or disable unrelated protections.
6. Preview and explicitly adopt existing task worktrees in place. Preserve original
   IDs, failed gates, uncertain evidence and dirty files. Refuse ambiguous cases.
7. Resume using native session locations and qualified launch paths. Verify no
   branch movement or data hydration occurred in another checkout.
8. Verify every claimed platform and active launch/provisioning path before retiring
   the old generation. Retain original archives and post-cutover work on rollback.

OpenCode V2 database/Desktop/fleet migration remains governed by V2-MIGRATION.md;
this contract does not turn source delivery into deployment permission. Codex CLI
keeps native auth/state/update boundaries; Codex Desktop remains unmanaged.

## Completion evidence

Require rendered shell/config checks, native Worktrunk behavior, both runtime
launch/resume checks, DVC reflink/independent-edit checks, bounded concurrent launch
tests, and in-place adoption/interruption checks. Measure representative physical
storage growth with an explicit baseline and report uncertainty. No blanket live
qualification from synthetic fixtures or a single host result.

## Visual Evidence

Boundary/state: reuse the shared lifecycle contract's ownership flow and adoption
table with their Text Equivalents. Interaction/deployment: the numbered cutover
sequence is the authoritative ordered transition (owner: project maintainers;
update when ordering changes). Data/trust, schema and quantitative charts are not
applicable here: no new shared data store or measured savings claim is introduced.
