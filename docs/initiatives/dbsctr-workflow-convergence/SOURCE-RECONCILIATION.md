# Workflow convergence: source reconciliation

Report-only baseline: `493fac03ea0b7959d38dc375f6e246995a41bfe1` in this public
repository. These are inspected source facts, not rollout, cleanup eligibility,
remote-data durability or performance-improvement claims. Private repository and
host inventories are deliberately excluded from this artifact.

## Reuse before replacement

| Concern | Existing authority or implementation | Observed gap / Discovery action |
|---|---|---|
| Verified delivery | `../dbsctr-delivery-lifecycle/README.md`; lifecycle feature `automatic-delivery.md` | Already specifies opt-in merge, exact head, safe base synchronization and cleanup. Reconcile its all-checks rule with repository-owned affected-check classification and its legacy session assumptions with native handoff; do not create a second delivery engine. |
| Native workspaces | Lifecycle feature `worktrunk-native-workspaces.md`; distribution feature `native-workspaces.md` | Sibling layout is normative today. Central roots, opt-in automatic cleanup and standing bounded DVC delivery consent are intentional new requirements, not already enabled behavior. |
| Native cleanup hook | `dot_local/bin/executable_dbsctrctl`: `workspace_remove_check` | Completed cycles receive a fixed 24-hour hold. Unknown ignored data and relevant open files/processes block removal. Preserve the data/process safeguards while replacing age with verified preservation eligibility. |
| Git preservation | Same removal checker | Candidate refs include delivery feature and base refs and checkout upstreams. Remote feature-branch preservation is not proof of merge into the ultimate default branch. Track intermediate delivery separately from final promotion. |
| DVC preservation | Same removal checker; `worktree-dvc-setup` | Shared external cache, independent local config and reflink-only setup already exist. Setup does not migrate populated caches. Local DVC status/cache existence alone is not independent proof that required remote objects were uploaded. |
| Inventory coverage | `dbsctrctl`: `global_worktree_roots`, `worktree_inventory` | Global enumeration starts from the retained registry layout. Inventory filters `created_by_dbsctr == true`, while native registration writes `false`. Reconcile native Git/Worktrunk coverage and completed-cycle correlation instead of trusting the legacy list as exhaustive. |
| Inventory cost | `worktree_inventory`, `worktree_bytes` | Size collection is coupled to each worktree record. Metadata classification needs a bounded fast path; expensive storage accounting should be optional and distinguish allocated blocks from unique physical extents. |
| Launch isolation | `agent-worktree`; native workspace specification | Foreground launch reservation exists. It is not universal process ownership, a session registry, or authority to kill jobs. Cleanup must retain unknown or live consumers. |
| Timing | DBSCTR skill: Critical-Path Profiling; `phase-span`, `execution-dag`, `execution-benchmark`, `cycle-performance` | Structured timing exists. Unsupported automatic attribution stays unavailable; do not infer complete telemetry from the presence of commands. Reuse the existing cycle-speed Initiative and its unresolved source/attribution contracts. |
| Historical delivery labels | Existing delivery, cycle-speed and toolchain-recovery manifests | Mixed captured/ready/delivered labels require reconciliation to Git evidence. For example, native platform-parity source remains labelled ready in its older manifest even though the baseline includes merged source delivery. Do not relaunch completed implementation from a stale label, and do not mark an unrelated active cycle complete. |
| Review / incident / improvement | Existing review, incident, backlog and performance-audit skills | Preserve native read-only and privacy boundaries. Unavailable indexes are not empty inboxes. New automatic incident submission requires its own qualified path, opt-in external destination and sanitized evidence. |
| Integration skill | `dot_agents/skills/dbsctr-integrate/SKILL.md` | Existing batch machinery is restricted to autonomous-improvement sources and draft publication. It is not a generic intent-driven PR merger or permission to promote claims, waive checks or alter active cycles. |
| Minimal engineering / prose | Managed `AGENTS.md`; Ponytail/Caveman skills | Existing defaults cover implementation simplicity and concise communication. Audit actual loading and duplication; retain gates, acceptance evidence and material caveats. No need to copy full skill prompts into every lifecycle phase. |
| Provider guidance | DBSCTR `references/openai.md`, `references/anthropic.md` | OpenAI reference already names GPT-6.1 and bounded delegation. Anthropic reference names Opus 5.5 but links an older Opus 5 guide. Verify current provider-specific differences and evaluate a minimal correction, not wholesale prompt replacement. |

Paths in the table are repository-relative; feature paths are under their existing
`docs/specs/<context>/features/` homes. Existing unfinished cycles and historical
receipts remain untouched. A document or ready label never proves installed runtime
behavior.

## Evidence boundaries

- Native Git inventory describes current registered paths and refs; ancestry of a
  cached remote-tracking ref is not fresh remote merge verification.
- Read-only lifecycle inventory must report bounded unavailability when its source,
  record validation or time budget fails. Do not reconstruct private Cycle Records
  or session databases through an alternate route.
- Effective DVC cache configuration, link capability, immutable object identity and
  remote durability are separate checks. A declared cache directory is not proof
  of any of the others. No full hydration or cache garbage collection is authorized.
- A private inventory is an observation, not a second task registry or deletion
  authorization. Publication checks must cover every new tracked document.

## External research inputs

Use public sources as research inputs; qualify installed versions and native routes
before changing runtime behavior:

- [Worktrunk configuration](https://worktrunk.dev/config/): native centralized path
  templates and user project-specific configuration exist. Current website support
  must be verified against the selected installed version; do not use command-line
  config overrides to evade native permission restrictions.
- [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) and
  [GPT-6 model guidance](https://developers.openai.com/api/docs/guides/model-guidance):
  distinguish model-specific facts, transferable hypotheses and harness support.
- [Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/overview) and its
  [prompting guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5):
  validate model/platform-specific tool, thinking and continuation behavior.
- [RTK](https://github.com/rtk-ai/rtk) and
  [trim-1](https://github.com/caveman-ai/trim-1): command filtering and extractive
  context reduction are different from concise generated prose. Both may omit
  evidence. Availability is not adoption, and output-byte estimates are not measured
  provider savings. Default to no stacking, no proxy and no authority compression;
  preserve an unfiltered recovery route and evaluate correctness before rollout.

## Next readiness work

This is the historical research checklist, not a reopened intent interview.
The finalized decisions and acceptance boundaries are in
[DECISIONS.md](DECISIONS.md); the compaction/resumption index is
[BUILD-HANDOFF.md](BUILD-HANDOFF.md). Specification decisions are settled;
implementation, rendered-PR review, runtime acceptance and launch approval are not
claimed by this report.

1. Reconcile the statement ledger with existing delivery, native-workspace and
   cycle-speed authority, retaining historical failures and deferred work.
2. Specify bounded metadata inventory, eligibility and unknown-artifact disposition
   before selecting any completed-checkout remediation batch.
3. Bind portable configuration, merge/CI policy, DVC delivery and native handoff
   contracts to their existing context owners and independently testable slices.
4. Keep private adoption/CI work in its own authority home; public examples remain
   synthetic and contain no private project identity or source material.
5. Produce launch receipts and exact preflight approval only for fully specified
   Build-owned slices. This report grants no implementation or deletion authority.
