# Performance Audit Orchestration

## Ownership

`opencode_control_plane` owns the audit command, skill discovery, provider-local
agent routes, bounded subprocess behavior, and sanitized session evidence exposed
to the lifecycle audit. The lifecycle context owns conclusions and priority.

## Contracts

- The current primary orchestrates the audit; commands do not silently switch
  agent or provider.
- Private session evidence stays in the primary. Hosted subagents receive only a
  bounded public research question or fixed-commit repository scope.
- Explore is for local architecture gaps. Scout is for current authoritative
  external guidance. At most three independent lanes run concurrently.
- DKS is attempted once. Graphify is loaded only after a graph-existence check.
- Incident Scan runs independently from optional DKS or external research so a
  sibling failure cannot cancel required evidence.
- History and incident subprocesses have bounded deadlines and process-group
  cleanup. Timeout remains explicit rather than becoming an empty result.
- `reviewer-openai` remains available only for explicit review, critical work, or
  a named specialist lens. A routine final double-check is not a reviewer task.
- Model and reasoning changes require comparable-cycle evaluation. The default
  primary remains GPT-5.6 Sol Fast medium; Explore remains Luna Fast low; Scout
  and bounded Builder remain Terra Fast medium unless evidence supports change.
- Prompt instructions state each rule once and compact at meaningful milestones.

## Evidence Interpretation

Reviewer presence, model identity, token count, tool count, and elapsed time are
associations. Reports include cohort composition, active/completed state, review
session count, timing coverage, and attribution quality before recommending a
route change. Missing provider cost is unavailable, never authoritative zero.

## Acceptance

- The reusable command loads the canonical skill under the invoking primary.
- Focused tests prove no private telemetry is placed in subagent prompts.
- Tool failure tests prove one optional failure does not cancel required local
  evidence.
- A/B activation requires no regression in gate failures, remediation, CI,
  escaped defects, or required-evidence availability.
