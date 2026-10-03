# One-time V2 control-plane transition

Status: Discovery contract; source implementation only. Risk: critical.
Profile: ../PROFILE.md. Owner: dotfiles maintainer. Modules: ML/AI, Security,
Python. Product-facing distribution outcomes remain in the existing distribution
Product Intent; this contract does not introduce another product or updater.

## Outcome and scope

Make the managed OpenCode control plane compatible with the exact latest V2
candidate selected for the one-time transition. Initial qualified research
candidate: 2.0.22. Candidate identity and limitations are recorded in the
Initiative's V2-TRANSITION-READINESS.md. Source baseline is merged PR 193.

Own OpenCode configuration, native agents/commands/skills, retained adapters,
TUI preference projection and their affected tests. Distribution owns trusted
binary installation, wrapper/package-lock compatibility, services, backups and
live activation. No hourly scheduler, Codex update redesign, automatic idle
upgrade or independent fleet rolling-update policy belongs to this slice.

## Contracts

1. Use stock V2 configuration and native permission enforcement. Retain configured
   role identities, provider affinity and Plan read-only restrictions. Validate
   resolved behavior, not just syntactically accepted configuration or key names.
2. Native API qualification must specify location[directory] and verify the
   returned directory. Role enumeration must wait for the complete expected set
   under a deadline. Empty startup results and a successful server start are not
   proof of configuration readiness. Query individual roles when bulk output is
   incomplete; do not parse truncated JSON as success.
3. Preserve credentials and unrelated machine-local configuration. Automated
   qualification uses isolated roots, synthetic providers and body-free results.
   It must not invoke hosted inference with operator history.
4. Preserve native-workspace and lifecycle CLI ownership from the shared contract.
   Do not restore the retired custom tool catalog, transparent routing or guessed
   actor/message/call identity. Initiative registration still requires exact
   interactive operator confirmation; Plan cannot register or mutate a cycle.
5. Trace each retained V1 adapter before changing it. Native global/project
   instructions must continue to require fresh committed Initiative authority and
   receipt validation, including after compaction. If a redundant automatic
   context-injection hook is retired, document its replacement by native
   instructions plus enforced CLI validation and verify that replacement. Do not
   silently retain an unloaded legacy plugin as purported authority.
6. Keep identity-dependent Incident/RND/federated operations explicitly unavailable
   as already specified. DKS remains disabled where managed configuration disables
   it; do not recreate a disabled tool through another transport. Any retained
   private-result route must preserve its bounded sanitized projection.
7. Preserve managed MCP integrations through the supported V2 configuration shape.
   Qualify native allow/ask/deny without returning secrets. Missing capability or
   unsupported integration is an explicit blocking result or a separately reviewed
   bounded gap, not a successful load.
8. V2 CLI preferences live in cli.json. Project the existing theme into the native
   structured theme setting without overwriting unfamiliar keys; Catppuccin with
   dark mode selects Mocha. Existing cli.json takes precedence over one-time legacy
   tui.json migration. Preserve V2 default Shift+Tab agent cycling unless the
   operator explicitly requests a remap; plain Tab remains autocomplete.
9. Source compatibility does not admit live sessions. Native TUI observations,
   Desktop/service/data-root behavior, per-platform qualification and history
   reconciliation remain rollout gates in the Initiative.

## Behaviors and acceptance

- Given the explicit task location, when roles are queried, all required roles
  resolve there with the intended model/provider and permission boundaries.
- Given a cold service or incomplete output, validation waits within a bound or
  refuses; it never treats missing roles as a valid minimal installation.
- Given Plan and a synthetic write/mutating shell request, mutation remains denied;
  the corresponding approved Build case proves the fixture can actually execute.
- Given a denied action, permission-key migration cannot turn it into allow; native
  ask cancellation performs no mutation. Compound shell commands remain covered.
- Given existing local preferences, projection preserves unrelated fields and
  produces the expected native theme without requiring a new update framework.
- Given unsupported legacy hooks, startup and documentation truthfully identify
  their replacement or unavailability rather than advertising missing tools.
- Given a source-only passing slice, production processes and history are unchanged.

Use existing pytest/Bun/rendering authorities, version-bound native smoke checks
and operator UI observations. Extend the affected control-plane/native permission
tests rather than installing a new QA framework. Record failed attempts and
unavailable checks. Kernel, Refactor, Review/Integrate and Maintain/Retire gates
are required; results remain pending. Release, Deploy and Operate are not
applicable to this source-only slice for the profile-bound reasons in the plan.
There are no Gate Exceptions.

## Visual Evidence

Boundary, interaction, state and data/trust: reuse the shared native-workspace
ownership and approval tables and the V2 migration flow, owned by the lifecycle
and distribution maintainers. Dependency/deployment: the Initiative slice table
is authoritative and changes with ownership/order. Schema: not applicable; use
the exact upstream candidate schemas rather than duplicating them. Quantitative:
not applicable; measured rehearsal results do not predict control-plane latency.
Text equivalent: source compatibility is validated in isolation; distribution
then qualifies and activates a coherent binary/configuration/service/data
generation. Source completion alone never admits production work.
