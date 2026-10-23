# Retirement recovery amendment

## Approved intent and source evidence

Operator approved all three repairs: record-only non-success retirement,
disposition-aware removal, and lifecycle reachability across migrations. Approved
existing context map in dotfiles-ai: lifecycle owns state/preservation/tests,
OpenCode owns guided native journey, distribution owns coherent activation and
one nominated real-cycle recovery. No independent agents or cycles launched by
Discovery. Stable intent coverage is INT-061 onward in MANIFEST.json.

Operator subsequently approved a distinct narrow prerequisite source repair,
[effective Initiative authority amendment](../../specs/dbsctr_v3_lifecycle/features/initiative-authority-amendment.md),
covered by INT-077..080. Its source plan is pending fresh validation and launch,
not a claim that `initiative-amend` exists or is deployed. Preserve the blocked
original retirement cycle, original receipt/approval/import/commits and failed
evidence. Do not replace, re-register or silently relabel it. The new slice supplies
the mechanism only; separately approved merged installation and exact real-cycle
amendment are later actions, with independent native permission repair. It cannot
amend its own bootstrap authority. Existing checkpoints below remain historical.

Baseline source: `3d2bc366dce40b2dd127dca2bfcaa278eef983b4`. Source inspection
confirmed unconditional retirement-command rejection, narrow branchless orphan
recovery, old retirement coupled to raw Git deletion, native registrations with
`created_by_dbsctr=false`, ancestry-based removal, consumer refusal and unavailable
strict automatic capabilities. `tests/test_dbsctrctl.py` tests command refusal,
not replacement non-success reachability. These are source facts, not independent
verification of a private incident, installed runtime or stash equality.

## Decisions

| Decision | Approved contract |
|---|---|
| Non-success intent | `superseded` with optional successor, `cancelled` without successor, `empty` only with no-work proof. Preserve successful completion separately. |
| Logical closure | Separate from archive/removal; preserve failures, dirty files and uncertainty. Operator asserts writers stopped; idle read-only/MCP consumers do not prevent record closure. |
| Git retention | Verified durable local archive refs and private evidence outside checkout suffice for explicitly non-delivered disposition; no remote publication required, no disk-loss guarantee. |
| User consent | Exact preview plus interactive terminal or chat approval with agent-confirmed assertion; fresh recheck, no fabricated native actor proof. |
| Dirty/ignored data | Exact inventory and approved regular-file capture only; unknown/unsupported/changing files retain checkout, DVC rules remain independent. |
| Dirty preparation | Separately approved restore of archived tracked paths to HEAD and deletion only of exact archived untracked/ignored regular files; no reset, force, hook bypass or unlisted deletion. |
| Usable manual path | Qualify manual removal independently of unavailable automatic ownership/policy capabilities, preserving native permission, process, reservation and artifact checks. |
| Completion | Include merged source, installed qualification and one nominated-cycle recovery with fresh approvals; no bulk retirement or assumed consumer shutdown. |
| INT-074 — writer classification | Updated CLI writers share locks; held locks or positively identified live writers block closure. Unfinished historical intervals alone remain uncertain, and optional/missing history never proves inactivity. Explicit operator quiescence assertion remains required. |
| INT-075 — operational compatibility | Stop old writers and keep incompatible clients out before closure. Updated clients enforce terminal records; distribution qualifies compatible tools and rollback reader. No universal fencing or new identity/liveness service. |
| INT-076 — exact replay | Retain original approved digest and verified original-byte preimage/custody. Validate original intent and terminal record as original plus exact approved metadata; only pointer_status may reconcile. Initial pointer conflict refuses; post-terminal reassignment retains pointer, reports recovery_required and blocks registration. Prepared evidence is a private sidecar, never partial active-record metadata. Preserve genuine completed history/counts; retirement creates no success. |

This amendment narrows prior completed/merged-only predicates for explicitly
approved administrative dispositions. Original recorded authority and delivery
results are retained; new exact consent authorizes new administrative effects.
Automatic cleanup remains unqualified. Merely changing `state` to retired does
not make a checkout removable.

## Separate captured ordinary Git reachability

[Ordinary Git reachability](GIT-REACHABILITY.md) captures INT-081/082: normal tracked
deletions and same-repository side-branch integration must work without losing
absence semantics, incoming-closure accountability or gate evidence. Primary's
source inspection/disposable local probes found staged-deletion path rejection
and ordinary final-push accounting that cannot account incoming side-parent
commits merely by recording the merge commit. Approved-default reconciliation
already has a supported special path; not all merges are broken. No live target
cause is verified, and no live cycle/remote was touched by those probes.

`ordinary-git-reachability` remains captured, non-ready and Discovery-owned,
depending only on safety-inventory. Authority/import interface, tracked-absence
representation and already-recorded-merge recovery remain unresolved. This is
not implementation scope for the ready authority-amendment slice and adds no
dependency to it. No arbitrary ahead commits, patch-equivalence inference,
unvalidated gate success, live auto-closure, history rewrite or DVC/remote-consent
bypass is authorized. The original retirement remedy source scope stays unchanged.

## Serial delivery, ownership and gates

| Slice | Owner / dependencies | Writable implementation closure |
|---|---|---|
| `cycle-authority-amendment` (prerequisite, specification ready) | lifecycle; safety-inventory | `dot_local/bin/executable_dbsctrctl`; new `tests/test_initiative_authority_amendment.py`; existing `tests/test_initiative_cli_approval.py`, `tests/test_initiative_local_launch.py`, `tests/test_native_workspace_records.py`, `tests/test_worktrunk_registration.py`, `tests/test_dbsctr_forgejo_identity.py`, `tests/test_dbsctr_forgejo_completion.py` as necessary; lifecycle README/CHANGELOG completion notes. No helper configuration source. |
| `cycle-record-retirement` (P0, captured pending prerequisite) | lifecycle; safety-inventory, cycle-authority-amendment | `dot_local/bin/executable_dbsctrctl`; `tests/test_cycle_retirement_recovery.py`, `tests/test_dbsctrctl.py`, `tests/test_workspace_adoption.py`, `tests/test_orphan_workspace_recovery.py`, `tests/test_native_workspace_execution.py`, `tests/test_native_workspace_records.py`, `tests/test_worktrunk_registration.py`, `tests/test_dbsctr_forgejo_completion.py`, `tests/test_dbsctr_forgejo_identity.py`, `tests/test_dbsctr_forgejo_local_safety.py`; record closure, readers, pointer reconciliation and CLI reachability only. |
| `cycle-disposition-removal` (P1) | lifecycle; cycle-record-retirement, merge-cleanup | Same CLI and journey test; `dot_local/bin/executable_agent-worktree`; `tests/test_workspace_remove_check.py`, `tests/test_agent_worktree.py`, `tests/test_native_dvc_removal.py`, `tests/test_native_workspace_records.py`, `tests/test_dbsctrctl.py`; archive/capture/restore/preparation and approved manual removal. |
| `cycle-retirement-journey` (P1) | OpenCode; both lifecycle slices | `private_dot_config/opencode/AGENTS.md`, `.chezmoitemplates/opencode.json.tmpl`, `dot_agents/skills/dbsctr/SKILL.md`, `dot_agents/skills/discovery/SKILL.md`; control-plane/lifecycle/native permission/projection tests named in journey contract. No new control-plane engine. |
| `cycle-retirement-rollout` (P1) | distribution; all three source slices | Existing managed installation targets only after exact rollout approval; private qualification/recovery evidence and distribution completion notes. Existing distribution tests may add qualification coverage; new installer/infrastructure requires reopened readiness. |

Reachability is required acceptance in both lifecycle slices and installed rollout,
not a detached test-only slice deliverable after broken entry points ship. Core
source uses CORE-SOURCE.plan.json, journey CONTROL-PLANE-SOURCE.plan.json, rollout
RETIREMENT-ROLLOUT.plan.json. Existing Profiles unchanged; overrides are critical
risk, these exact paths, Python/Security plus ML/AI guidance, macOS-first live
qualification, feature-branch/draft PR source delivery and separately approved
installed recovery. All gate results pending, no exceptions. Source release,
deploy and operate are reasoned not_applicable; rollout deploy/operate required.

Build owns implementation/completion evidence only. Discovery owns normative
scope, transitions, interfaces and dependencies. Serialize shared CLI/test/skill
edits. Each source slice runs affected QA and critical review; no repository-wide
local audit without request. Configured GitHub CI remains authoritative.

## Validation and handoff

Run `dbsctrctl initiative-check --manifest
docs/initiatives/dbsctr-workflow-convergence/MANIFEST.json --json` after manifest
changes. Run configured publication/instruction tests over exact staged additions:
`uv run --group test pytest tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers
tests/test_opencode_control_plane.py tests/test_dbsctr_lifecycle.py -q`.
Use installed approved environment; do not install missing tools for Discovery.
Also validate JSON plans, Markdown links and whitespace. No source test result
qualifies real deletion, native permissions or consumer shutdown.

The new prerequisite source slice imports the complete changed-document closure
(18 existing retirement artifacts plus the new feature and captured Git
reachability note, 20 declared artifacts)
enumerated in its manifest. Profile remains unchanged. Primary must compare the
actual unmerged changed-document set to this closure before receipt/preflight;
enumeration is not proof of source checkout membership or complete Git custody.
`GIT-REACHABILITY.md` is included only as captured Discovery evidence needed for
the branch-wide document closure, not writable source authority or implementation
inclusion for the ready amendment slice. The unfinished slice has no launch receipt.
Later retirement readiness remains captured until dependencies and the exact
real-cycle effective-authority route are freshly verified. Historical first-slice
bootstrap guidance follows, subject to that prerequisite.

First slice imports the complete changed-document closure enumerated in its
manifest artifacts. Keep this committed Discovery checkout/ref. Current begin
requires clean Build HEAD at approved base; use one code-only Worktrunk checkout
and import authority through native Initiative route, never reset Discovery or
publish a preliminary docs PR just to satisfy launch. Fresh receipt/preflight and
exact scope/risk/target/digest approval required immediately before registration.
Recommended primary: existing Build agent with session-selected provider; no new
independent slice session or cross-provider fallback.

The bootstrap description above applies only where current CLI admission actually
permits it; it does not authorize re-registering an existing registered cycle or
establish an amendment/renewed-launch CLI route. Review found generic classification,
compatibility and replay gaps, settled normatively by INT-074..076 without changing
slice scope or dependencies. Preserve previous failed evidence and original
authority-import/cycle history. This source amendment requires fresh validation,
readiness and exact approval of the changed plan; actual supported current CLI
continuation remains for primary verification. This amendment establishes no gate
pass; the checkpoints below distinguish prior evidence from fresh primary validation.

Specification readiness does not establish launch feasibility or activation.
Private nominated identity and exact installed/consumer state are runtime inputs
to rollout preview, not public specification holes. Unsupported file metadata,
data backend or native shutdown remains a truthful blocker; any needed expansion
returns to Discovery rather than weakening preservation.

### Discovery validation checkpoint

Native `initiative-check` accepted 73 statements, three contexts, 15 slices and
four release groups, with `cycle-record-retirement` dependency-satisfied. All 17
changed documents are in its declared import closure; 105 local Markdown links
resolved, three referenced applicability plans passed structural checks, and
staged whitespace validation passed. Existing context changelogs were reviewed;
no implementation/completion entry is added by Discovery.

Required publication/instruction test authority is **unavailable**, not passed:
the offline/no-sync configured uv invocation could not spawn pytest. Available
Python 3.12 and 3.14 also lacked pytest. No package was installed; the attempted
uv invocation left an empty ignored environment in the Discovery checkout.
Retain this failed evidence. All 17 candidate documents await the configured
publication check; source receipt, publication and launch readiness remain blocked
until an approved existing test environment runs it successfully. The manifest's
ready state denotes settled specification/dependencies only. No receipt, Build
preflight, lifecycle registration, deployment or live retirement was performed.

Subsequent operator-authorized environment provisioning resolved this validation
blocker: `uv sync --frozen --group test --python python3.14` installed the existing
locked test group without changing dependency metadata. Python 3.14.9 / pytest
9.1.1 ran the configured publication/instruction checks: **89 passed, 1 skipped**.
The skip is the explicitly unselected native V2 test binary, not a publication
failure or native runtime qualification. Earlier unavailable evidence remains
above. This clears the test-environment blocker; exact Build preflight and
plan-specific launch approval remain separate prerequisites.

### INT-074..076 amendment validation checkpoint

Primary reported fresh native `initiative-check` success: 76 statements, three
contexts, 15 slices and four release groups. Primary also reported configured
publication/instruction checks: **89 passed, 1 skipped**; the skip remains the
explicitly unselected native V2 binary, not native runtime qualification. These
results supplement, not replace, the earlier failed and passing evidence above.
They do not establish launch readiness or a lifecycle gate outcome.

Primary source review found `--resume-existing`, but
`check_initiative_cycle_occupancy` requires the exact identical recorded receipt
(helper lines 4661–4662), and is called before preflight (line 5334); resume also
revalidates `record.initiative` equality (line 5408). No active-cycle changed-receipt
amendment operation was found. Continuation feasibility therefore remains unresolved
pending an exact current CLI check after the amended authority is committed and
its fresh receipt is available. Preserve the recorded receipt, previous failed
evidence and original import/cycle history; do not relabel authority or infer a
new continuation route. Fresh readiness and exact approval of the changed plan
remain required, independently of whether the current CLI can admit it.

### INT-077..080 prerequisite handoff (not validation evidence)

The current source lacks a supported changed-receipt operation; the new contract
specifies one rather than pretending `--resume-existing` can admit changed
authority. Preserve its exact-match rule against validated effective authority.
Bind committed same-repository docs/blobs/modes, owned checkout/branch/HEAD/index,
unrelated dirty inventory/content and private original bytes; do not mutate Git,
fetch, access credentials or auto-import. Append a validated versioned amendment
chain with exclusive fsynced immediate-pre-amendment preimage, hash-bound owned
private full-plan envelope and separate deterministic replacement outcome (no
recursive postimage hash). The feature defines exact version-1 entry fields and
fixed consent time. Reopen required gates and remove current evidence AND
exception fields without erasing ledger/failures/exception history. IDs in the
latest preimage ledger cannot dispose reopened gates: require newly executed
evidence even at unchanged HEAD, enforced by gate setter, Gate Commit, completion
and final push. One recorded ordinary Gate Commit must establish the entire
selected path/blob/mode closure, including already-identical files without staging
them. Completion/final push revalidate effective closure at HEAD; original
discovery_import and existing evidence path-set checks remain intact. Material
normative drift requires fresh Discovery/amendment; editorial remediation requires
explicit existing scope authority and recorded exact validation.
Risk/profile/applicability/delivery stay unchanged; changes use existing routes
before fresh preflight. Exact terminal `AMEND ID SHA` or exact chat assertion is
new live consent, never inferred from this approved source plan.

Bounded result statuses/exits are `preflight`/`applied`/`already_applied` (0),
`blocked` (1), `recovery_required` (75). Preflight state_digest is the actionable
approval launch digest; invalid selection without trustworthy digest yields null.
Optional status amendment summary exposes only version/count/effective receipt
digest/latest launch digest, preserving original public-compatible fields. Never
emit exact new reason, private locators or raw envelope to hosted channels.

CORE-SOURCE plan and existing Profile apply unchanged: critical Python/Security;
all kernel gates, Review/Integrate and Maintain/Retire required; source Release,
Deploy and Operate not applicable for their existing source-only reasons. Results
are pending. Test registration -> failed evidence -> amend -> status -> resume;
concurrency, stale approval, lost reply, denied/no-mutation, chain/schema 3/4/5/6
compatibility, retained failures, final-push lineage and schema 6 local completion
replay/no-network. No historical checkpoint qualifies these new paths.

Primary verification still required: native `initiative-check`, publication/
instruction authority including the new file, JSON/link/whitespace checks, actual
changed-document closure, fresh receipt and launch preflight. This docs helper has
no native shell route and ran none of those commands; no new check or gate pass
is asserted. No material contract question remains from the approved selection;
runtime feasibility, installed compatibility and exact real-cycle approval remain
separate evidence/authorization blockers, not assumed success.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: serial ownership table above |
| Interaction | not_applicable: lifecycle/journey contracts own ordered effects |
| State | not_applicable: lifecycle transition table is canonical |
| Data/trust | not_applicable: lifecycle archival and distribution private evidence contracts are canonical |
| Schema | not_applicable: machine manifest and feature field contracts own shapes |
| Dependency/deployment | required: serial ownership table above |
| Quantitative | not_applicable: no measured latency/storage claims |

**Text Equivalent:** Lifecycle first delivers the narrow authority-amendment
source mechanism with no live mutation or self-amending bootstrap. Separate merged
installation and exact live-cycle consent precede renewed retirement readiness;
the original blocked cycle and failed evidence stay intact. Lifecycle then restores
non-success record closure and its
reachability tests, then archival/manual removal. OpenCode exposes the supported
journey after both interfaces exist. Distribution qualifies the installed set and
one separately approved real recovery, including compatible tools/rollback reader.
Closure requires shared-lock/live-writer checks, explicit quiescence and operational
old-writer/incompatible-client exclusion. Uncertain history is not liveness or
inactivity proof. Original-digest replay validates preimage, custody, intent and
exact terminal outcome; only pointer_status reconciles, with reassigned pointers
retained and registration blocked. Prepared sidecars leave active records intact;
genuine completed history remains. The original automatic-cleanup blockers
stay intact. Source: manifest and this handoff; owner: Discovery primary; revisit
on ownership, dependency, scope or installed-capability changes.
