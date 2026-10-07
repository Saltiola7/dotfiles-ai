# OpenCode Rolling Stable

This Initiative removes the moving Homebrew formula from OpenCode runtime
authority and applies the delivered transactional Codex update pattern to
OpenCode-specific assets and semantic compatibility checks.

The original elevated-risk package slice established V1 rolling updates.
Its receipt does not authorize the critical-risk V2 migration described in
[V2 Migration](V2-MIGRATION.md). V2 qualification precedes implementation,
fleet cutover, and retirement; the approved contexts remain in this repository.

The original package migration targeted `1.18.29`. V2 candidate identity and
qualification are separate. Existing host and guest state remains isolated;
ordinary package updates never read provider credentials or session content.
The explicitly controlled V2 data migration operates boundary-locally and
retains original recovery evidence.

The [native workspace baseline](WORKTREE-BASELINE.md) replaces task allocation
and transparent continuation with Worktrunk, native sessions and lifecycle CLI
validation for OpenCode and Codex. Existing work adopts in place under explicit
operator confirmation. Initiative registration additionally requires interactive
confirmation of its fresh launch digest; agents prepare the command and resume
the registered cycle rather than supplying that confirmation themselves.

The [shared lifecycle contract](../../specs/dbsctr_v3_lifecycle/features/worktrunk-native-workspaces.md)
owns these interfaces and the operator handoff. Source readiness is separate from
host/Desktop/guest qualification and controlled rollout approval.

The [latest V2 transition record](V2-TRANSITION-READINESS.md) captures the current
one-time migration scope, staged candidate evidence and remaining qualification.
Periodic OpenCode/Codex updates and rolling-update policy changes are deferred;
they are not prerequisites for this transition.

PR 193 delivered the native-workspace source for both harnesses. Codex source
readiness was refreshed against native 0.155.1 with 99 affected tests passing.
PR 194 delivered the V2 control plane at merge `8124f163840c58e163df0cca0da9d2adfd00af5a`;
Python 3.12/3.13/3.14 CI and the CentOS smoke passed. These are source results,
not live deployment. The next bounded source contract is
[V2 distribution source](../../specs/dotfiles_ai_distribution/features/opencode-v2-distribution-source.md),
with its profile-bound OPENCODE-V2-DISTRIBUTION.plan.json. The
[distribution/recovery contract](../../specs/dotfiles_ai_distribution/features/opencode-v2-recovery.md)
retains the downstream implementation and live-admission requirements. Fresh
committed authority and a successful launch preflight are still required before
asking for exact implementation approval.

The operator requested continued delivery through live completion and explicitly
authorized merging passing transition PRs rather than stopping at draft delivery.
This does not replace exact digest-bound launch consent or writer-quiescence
evidence. Guest inventory is currently unavailable to the running primary because
its VM command permission is denied; resolve that before live fleet qualification.

## Visual Evidence

PR 195 delivered distribution source at `67aa5268969d44ec5374208339425512ff779a72`.
The next source prerequisite is native V2 session recovery: reject retained V1
identity as proof of V2 resume readiness. Its contract and plan are under
`docs/specs/dotfiles_ai_distribution/`. Both guests now have isolated Linux
artifact surface evidence; Desktop has archive/signature evidence. Neither is a
live rollout claim. See V2-TRANSITION-READINESS.md for current bounds.

Boundary, interaction, state, data/trust, schema, and deployment concerns are
owned by the V2 Migration specification, the shared native workspace contract
(including its approval handoff table), and the original rolling-stable feature
specification. Quantitative charts are not applicable: no measured V2
migration benchmark is available. Those specifications own accessible text
equivalents and must change when their represented contracts change.
