# OpenCode native workspaces and lifecycle CLI

Status: specification reconciliation; not deployment qualification.
Owner: project maintainers. Profile: `../PROFILE.md`. Risk: critical.
Authority: Initiative INT-027–INT-030 and the shared lifecycle native-workspace
contract. This supersedes porting the custom continuation transport unchanged.

## Behavior and boundary

Worktrunk selects the checkout; OpenCode owns the native session location. Skills
invoke dbsctrctl through native shell permissions. Retire the redundant custom
DBSCTR tool catalog and transparent continuation hooks. Do not replace the missing
custom-tool ask API with an ad hoc permission evaluator, fork or MCP server.

Native session visibility is independent of storing sessions at the primary
checkout. Qualify the actual TUI and Desktop picker/resume behavior, not only the
already-tested API. Selecting an old session must not create an empty replacement
or silently retarget its worktree. Session migration, attachments and compaction
verification remain separate required rollout work.

Preserve native role permissions, model/provider selection, credentials, external
state-root checks and unrelated MCP integrations. Plan/read-only roles do not gain
mutation permission when custom wrappers disappear. Native shell approval does
not itself prove a DBSCTR gate passed; the CLI validates lifecycle state/evidence.

## Source ownership and retirement

Audit consumers of `plugins/continuation.ts`, `lib/continuation.ts`,
`tools/dbsctr.ts` and the continuation-related parts of `lib/dbsctr-runtime.ts`.
Remove routing/admission/tool-wrapper dependencies, retaining independently used
history/incident/metadata behavior only where its CLI interface is qualified.
Update Initiative context injection, managed agents, skills and capability probes
so they neither advertise removed tools nor require their successful loading.
Source removal alone is insufficient: rollout must retire deployed stale plugin
files and stop relying on modules cached by already-running processes.

## Privacy and identity

Initiative registration uses the shared INT-031 interactive CLI confirmation
contract. Agents prepare preflight and the operator command, then resume the
registered native cycle. They cannot synthesize confirmation, simulate a terminal,
or substitute general shell permission for exact Initiative consent. Native
permission enforcement and current unavailable attribution remain distinct.

Before removing each tool wrapper, trace its validation, redaction, private-data
handling and consent behavior. Required filtering moves into the CLI output
boundary rather than disappearing. Agent-facing stdout must not expose transcripts,
credentials or governed private bodies. Fail closed or report a capability as
unavailable when its safe projection requires unavailable native identity.
No generic shell-output passthrough substitutes for a validated private-result
projection. Preserve the existing operator-invocation requirement for incident
evidence; revise its source instructions explicitly for any approved CLI route.

Native actor/message/call identity absent from plain CLI execution stays unavailable.
Do not recover it by guessing the latest assistant message, borrowing another
session, inspecting inherited environment claims or reusing a historical receipt.

## Acceptance

- Ordinary native task sessions operate without the custom tool/continuation plugins.
- CLI registration and required lifecycle gates work in the explicit checkout.
- Root navigation sessions remain useful without becoming hidden task writers.
- Negative native permission cases remain denied; missing attribution is truthful.
- Each retained private CLI result passes synthetic secret/content-leak tests.
- Existing worktrees adopt in place only under the shared transition contract.
- Launch-only busy-check limitations remain visible, including in-UI session changes.

Use existing pytest/Bun/rendering authorities and isolated scripted native fixtures.
Actual Desktop, guest and large-history qualification remain required for rollout.

## Visual Evidence

Boundary/state/interaction: reuse the shared native-workspace ownership flow,
adoption table and approval handoff table with their Text Equivalents. Other visuals are not applicable: this contract
removes an adapter layer and adds no independent protocol, storage schema,
deployment topology or quantitative claim.
