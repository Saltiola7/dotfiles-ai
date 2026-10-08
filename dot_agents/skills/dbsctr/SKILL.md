---
name: dbsctr
description: Deliver behavior and downstream-visible changes through the DBSCTR V3 development kernel and every applicable review, release, deployment, operations, maintenance, and retirement gate.
trigger: /dbsctr
---

# DBSCTR V3

## Outcome

Deliver the requested change through a language-neutral Development Kernel—
Domain, Behavior, Spec, Contract, Test-driven implementation, and Refactor—then
evaluate Review/Integrate, Release, Deploy, Operate, and Maintain/Retire. No gate
is skipped silently.

Use DBSCTR for behavior, domain, schema, API, service, pipeline, orchestration,
validation, contract, or downstream-visible changes. Skip trivial, formatting,
git-only, dependency-only, or non-behavioral configuration work unless invoked.

## Start

1. Read project instructions, matching specs/ADRs, configured validation, and
   relevant source. Reuse existing artifacts.
2. Check an existing Graphify graph before broad search; verify useful results
   against source and fall back when stale, weak, or irrelevant. Update it only
   when explicit project policy requires an update.
3. Verify the bounded-context Engineering Profile. Run `discovery` when an
   unresolved question can materially change scope, behavior, interfaces,
   safety, delivery, or validation.
4. Record current affected scope, risk, delivery intent, applicable modules, and
   required capabilities.
5. Report Method Revision `3.29` (older V3 records remain readable). Use
   `dbsctrctl status` in the explicit native checkout to resume its Cycle Record.
   Worktrunk owns task checkout creation and navigation; start a native OpenCode
   or Codex session there. A shell directory change does not retarget a session.
   For new work, create a JSON applicability plan under the checkout's ignored
   `.dbsctr/plans/`, bound to the committed Engineering Profile. Use
   `dbsctrctl begin --plan PATH` to register the prepared clean linked checkout;
   it does not allocate a worktree or switch branches. Primary checkouts are
   navigation contexts, not implementation targets. Legacy cycles require
   separately confirmed in-place adoption before mutation. Create actionable
   todos; adjacent kernel concerns may share one item when evidence is compact.

## Progressive Modules

For an Initiative, issue a fresh `dbsctrctl initiative-receipt` and run
`dbsctrctl begin` with its Initiative arguments and `--preflight`. This validates
the exact launch plan without registering a cycle or collecting consent. Present
that plan's scope, risk, target and launch digest, then ask for explicit chat
approval. A Build primary may run the exact command with
`--expected-launch-digest DIGEST --approval agent-confirmed` after the user
approves that plan. This is caller-reported consent, not authenticated identity.
The default terminal path still accepts `BEGIN CYCLE_ID LAUNCH_DIGEST` from the
operator. Never synthesize that input, create a pseudo-terminal, or treat general
continuation or shell permission as plan-specific approval. The CLI rechecks
authority before mutation; changed state requires fresh preflight and approval.
Resume an already registered matching cycle without renewed registration consent.
Local same-repository Discovery does not need its own published upstream or
separate documentation PR for draft delivery.

Load only matching modules before Domain. Multiple modules may apply.

| Signal | Module |
|---|---|
| Python source, metadata, runtime, package, or service | `modules/python.md` |
| Elevated/critical security or sensitive-data impact | `modules/security.md` |
| Pipeline, ETL/ELT, stream, warehouse, lake, dataset | `modules/data.md` |
| Cloud, platform, IaC, network, deployment runtime | `modules/cloud.md` |
| Model, prompt, embedding, evaluation, ML/AI serving | `modules/ml.md` |
| Self-service analytics, semantic routing, governed answers | `modules/analytics.md` and, when data changes, `modules/data.md` |
| Browser UI, product-facing web flow, frontend component, rendered user document | `modules/web.md` |

Modules use REQUIRED, CONDITIONAL, PROJECT POLICY, and EXAMPLE. Optional
provider/tool patterns live in `references/` and never gate a cycle by
themselves. A future language/framework module may extend phases and gates but
cannot reorder or weaken core evidence and safety contracts.
Load `references/openai.md` only under `build-gpt` and
`references/anthropic.md` only under `build-claude`. Native or other primaries
receive neither overlay. Provider failure never changes provider family.
When Product Intent applies, read the Engineering Profile-selected artifact
(conventionally `docs/specs/<context>/PRODUCT.md`) before Domain and trace affected
journeys/outcomes through behavior, contracts, validation, and completion. Do not
invent that artifact for non-product work.

## Engineering Profile And Risk

Use bounded-context defaults and record only cycle overrides. Risk is:

- `routine`: localized and reversible without material public, production,
  sensitive-data, security-boundary, money, or safety impact
- `elevated`: public compatibility, migration, external integration, production,
  sensitive data, material reliability/performance, or security-boundary impact
- `critical`: irreversible loss, broad outage, regulated exposure,
  authentication/authorization failure, material financial impact, or safety harm

Risk may rise with new evidence and never falls silently.

## Development Kernel

Consider phases in dependency order; each consumes the prior artifact. Iterate
back when examples or tests reveal a domain, behavior, interface, or contract
error. Routine work may compress adjacent artifacts when existing stable context
and focused evidence already cover them; no concern is skipped silently.

### 1. Domain

Name bounded/adjacent contexts, ubiquitous language, entities, values, events,
owners, sources/sinks, trust boundaries, applicable modules, and affected
artifacts. Update the matching spec.

### 2. Behavior

Write implementation-free Given/When/Then scenarios using Domain terms. Cover
happy paths, edges, failures, recovery, compatibility, abuse cases when
applicable, and downstream-visible outcomes. Resolve consequential ambiguity.

### 3. Spec

Define concrete interfaces, signatures, commands, config/schema shapes, files,
examples, migrations, architecture decisions, and a dependency-aware backlog.
Map each interface to behavior and assign non-overlapping ownership.
For every Normative Specification created or materially changed, load
`references/spec-visuals.md`, add or refresh its Visual Evidence Plan, and
implement every required accessible visual without inventing decorative charts.

### 4. Contract

Define preconditions, postconditions, invariants, boundary validation, failure
semantics, compatibility, migration/rollback, security/reliability/observability
requirements, stale-artifact checks, and validation commands. Apply module
extensions.

### 5. Test-Driven Implementation

Create failing behavior or regression evidence before implementation when the
harness can express it. Confirm failure for the intended reason, implement the
minimum correct change, and obtain passing affected-scope evidence. Record why a
red check was impossible rather than fabricating one. Deploy and smoke-test
managed config or skills when applicable.

### 6. Refactor

With affected behavior passing, remove duplication and stale notes, simplify,
align names with Domain language, update specifications/changelog, and preserve
contracts and evidence. Finish with only intended worktree changes.

## Gate Ledger

Enumerate Development Kernel and completion gates with separate dimensions:

- Gate Applicability: `required` or `not_applicable` with reason
- Gate Result: `pending`, `passed`, `failed`, `unavailable`, or `not_run`
- Gate Exception: user-approved `deferred` or `accepted_risk` with rationale,
  owner, and expiry or review condition

Missing or failed required evidence blocks completion unless a Gate Exception is
explicitly approved. The agent may propose but never approve an exception. An
unavailable preferred tool creates a capability gap, not a pass.

For new schema-versioned cycles, a gate passes only after every predecessor is
disposed. Record a failure or unavailable authority immediately even when an
earlier gate is open. New evidence may tighten applicability from
`not_applicable` to `required` and reopen dependent passed gates; applicability
and risk never loosen silently. Use `dbsctrctl update-plan --plan PATH` after a
committed Engineering Profile change and `dbsctrctl raise-risk --plan PATH` when
risk rises. Gate Commit and Final Push reject stale profile identity. Schema-less
V3.1 records continue under their legacy transition rules.

## Artifact Lifecycle

Every cycle reviews README and CHANGELOG. README holds stable truth and
changes only when durable domain, behavior, interface, contract, Engineering
Profile, or validation truth changes. The private Cycle Record owns live execution
state and evidence. CHANGELOG gets one compact entry
at completion with outcome, validation, exceptions, commits, deployment, and
intended Final Push target. The Cycle Record and final response capture the
actual push result. Record each review with `dbsctrctl review-artifact`; validate with
`dbsctrctl check artifacts`. New Cycle Record state uses the Git common directory;
completed records remain there while each worktree has one active pointer.
Multiple sessions may resume one cycle, but one primary owns integration.
Delivery to the same upstream is serialized by the helper's target lock.
`begin` refuses dirty initial state and unknown ahead commits without changing
files or refs. Use native Worktrunk inventory and navigation. Removal requires
operator authorization and its blocking managed user pre-remove hook:
`dbsctrctl workspace-remove-check --json`. Retain successful cycles for at least
24 hours; failed gates, unknown delivery, dirty/private data or unavailable
process evidence block removal. Never bypass hooks, force removal, delete branches
automatically or garbage-collect shared caches. DBSCTR cleanup is retired.

DVC worktrees start code-only. Explicit `worktree-dvc-setup --cache PATH` selects
the repository-scoped external cache and reflink-only mode; `--check` verifies
configuration without hydration. Materialize only requested native DVC targets.
No copy fallback, full pull, shared mutable `.dvc` state or ignored-data copying.
Conflicting configuration/private cache data needs separately approved migration.

Invoke `dbsctrctl` through native shell permissions. Custom tool catalogs,
transparent routing and attach/bind/handover controls are retired. Native actor,
message and call identity remains unavailable unless independently verified;
arguments/environment never authenticate an actor. Plan and subagents retain
native write restrictions. Initiative registration requires the operator handoff
above; there is no custom child-session launcher. Herdr is presentation only.
`agent-worktree -- opencode|codex ...` provides optional foreground launch-only
busy coordination. Direct launches, in-UI switches and background jobs bypass it;
it is not a security boundary. Only an operator may confirm its busy override.

When the applicability plan contains `graphify`, run `dbsctrctl graphify-check`
after the final affected source change and before Final Push. The helper runs the
digest-bound managed central adapter in a disposable detached worktree and retains
private receipt evidence; feature cycles never update canonical `graphify-out/`.
Version changes require a new cycle selection and Engineering Profile change.
Selection authorizes bounded local execution only; the adapter never pulls or
pushes DVC, pushes Git, publishes, calls providers, or deploys. Target repositories
provide source, local DVC configuration, and canonical graph artifacts, not adapter code.
Private lifecycle state retains the digest-selected central executable so active
cycles and batches survive a later managed adapter upgrade.

Before final artifact closure, use `dbsctrctl reconcile-target --mode preview --json`
when the recorded
upstream may have advanced. If it reports `diverged`, prepare the no-commit merge,
resolve only explicit conflict paths, rerun the union affected validation, and
record every staged path through the Review/Integrate Gate Commit. The helper
never resolves conflicts, selects QA, rebases Gate Commits, or mutates the source
checkout. Repeat if Final Push detects another advance.

## Lifecycle Reconciliation Audit

When the user asks for a DBSCTR project/codebase audit, default to report-only.
Use `dbsctrctl audit --commit HEAD --json` to pin committed
scope, inventory lifecycle triplets, expose excluded dirty overlay, and check
Graphify freshness. Then verify material claims against authoritative source and
classify confirmed drift, stale evidence, missing artifacts, authority conflicts,
historical content, and unverified claims. Do not treat graph inference as source.
Use `dbsctrctl inspect` for bounded `read`, `tree`, `search`, and `object`
access to that resolved commit; never substitute filesystem reads that include
the dirty overlay.
For semantic reconciliation, load `references/semantic-audit.md`, keep the audit
on the resolved commit, apply its authority order and exact classifications, and
return its report shape. Evidence Envelope metadata may support a trace, but
withheld content remains unavailable. Private local references require explicit
authorization, a pinned commit, and non-public/non-authoritative treatment.

Keep this distinct from `/qa full`: lifecycle audit reconciles artifacts and
traceability; QA runs configured quality authorities. Do not write, archive,
execute external systems, or change statuses during report-only audit. When the
user explicitly approves remediation, turn verified findings into collision-safe
context batches and start each approved isolated DBSCTR cycle separately. Never infer
product/domain truth merely to make documents agree.

## Completion Gates

### Review/Integrate

Always evaluate diff coherence, behavior/interface/contract/test traceability,
migration impact, direct downstreams, configured CI, and final orchestrator
integration. Provider overlays or explicit Project Policy may add bounded review;
the core does not require repeated self-review or a human reviewer.

### Release

Apply when producing or publishing a releasable artifact. Record version,
release notes, compatibility/migration, artifact identity, approvals, and
applicable provenance. Planning does not authorize publication.

### Deploy

Apply when changing an environment. Record preview/plan, ordering, migrations,
health evidence, rollback/recovery, owner, and approval. Never perform an
external deployment without explicit authorization.

### Operate

Apply to running systems. Record ownership, health/readiness, applicable logs,
metrics/traces, alerts, incident path, capacity/cost signals, and post-deploy
verification.

### Maintain/Retire

Apply to public or long-lived systems. Record runtime/dependency EOL,
vulnerability intake, support/deprecation, migration, retention, ownership
transfer, access removal, and decommission evidence.

## QA

At evidence checkpoints, call `qa` in scoped mode with touched files, imports,
manifests, packages, tests, specs, downstream contracts, and Engineering Profile
Capability Requirements. Use project-selected authorities; do not install tools.
Unrelated pre-existing findings do not fail scoped work. Explicit full audits
remain user-requested.

QA returns a human summary plus structured Gate Result evidence for each
applicable Capability Requirement.

## Delegation And OpenCode

Ordinary DBSCTR executes in the current primary without Task or child sessions.
The primary implements, reviews, validates, deploys, stages and commits directly.
Only the explicitly selected Discovery-Coordinator may orchestrate approved child
work under its permissions. Preserve provider affinity and do not infer agent
authority from the skill name, model, tab label or unavailable tool.

Plan is read-only and ends with a Build Handoff. Build verifies source and
artifact freshness before writing. Request the mode change in the same conversation,
not another checkout/session as a workaround. Todos hold current state; specs and
Git are durable authority. File access never overrides lifecycle authorization.

## Critical-Path Profiling And Safe Concurrency

When diagnosing cycle wall time, a validated Build primary may bracket material
lifecycle work with `dbsctrctl phase-span` start and finish events. Declare only opaque span
identity, phase/operation class, dependencies, repository-relative ownership,
attribution, and final result. The helper owns timestamps and returns a path-free
compact profile. Unsupported automatic tool or subagent timing remains
`unavailable`; never infer a full critical path from message persistence times.

When benchmarking or authorizing non-obvious concurrency, submit the complete
candidate graph, completed-node set, and exactly one reconciliation node to
`dbsctrctl execution-dag`. The reconciliation node depends directly or transitively
on every worker. The helper validates operation classes, dependencies, cycles,
risk, and ownership overlap. The helper does not dispatch
work: the primary runs only returned ready nodes with existing parallel tool
calls, never Task delegation in an ordinary session, records finish spans, then
resubmits completed worker IDs. Only the
returned reconciliation node may integrate results and rerun affected validation
before dependent gates pass. A failed node follows normal gate
remediation and is never hidden by an automatic serial retry.

`benchmark` mode authorizes only the repeatable fixture. Real `concurrent` mode
remains forced serial until `dbsctrctl execution-benchmark` records at least
five successful post-warmup pairs bound to one committed fixture/blob, equivalent
required-gate digests, at least 10 percent lower median wall time, and no added
remediation rounds. The helper executes and times the committed fixture; callers
never submit benchmark durations or outcomes. Critical cycles,
uncertain dependencies, and overlapping independent ownership always remain
serial. DBSCTR adds no separate worker cap after independence is proven.

## Evidence And Git

At cycle start, use Worktrunk to create isolation, then register the explicit
checkout with `dbsctrctl begin --plan PATH` to record
schema version, committed Engineering Profile identity, explicit gate
applicability, HEAD, branch, upstream, worktree status, pre-cycle ahead commits,
Method Revision, gates, and Artifact Reviews. Use low-level `start` only for an
already prepared clean worktree. This baseline defines which commits the cycle
owns and whether an automatic Final Push can be safe.

Evidence checkpoints and coherent Gate Commits are mandatory when a gate changes
files. After one gate or a small adjacent gate group passes:

1. Inspect status, diff, and recent log.
2. Run affected-scope QA and required gate evidence.
3. Stage only intended files; never stage secrets, unrelated drift, or known
   failing required work.
4. Create one atomic Gate Commit with `dbsctrctl gate-commit --gates ...`; the
   helper rejects incomplete associated gates. Use the repository convention. Combine tiny
   adjacent gates when separate commits would add noise; skip gates with no file
   changes.
5. Verify the commit and remaining worktree state before continuing.

For schema-3 cycles, execute a project-selected authority through
`dbsctrctl record-evidence GATE --authority NAME [--path FILE ...] -- PROGRAM ...`.
This nested authority execution is permission-gated. The helper runs
an argument vector without a shell, stores only conservative metadata and safe
allowlisted output, withholds everything unclassified, and binds passing evidence
to the exact validated path/blob set and its Gate Commit. Do not place secrets in command arguments merely because the
record sanitizes them; use the project-owned secret wrapper and inherited process
environment. Gates with no file changes retain evidence only when its HEAD still
matches Final Push HEAD.

The primary alone stages, commits, and pushes. If hooks reject a commit, fix the
issue and create a new commit; never bypass hooks or rewrite published history.

After all required gates pass, perform one Final Push with `dbsctrctl final-push`
without another confirmation when the worktree is clean and only cycle-owned
commits are ahead. The user's standing DBSCTR policy authorizes only the recorded
feature-branch push and verified draft pull request into the protected base
branch; direct cycle delivery to `main` is prohibited. Verify synchronization and
report pushed commit IDs plus the draft pull-request URL. Draft delivery leaves
the recorded original checkout untouched.

Stop before push when HEAD is detached, no upstream exists, the destination
changed, pre-cycle ahead commits would be included, required evidence failed,
force would be needed, or repository policy requires another approval.
Never force-push automatically.

For a DVC-relevant cycle changing `*.dvc`, `dvc.yaml`, `dvc.lock`, `.dvc/config`,
or `.dvcignore`, run `dvc status`, couple changed outputs with their metadata,
and obtain separate approval for `dvc push`. After it succeeds, use
`dbsctrctl record-dvc-push` to bind its evidence to current HEAD. An unrelated
cycle in a DVC repository needs neither DVC execution nor push evidence. Never
hide the DVC external write inside standing Git-push authorization.

## Final Response

Lead with outcome. Include applicable modules and gates, validation evidence,
changed files, residual risks, blockers, accepted risks, deployment/restart
requirements, Gate Commits, and Final Push outcome. Stop for unresolved context, failed required
evidence, unsafe ownership overlap, or destructive, irreversible, external,
costly, or materially expanded action requiring approval.
