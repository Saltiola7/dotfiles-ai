# Codex native workspaces and lifecycle CLI

Status: specification reconciliation; not deployment qualification.
Owner: project maintainers. Profile: `../PROFILE.md`. Risk: critical.
Authority: OpenCode rolling-stable Initiative INT-027–INT-030 and the shared
`docs/specs/dbsctr_v3_lifecycle/features/worktrunk-native-workspaces.md` contract.

## Behavior and boundary

Codex CLI uses its native cwd, sessions, sandbox and approvals in a Worktrunk task
checkout. Skills invoke the same dbsctrctl CLI as OpenCode. Remove task allocation,
root-target redirection and continuation receipt/admission orchestration; never
add an MCP replacement or a second lifecycle implementation.

Preserve the managed CODEX_HOME boundary, native login, provider affinity,
release-lock validation, rolling updater and unrelated supported history hooks.
Codex Desktop is not managed by this change. Do not read undocumented session
databases or infer native call identity from arbitrary arguments/environment.
Missing attribution remains unavailable. Plain CLI execution does not require a
manufactured native receipt.

Initiative registration follows the shared INT-031 interactive CLI confirmation
contract. The agent prepares preflight and hands the exact registration command
to the operator, then resumes the registered cycle. Do not simulate a terminal,
supply confirmation on the operator's behalf, or treat general shell permission
as exact Initiative consent. Ordinary registration is not made interactive by
this additional Initiative boundary.

Existing active worktrees follow shared operator-confirmed adoption, in place,
with original cycle IDs and failed/uncertain evidence intact. The launch-time
busy check covers managed foreground launches only, with explicit operator
override and no security-boundary claim. Native permissions remain enforced.

## Source ownership and retirement

Review `executable_codex-continuation` and its probe as retirement candidates for
task orchestration. Review consumers before removal. Keep the independent
`codex-control-plane` SessionStart/SessionEnd/Subagent/Stop hooks when required
for retained history or identity capabilities; their presence is not a reason to
retain continuation. Update managed role/skill guidance, capability reporting,
installer/requalification checks and tests together. An intentionally retired
capability is not reported as a native-probe failure or restored by rollback of
an unrelated package update.

The shared lifecycle helper, not Codex-specific code, owns evidence/gate/delivery
validation. Remove stale invocations from Herdr/Hermes/worker paths where they
launch task sessions. Any dependent autonomous behavior lacking safe native
permission semantics is explicitly unavailable, not silently elevated.

## Acceptance

- Native cwd is the selected task checkout; another checkout's branch is unchanged.
- Both allowed and denied native commands obey the configured sandbox/approval mode.
- Lifecycle registration, evidence, gate progression and PR delivery work through CLI.
- No new native task requires continuation enrollment, native receipts or root routing.
- Current attribution is unavailable unless independently verified; old receipt data
  remains historical and cannot authorize current commands.
- State-root failures preserve existing fail-closed startup behavior.
- Migration keeps original cycle IDs, dirty work and failed gates; background work
  is not declared stopped merely because the foreground CLI exited.

Use selected pytest, rendered configuration and native boundary-local smokes.
Source tests do not qualify host/guest rollout. No provider requests with private
history are authorized by specification work.

## Visual Evidence

Boundary/state/interaction: use the shared native-workspace contract's ownership
flow, adoption table and approval handoff table with their Text Equivalents. Data/trust, schema,
deployment and quantitative visuals are not applicable here: this delta adds no
independent protocol, data store, deployment topology or quantitative claim.
