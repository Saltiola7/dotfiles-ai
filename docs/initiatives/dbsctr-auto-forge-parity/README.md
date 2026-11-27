# DBSCTR Initiative Auto and forge parity

## Discovery status

The operator approved the context ownership below, one bounded approval for
selected Initiative slices, unattended continuation after a Build session closes,
and Forgejo merge qualification in an isolated protected homelab repository.
Implementation, deployment, and remote actions remain separate delivery steps
under the applicable lifecycle approvals.

DBSCTR has per-PR coordinated delivery on GitHub and a Forgejo local completion
route. The Forgejo adapters support pull requests, exact required CI evidence, and
protected merge. The deployed Forgejo merge API verifies the expected source head.
The qualified repository-scoped guard binds the merge to the tested base.

The first outcome is one approved Initiative delivered across its selected
slices with the same user-facing Draft PR and Auto choices on either qualified
forge. The operator can see progress, CI failures, and the next required action
per slice. Tempo remains a downstream consumer.

## Context ownership

| Bounded context | Home | Owns | Reads |
| --- | --- | --- | --- |
| DBSCTR Lifecycle | dotfiles-ai | Provider delivery, exact Initiative approval, continuation and delivery state, CI reconciliation, live tally | Activated preference and repository policy, approved specifications, native CI and forge evidence |
| Dotfiles AI Distribution | dotfiles-ai | Private TOML preference, configuration validation, rendering and activation | Existing coordinator mode and repository enrollment contract |

The forge and selected native Build runtime supply capabilities. Runtime changes
requiring a new owning context reopen Discovery. Native review, trusted checks,
branch protection, and operation authorization remain the acceptance authorities.

## Specifications

- [Delivery preference](DELIVERY-PREFERENCE.md)
- [Initiative Auto and CI recovery](INITIATIVE-AUTO.md)
- [Forgejo parity](FORGEJO-PARITY.md)

Use the existing [DBSCTR Lifecycle profile](../../specs/dbsctr_v3_lifecycle/PROFILE.md)
and [Distribution profile](../../specs/dotfiles_ai_distribution/PROFILE.md) for
stable runtime and policy defaults. Reuse [coordinated delivery](../../specs/dbsctr_v3_lifecycle/features/integration-coordinator.md),
[Forgejo local registration](../../specs/dbsctr_v3_lifecycle/features/forgejo-local-registration.md),
and [workflow integration CI](../../specs/dbsctr_v3_lifecycle/features/workflow-integration-ci.md)
as existing contracts. This Initiative has its own manifest so existing
Initiative digests and approvals retain their original scope.

## Slice and dependency plan

The [Initiative manifest](MANIFEST.json) records requirements, ownership and
dependencies. The delivery preference, Forgejo PR parity and Forgejo CI source
slices have landed on `main`. [Delivery preference PR](https://github.com/Saltiola7/dotfiles-ai/pull/347) ·
[Forgejo PR parity PR](https://github.com/Saltiola7/dotfiles-ai/pull/350) ·
[Forgejo CI parity PR](https://github.com/Saltiola7/dotfiles-ai/pull/351)

An earlier isolated v15 repository verified green and red statuses from a
separate CI identity. A restarted receipt reader accepted both exact results and
rejected missing, stale, and misattributed evidence. The guarded merge source
has landed with all required GitHub checks passing. The approved guard is
installed on the private test repository and passed the 31-case harness on
its native Git runtime. The live fixture passed eight cases, including a stale
competing merge and lost-response reconciliation.
[Forgejo merge source PR](https://github.com/Saltiola7/dotfiles-ai/pull/352)

Six of seven Forgejo-first delivery slices have met their acceptance criteria.
In the protected Forgejo continuation test on native Linux, slice A landed through independent
required CI and the ordinary guarded merge. The originating OpenCode session
closed before the controller restarted. The same grant and journal authorized
one first launch of dependent slice B from A's protected landing. Independent
readback verified both deliveries. This establishes installed Forgejo
continuation in the enrolled fixture.
[Initiative continuation source PR](https://github.com/Saltiola7/dotfiles-ai/pull/357) ·
[GitHub managed composition PR](https://github.com/Saltiola7/dotfiles-ai/pull/362)

CI recovery and tally has landed. Its approved contract covers one shared
repair for an in-scope source fix or a verified infrastructure retry on a
qualified target. It also covers a private read-only tally for progress,
evidence age, next action and budget. Installed Forgejo qualification comes
first. GitHub qualification remains a separate follow-up with its own
protected test repository and authorization.
[CI recovery and tally PR](https://github.com/Saltiola7/dotfiles-ai/pull/386)

| Slice | Depends on | Acceptance evidence |
| --- | --- | --- |
| `delivery-preference` | Existing workflow policy | Default Draft PR. Personal Auto and exact-task override resolve predictably. Existing enrollments and records still load. |
| `forgejo-pr` | Existing local Forgejo identity | Provider adapter and fixture coverage for draft and ready PRs, idempotent lookup, and exact head and repository identity. |
| `forgejo-ci` | `forgejo-pr` | Normalized candidate-bound CI evidence and diagnostic status, including incomplete and paginated results. |
| `forgejo-merge` | `forgejo-ci` | Protected isolated fixture proves ordinary-actor merge, stale-base rejection, and lost-response reconciliation. |
| `initiative-continuation` | `delivery-preference`, `forgejo-merge` | One exact grant and two dependent slices delivered through protected private Forgejo. Close the originating session and restart the controller before the second launch. Verify durable dispatch and material drift handling. |
| `ci-recovery-and-tally` | `initiative-continuation`, `forgejo-ci` | One shared repair for qualified source or infrastructure failures, fenced rechecks and actionable stall evidence, and one read-only text and JSON tally. |
| `auto-qualification` | `forgejo-merge`, `ci-recovery-and-tally` | Qualify the current installed release on private Forgejo and native Linux. Verify protected continuation, one shared attempt for a qualified repair class, fresh CI, and private status readback. |
| `github-auto-qualification` | `auto-qualification` | Deferred. Verify installed Auto on a separately enrolled protected GitHub target. |

Work on the preference and Forgejo adapter is independent at the contract level.
Build must serialize edits to shared lifecycle entry points and tests. A
repository still needs exact enrollment and a qualified capability record for
live delivery.

Tempo changes, a mandatory Forgejo upgrade and promotion of Dagger to a required
check are outside this Initiative. Provider qualification verifies whatever
required CI the target has already approved.

## Build handoff

- **Risk.** Preference behavior is elevated. Any live unattended publication
  or protected-base merge is critical.
- **Delivery intent.** Review and test managed source in a linked checkout.
  Qualify remote actions separately in protected fixture repositories.
- **Validation.** Reuse the workflow policy, Initiative registration, provider
  adapter, coordinator, and CI repair test suites. Native fixture evidence is
  required for production claims about forge behavior, CI, restart recovery,
  and protected merges. Run the repository publication checks for the exact
  source set before receipt or promotion.
- **Gates.** The development kernel and Review/Integrate apply to every Build
  slice. Release, Deploy, Operate, and Maintain/Retire apply where a slice
  qualifies or activates installed or remote behavior. Record applicability
  and actual gate evidence in each scope-specific plan.
- **Readiness.** The manifest records Discovery decisions and dependencies.
  Promotion requires stable committed specification authority, evidence for
  required prerequisites, fresh receipt and preflight, and the current
  applicable approval. An isolated fixture can establish a capability. Any
  production enrollment requires its own verified authority.
