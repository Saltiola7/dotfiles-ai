# Shared global skill activation

Owner: distribution maintainers. Profile: [../PROFILE.md](../PROFILE.md).
Risk: elevated. Modules: Python, Shell, ML/AI, Security.

## Outcome and boundaries

OpenCode and Codex CLI/Desktop share one maintained source of global activation
policy. Ordinary requests use native model judgment. Skills offer relevant
guidance under operator control; DBSCTR supplies lifecycle orchestration after
explicit activation. Global instructions do not repeat that orchestration.

This feature changes activation policy, not the applicable DBSCTR gates or
evidence contract. It does not implement PR-Agent, replace local review with a
future service, change startup modes or permissions, activate DKS, or create a
handoff framework. Review skills remain available for ad hoc use. Existing
Review/Integrate obligations remain until the separate review work changes them.

## Ownership

| Concern | Canonical owner |
|---|---|
| Global activation policy | `.chezmoitemplates/agent-activation.md` |
| OpenCode global instructions | Native `AGENTS.md` rendered from that template |
| Codex CLI global instructions | The same template rendered into the existing managed source and projected by `codex-project` |
| Separately selected Codex Desktop home | Explicit local adoption of an instruction alias to the rendered managed source; preserve its previous file and leave other Desktop state alone |
| Lifecycle and automatic specialist selection | DBSCTR and its existing router |
| Requirements, contracts and approved scope ownership | Discovery and DBSCTR |
| Conversation and engineering style during DBSCTR | Canonical Caveman and Ponytail skills |
| Commit-message formatting | Caveman Commit, automatically selected whenever a commit message is prepared |
| Review procedure and merge authority | Existing review skill and native protections; separate review work owns future changes |
| Evidence privacy | DBSCTR policy and existing evidence/publication authorities |

Multiple required native destination files are projections, not independently
maintained instruction sources. No personal path, account, workstation exception
or fixed model selection belongs in the shared template.

## Behavior and activation state

| Given | When | Then |
|---|---|---|
| No workflow was activated | The operator asks for a bug fix and PR | Investigate, implement, test and deliver with ordinary judgment; relevance alone does not activate DBSCTR |
| A skill could materially improve the task | The agent recommends it | Wait for the operator's answer before activating it |
| A recommendation was declined | The task continues | Proceed normally and do not repeat the suggestion without material new circumstances |
| An explicit skill request or slash command | The skill is selected | Approval lasts for the conversation; retain relevant loaded guidance |
| DBSCTR was activated | Its router selects a dependency or specialist | Load the applicable skill without another activation prompt |
| DBSCTR is active | A small change leaves existing requirements stable | Reuse existing artifacts, read relevant sections and run applicable checks without redundant phase work |
| A commit message is needed | Any workflow prepares it | Use Caveman Commit; formatting grants no staging, commit, merge or deployment authority |
| An OpenCode configuration contains the retired Ponytail plugin and another plugin | Managed configuration is reconciled | Retire the automatic Ponytail injector and preserve the unrelated plugin |
| A native instruction projection is rendered | Another supported client is rendered | Both receive the same activation policy |

DBSCTR stays active for the conversation together with its selected skills. No
new off command, conversation registry or orchestration layer is introduced.
Reuse never substitutes for revalidation after material source, policy or
environment changes. Preserve gate applicability and evidence requirements.

## Rule disposition

| Existing global material | Disposition |
|---|---|
| Automatic lifecycle triggers | Replace with operator-controlled activation |
| Lifecycle phases, QA, typing, Gate Commits and Final Push | Keep with DBSCTR/QA and remove global repetition |
| Initiative readiness and scope ownership | Keep with Discovery/DBSCTR; remove implicit dependence on global prose |
| General DVC and workspace preservation | Keep with existing lifecycle/native owners |
| Detailed session-move handoff protocol | Remove and repair dangling references; no replacement framework is introduced |
| Personal/custom-path and version-specific exception prose | Remove from portable prompts; native enforcement remains independently owned |
| DKS-first routing and lifecycle migration history | Remove from active global instructions |
| Caveman/Ponytail defaults | Select once within activated DBSCTR |
| Legacy per-phase commit formatting | Use current Gate Commit rules and canonical Caveman Commit formatting |
| Global Caveman Review trigger | Remove; review orchestration is deferred |
| Plan/Build advice and provider-specific global prose | Leave native controls and applicable skill references as owners |

## Evidence and privacy contract

Cycle records and retained allowed sidecars remain in the common Git directory's
private `dbsctr/` storage. Unclassified output remains withheld by existing tools.
Plans and deliberately retained scratch diagnostics use verified ignored or
external private storage. Public commits contain checked summaries and relevant
reproducible tests. Gitignore is not redaction and does not authorize model or
service disclosure. Reuse existing publication authorities; do not add a second
evidence store or claim that a prompt alone enforces privacy.

## Distribution and compatibility

Preserve canonical upstream skill attribution, licensing and immutable import
provenance. Package only the selected skill resources, not upstream hooks that
inject instructions outside the approved activation path. Native instruction
templates remain wrappers around the shared source. The existing Codex projector
retains its config, manifest and collision protections.

An explicitly selected Desktop home may use a reversible alias to the rendered
managed instruction source. Back up its existing instructions before adoption;
verify source/target identity, alias resolution and content equality. Do not
change Desktop authentication, configuration, sessions or managed CLI ownership.
Do not silently overwrite divergent installed skills during rollout.

Existing conversations may already contain earlier prompts. Qualify fresh native
sessions; do not claim that file replacement removes their existing context.

## Validation and delivery

Use existing publication/instruction tests plus affected rendering, configuration
merge and distribution tests. Exercise projection equality, unrelated-plugin
preservation, canonical skill resources, and the existing projector's collision
and idempotency behavior. Evaluate independent activation cases, including an
ordinary task, an accepted/declined recommendation, explicit DBSCTR, conversation
continuation and commit formatting. Static wording checks are not proof of
model behavior; report the limits of native and model-based qualification.

Deliver source through a feature PR into the current protected base. Keep live
installation separate from source delivery. After main merge, apply only the
reviewed local instruction, configuration and skill targets, preserve preimages,
verify bytes and idempotency, and record the rollout result privately. No package
or provider update, shared-cache collection, branch deletion or unrelated service
restart is part of this feature.

## Local adoption and recovery

Use the dedicated dotfiles-ai chezmoi configuration and an explicit merged source
checkout. Preview only the instruction projections, selected skill bundle files
and retired Ponytail plugin entry. Exclude scripts during the scoped apply;
unrelated installers, providers, startup settings and services are not rollout
targets. Compare the proposed configuration structurally with the live file and
preserve unrelated settings and plugin entries.

Before writing, retain private preimages, modes, resolved targets and source
identities. Investigate divergent installed skills instead of replacing unrelated
work. Project the managed CLI instructions through the existing owner manifest;
do not bypass its collision checks. Adopt a separately selected Desktop home only
after checking its existing instruction file, then verify its alias resolves to
the reviewed rendered source. Keep authentication, sessions and other home files
unchanged.

Verify projection equality, selected skill file hashes, native skill discovery
and fresh native instruction loading. A second scoped apply must produce no
changes. Retain source revisions and private rollback preimages; restore only
owned rollout targets if verification fails. Do not remove shared caches,
installed upstream packages, branches or retained cycle evidence as cleanup.

The immutable style inventory records supported imports and licenses. Future
updates requalify the selected bundles and native discovery rather than silently
following an upstream default branch. Retirement of the old global prose does
not retire native safeguards or the existing review process.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: Ownership table identifies operator, clients, lifecycle and native authorities |
| Interaction | required: Behavior table specifies recommendation, approval, routing and delivery order |
| State | required: Behavior table defines inactive, approved and declined activation outcomes |
| Data/trust | required: Evidence and privacy contract defines private retention and checked public output |
| Schema | not_applicable: no new persistent schema is introduced |
| Dependency/deployment | required: Ownership and distribution sections identify shared-template projections and explicit Desktop adoption |
| Quantitative | not_applicable: no measured token, speed or cost improvement is claimed |

Text Equivalent: the tables and adjacent prose are the editable canonical
evidence. Maintainers update them when activation, ownership, privacy or
distribution contracts change; native projection files contain the policy only.
