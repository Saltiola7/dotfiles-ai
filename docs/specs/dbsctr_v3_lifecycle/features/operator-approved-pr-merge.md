# Operator-approved single-PR merge

**Specification ready; implementation, launch and activation unverified.** Owner:
lifecycle Discovery primary. Context: `dbsctr_v3_lifecycle`;
[Profile](../PROFILE.md); risk: critical (merge authorization); modules: Security,
ML/AI. Initiative coverage: INT-053–INT-060. Delivery is source-only.

## Bounded policy change

Permit the primary session/agent to perform an authorized ordinary native GitHub
merge of one exact PR after actual applicable gates and CI/CD succeed. A human
GitHub GUI click is not required. This changes prompt instructions, not the CLI's
capabilities: `dbsctrctl check pr-review` remains a structurally blocked diagnostic;
supplied green JSON, a policy digest or a mocked test never authenticates evidence.
No new merger engine, CLI executor, automatic batch, repair/watch service or
qualification of autonomous automation is included.

This contract narrows the blanket native `gh`/API prohibition in the current
`dbsctr-pr-review` skill for this single-PR route only. It supplements
[workflow-integration-ci](workflow-integration-ci.md), without rewriting its
historical delivery or qualifying its broader admin/waiver/automation contracts.
For this route ordinary merge only and all required checks successful take
precedence over those broader options. No admin bypass or failure waiver applies.
Writing this specification does not activate the changed instruction policy.

Approved amendment (INT-060): standard native protected-merge semantics supersede
this route's original immutable-base consent and approved-base parent assertions.
Independent Build review reopened readiness on the approved-base SHA race. The
base is observed evidence, not an immutable consent boundary or atomic base CAS.
Historical INT-001–INT-052 and broader integration contracts are unchanged.

## Authorization and evidence

The primary must establish all of the following before mutation:

1. Explicit user authorization binds the exact repository, PR, head, target branch,
   ordinary merge-commit strategy and consequence, not an immutable base SHA;
   alternatively a separately qualified,
   unchanged exact-repository policy must independently cover that same action.
   A shell grant, general continuation, role label or configuration digest is not
   consent. Missing standing-policy qualification requires explicit authorization,
   not fabricated qualification. Helpers remain read-only evidence reporters.
2. Native authenticated GitHub reads establish repository/default/target identity,
   open non-draft PR, exact head and observed base, mergeability, permissions, required reviews,
   applicable protection/rulesets and CI producer/run/job identities. Native `gh`
   API reads are permitted by the future policy; caller-supplied JSON is not proof.
3. Trusted-base repository authorities establish the complete applicable check
   set, including affected dependency closure and required protections. Unknown
   scope needs conservative broad checks or blocks. Fresh authenticated results
   must be `success` for every applicable check on the exact tested head/base.
   Missing, skipped, neutral, cancelled, pending, failed, stale, unknown or
   unavailable required evidence blocks. Synthetic merge evidence requires
   verified ordered parents `[base, head]`; names alone prove nothing.
4. Where DBSCTR applies, inspect actual cycle records, required gate results,
   exact Gate Commits and their ancestry in the PR. CI alone is not cycle evidence;
   a changelog assertion alone is insufficient. A dependency-only or other
   policy-exempt PR needs an explicit documented exemption tied to inspected scope
   and the applicable policy; no synthetic cycle or retrospective gate pass.
5. Immediately recheck head, observed base and authority. Use the native exact-head guard
   (`gh pr merge --merge --match-head-commit HEAD`) for the exact repository/PR,
   only with verified strict current-base protections enforced by GitHub across
   the request, requiring successful applicable checks covering the actual current
   tested base/result. A fresh read plus head guard alone does not close the base
   race; if those protections cannot enforce current-base validation, block.
   Record observation times, observed base, tested object/parents, check identities
   and protection evidence. Reads prove state only at observation time, not atomic
   base CAS. Revalidate observed base advances against trusted scope/check authority
   and fresh CI; unchanged approved scope/protections need no renewed consent solely
   for base advancement. Changed head, target, material intent or protections require
   renewed approval; other lost or unavailable authority blocks. Never reuse old
   base evidence as proof of a newly advanced base.
6. Request only an ordinary immediate merge commit: no `--admin`, `--auto`, squash,
   rebase, queue enrollment, direct default push, force, reset, deletion or cleanup.
   If native rules require an unsupported route, retain and report blocked. Do not
   request merge where automatic branch deletion would violate this route's
   retention boundary; do not change repository settings to bypass that boundary.
7. Query the remote outcome and inspect the returned merge object's two ordered
   parents: second parent must equal the approved head; first parent identifies the
   actual merged base, which need not equal the earlier observed base. Verify
   head/Gate Commit ancestry, intended-target inclusion and authenticated native
   checks covering the actual result/base through strict protections enforced at
   merge. If the base advanced between observation and request, reconcile that
   actual base and evidence; never retroactively equate old tested and new bases.
   Missing coverage or enforcement proof prevents a verified-merge claim even if
   GitHub reports merged; preserve the actual outcome and uncertainty. Uncertain results require
   read-only reconciliation before any retry, never a guessed second mutation.
   Keep credentials, private records and raw logs outside public Git.

## State and acceptance

Single-PR state table: what permits each transition?

| From | Guard / event | To and required outcome |
|---|---|---|
| Reviewed | Exact authorization and every fresh applicable gate, CI and native guard proven | Eligible; primary may request ordinary guarded merge without GUI |
| Reviewed / eligible | Missing authorization, failed/unknown/unavailable required evidence, unsupported protection | Blocked; retain PR, refs and work, report exact gap |
| Eligible | Observed base advances, approved scope/protections unchanged | Reviewed; refresh scope and CI evidence without renewed consent solely for base advance |
| Eligible | Head, target, material intent or protections change | Reviewed; discard stale evidence and renew approval |
| Eligible | Other authority lost or unavailable | Blocked; retain work pending fresh proof |
| Eligible | Guarded native request returns | Unverified outcome; query remote, do not claim merged |
| Unverified outcome | Second parent equals approved head; actual first-parent base, protected check coverage, target inclusion and gate ancestry verified | Merged; retain branch/worktree, no implicit activation |
| Unverified outcome | Timeout, mismatch or incomplete proof | Blocked/uncertain; read-only reconcile before retry |

**Text Equivalent:** Review and bind authorization first. Only fresh real gates,
authenticated CI, exact-head guard and strict native current-base protection permit
the primary's merge request. Observed base advancement requires fresh scope/CI
validation, not new consent alone; head, target, material intent or protection
changes require renewed approval. Lost authority or negative evidence blocks.
A request is not success: verify approved head as second parent, actual merged
base as first parent, protected check coverage, target inclusion and gate ancestry.
Observation is not atomic base CAS; reconcile advances and uncertain outcomes
without relabeling old evidence. Every state retains branches/worktrees. Canonical source: this contract;
owner: lifecycle Discovery primary; update table and equivalent together when any
guard, authority or outcome changes.

## Build handoff and validation

Append-only slice `operator-approved-merge-policy` depends on delivered
`integration-review` and `ci-contracts`; those source deliveries do not establish
live merge qualification. Recommended exact writable Build scope, subject to
preflight approval: `dot_agents/skills/dbsctr-pr-review/SKILL.md`,
`dot_agents/skills/dbsctr/SKILL.md`, `private_dot_config/opencode/AGENTS.md`,
`private_dot_config/dotfiles-ai/codex-managed/AGENTS.md` only if the duplicated
rule needs reconciliation, affected existing instruction tests
(`tests/test_dbsctr_lifecycle.py`, `tests/test_opencode_control_plane.py`,
`tests/test_codex_control_plane.py`, `tests/test_dbsctrctl.py`), and
`docs/specs/dbsctr_v3_lifecycle/CHANGELOG.md` for completion evidence only.
No CLI/source implementation, new schema, CI refactor or consumer change.
Normative specification/manifest scope remains Discovery-owned; material Build
findings return `readiness_reopened`.

Primary verifies instruction consistency and negative cases: absent authorization,
forged green JSON, missing cycle evidence, unjustified exemption, stale head/base,
unenforced current-base protection, non-success checks, admin/auto/delete requests,
and uncertain outcomes must not permit merge. Positive instruction coverage must
allow the authorized ordinary native route without claiming automation qualified.
Include the race case: a base advance with unchanged scope/protections and fresh
successful native current-base checks does not itself require renewed consent;
an unproven actual merged base/result must never inherit old green evidence.
Run affected repository-selected tests, publication/privacy authority on the full
three-document candidate inventory, `git diff --check`, and `initiative-check`.
These are verification requirements, not results recorded by this document.

[OPERATOR-MERGE.plan.json](../../../initiatives/dbsctr-workflow-convergence/OPERATOR-MERGE.plan.json)
requires all kernel, Review/Integrate and Maintain/Retire gates; results pending,
no exceptions. Release, Deploy and Operate are not applicable to source-only
delivery, not passed. Do not require activation of unmerged instructions to merge
their source PR. Installation/activation of newly merged skills is explicit later
work with applicable runtime gates and fresh qualification; no current-policy
activation is inferred. Before Build registration the primary must validate the
manifest, obtain a fresh slice receipt, run exact future Build preflight and obtain
explicit approval for its scope, critical risk, target and launch digest.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary | not_applicable: authorization prose identifies primary, read-only helpers and GitHub authority without a redundant diagram |
| Interaction | not_applicable: numbered evidence sequence specifies authorization, checks, guarded request and outcome ordering |
| State | required: state table above; which evidence permits mutation or forces retention? |
| Data/trust | not_applicable: evidence prose distinguishes native authenticated results from untrusted supplied JSON and private records |
| Schema | not_applicable: no new persistent schema; existing lifecycle evidence remains authoritative |
| Dependency/deployment | not_applicable: Build handoff names delivered dependencies and separate later activation explicitly |
| Quantitative | not_applicable: no measured benefit or quantitative claim |
