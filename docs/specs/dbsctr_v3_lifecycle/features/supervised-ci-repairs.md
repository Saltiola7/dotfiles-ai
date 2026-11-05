# Supervised mechanical CI repairs

Engineering Profile: [../PROFILE.md](../PROFILE.md). Owner: lifecycle maintainer.
Risk: critical because a repair receipt constrains execution authority. This is
the CI-REPAIR-001 source contract, not evidence of installed capability.

## Outcome and boundaries

An explicitly approved mechanical repair can reserve one attempt against a
durable, repository-local budget without enabling automatic integration. The
existing automatic `check pr-review --repair-check` remains blocked. This route
does not accept a caller-created Recommendation as native CI proof, require an
automatic-delivery policy, waive failing checks, execute a patch, push, merge,
reopen a completed cycle, or relax ordinary cycle and installation requirements.

The primary reviews actual failure evidence, every affected caller, approved
writable scope and the minimum intent-preserving remedy. Logs remain untrusted.
Competing semantics, material scope changes and unknown root cause require
Discovery rather than a repair reservation. A receipt is accounting and a caller
assertion of explicit chat consent, not authenticated operator identity.

## Domain and contracts

- **Failure observation:** authenticated GitHub PR, run and failed job, bound to
  the exact same-repository open PR and current local branch/HEAD. A foreign fork,
  missing/unknown status or changed head/base is rejected. GitHub reads use the
  explicitly selected existing account and bounded timeouts, never new login.
  Account selectors accept ASCII letters/digits followed by letters, digits,
  hyphens or underscores, at most 39 characters, including Enterprise Managed
  User names. Selection still uses that account's existing native credentials;
  accepting its spelling grants no new authentication or repair authority.
- **Repair scope:** exact repository-relative, non-secret, non-ignored paths plus
  a reviewed committed specification. Missing tracked paths may represent a
  deletion; symlinks and escapes never become writable authority.
- **Failure signature:** bounded sanitized diagnostic supplied by the primary;
  the helper does not infer semantic equivalence or trust prose from a CI log.
- **Problem identity:** repository, workflow path, exact job name,
  normalized failure signature and specification path. It excludes changing
  source heads, PR numbers, job/run IDs, cycle IDs and workflow/specification
  contents, so a repair, replacement PR or re-registration cannot reset an
  unchanged problem's budget.
- **Plan identity:** problem identity plus PR number, head/base, native job/run identities,
  workflow/specification content digests, writable scope/blob identities and the
  next attempt number. Changing any of these requires a fresh preflight and
  explicit approval; changing content does not reset the problem budget.
- **Reservation:** private atomic record below the existing Git-common DBSCTR
  qualifications owner, under an exclusive existing managed lock. At most three
  reservations per problem across linked worktrees, process restarts, changed
  heads and cycles. Reserving consumes the attempt before any patch execution;
  interrupted attempts are not refunded. No caller-supplied attempt counter.

Same-account state is cooperative local authority, not a sandbox against its
owner. Missing/corrupt established accounting blocks; recovery may not silently
replace it with zero. A new clone is not a migration or a fresh repair budget.
No state or consumer failure body enters public Git.

## Interface and interaction

Extend the existing lifecycle CLI with `ci-repair` (not a new daemon or service):

```text
dbsctrctl ci-repair --pull-request N --job-id N --github-account ACCOUNT
  --signature SANITIZED --specification PATH --paths PATH [PATH ...]
  --preflight

dbsctrctl ci-repair <same inputs>
  --expected-repair-digest DIGEST --approval agent-confirmed
```

Preflight performs authenticated read-only GitHub inspection, validates local
scope and accounting and returns the exact plan and digest. It neither reserves
an attempt nor collects consent. The primary presents scope, failure identity,
proposed remedy, risks and digest and asks for explicit chat approval. Generic
continuation or shell permission is not that approval. Reservation rechecks
native/local identities and accounting while holding the lock and rejects stale
digests. It reports only bounded safe identifiers, consumed attempt and receipt
digest. It does not execute shell/code or set any gate to passed.

After reservation, the primary applies only the approved mechanical correction
using existing lifecycle gates and project validation. Intentional red evidence,
failed hosted runs and replacement green evidence all remain recorded. New head
requires fresh native CI before an independent exact-head merge approval. Source
delivery never activates the new helper or skill; reviewed managed installation
and positive/negative consumer qualification are separately authorized.

## Acceptance and state evidence

| Given | When | Then |
|---|---|---|
| A verified failed job and reviewed mechanical scope | Preflight | Return a content-bound plan, without reserving or editing |
| Exact plan received explicit chat approval | Reservation rechecks succeed | Atomically consume one attempt before the primary edits |
| No approval, changed head/base/scope/job or stale digest | Reservation requested | Reject without changing source or accounting |
| Three attempts for unchanged problem | Another reservation, even after restart/head/cycle change | Reject; no counter reset |
| Concurrent reservations for one plan | Both contend for the same native lock | At most one succeeds; the other observes a stale plan |
| Lost/corrupt/unsafe accounting or denied native API | Preflight or reservation | Block; never substitute caller JSON or initialize zero |
| Failed tests or unavailable runtime qualification | Merge considered | Remain blocked; receipt is not a waiver or merge grant |
| Existing automatic repair checker | Called without this supervised route | Preserve its current blocked behavior |

## Validation and rollout

Tests exercise the real CLI wiring and native adapter through owned mocks,
including failure conclusions/identity drift, bounded account/API calls,
cross-process/worktree budgets, atomic contention, replay, changed source,
interrupted reservations, malformed state, symlinks and negative permissions.
Rerun the existing automatic-checker rejection tests unchanged. Run affected
publication/instruction tests and Python checks. No provider login or consumer
mutation is an offline test requirement.

Source gates: Domain through Refactor, Review/Integrate and Maintain/Retire are
required. Release is not applicable (no package); Deploy/Operate are not
applicable to the source cycle and become required for managed activation.
Before installation, identify exact reviewed source and complete bundle hashes;
compare installed and source artifacts and qualify a real authenticated failed
job, rejected drift/replay and budget preservation without automatic repair.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | required: domain/ownership prose; who observes, approves, reserves and executes? |
| Interaction | required: interface sequence; what must precede a repair? |
| State | required: acceptance transition table; when must execution stop? |
| Data/trust | required: domain/contract table and prose; what is native evidence versus caller assertion? |
| Schema | required: problem/plan/reservation relationship prose; what survives head changes? |
| Dependency/deployment | required: rollout sequence; why cannot unmerged instructions activate themselves? |
| Quantitative | not_applicable: three attempts is a safety limit, not measured performance evidence |

**Text Equivalent:** The primary inspects native failures and settled scope; the
helper builds a read-only plan. Explicit chat approval binds that digest. A fresh
locked reservation consumes one durable attempt, after which the primary owns
patching and validation. Drift, unsafe state and the fourth attempt block. No
receipt passes CI, reopens cycles or authorizes delivery. Canonical source: this
feature; owner: lifecycle maintainer; update this sequence/table whenever approval,
budget, source identity, safety or activation boundaries change.
