# Six operator-facing CLI corrections

Owner: lifecycle maintainer. [Engineering Profile](../PROFILE.md); Python and
Security modules. This specifies six independent source changes. The
[Initiative](../../../initiatives/dbsctr-workflow-convergence/README.md) orders
them. Use the existing CLI, Git, Worktrunk and Cycle Record interfaces. The
delivery and native acceptance criteria are in the
[Linux rollout](../../dotfiles_ai_distribution/features/operator-cli-rollout.md).

| ID / risk | Given | When | Required outcome |
|---|---|---|---|
| INT-104 / elevated | A regular file was committed before its parent directory was ignored | Fresh path-bound evidence and `gate-commit` name that exact modified file | Commit its validated blob once. Leave the ignore rules and any ignored untracked neighbor alone. |
| INT-105 / elevated | An Initiative amendment cannot proceed | The operator reads `initiative-amend` output | Distinguish the failed precondition from a partial amendment needing recovery, with a safe next action. |
| INT-106 / elevated | A task checkout is dirty, or tracks no upstream or the wrong one | The operator requests new-cycle registration or Initiative preflight | Refuse before offering a digest or asking for approval; explain the remedy for this launch mode. |
| INT-107 / elevated | A completed feature delivery has an open PR and the protected base advances | The operator asks how to reconcile it | Point to a **new** exact-approved Initiative `begin --follow-up-pr` on the same PR. Keep the original completion and require fresh union validation and CI on the updated head. |
| INT-108 / critical | A retained Cycle Record refers to a missing checkout | Worktrunk asks about another target | Skip the unrelated record as a target blocker **only** with positive evidence of disjoint ownership and preservation of its required metadata through native removal. Otherwise retain the checkout. |
| INT-109 / critical | The global process listing warns its output may be incomplete | The removal check evaluates a target | Clear only the process predicate and only if a fresh independent observation establishes complete coverage of that target with no relevant users. Positive holders block; incomplete evidence is unavailable. |

## First slice: tracked-file staging

Characterization at `196e7446`: in a disposable native Git fixture, track a
file, commit a parent ignore rule, modify the file and create an ignored
untracked sibling. On the unmodified source CLI, `record-evidence` succeeds.
`gate-commit` refuses at the literal Git add; the requested file alone is
already staged, but HEAD and the Cycle Record do not advance. A nonzero staging
result is not proof that the index stayed unchanged, nor is a populated index
permission to disregard an error.

Acceptance:

- Cover both initially unstaged and already exactly staged tracked edits. Exercise
  a mixed request with a normal permitted new path; verify the evidence, index
  and committed blob for **each** named path, the exact commit path set, and one
  recorded Gate Commit. Never recurse into an ignored directory or require the
  consumer to edit `.gitignore`.
- Explicitly requesting an ignored untracked neighbor must fail, even when
  another requested file is tracked. A path staged as a new ignored file by
  another writer is not a committed tracked predecessor. Do not broaden secret
  path permissions, treat a pathspec as a literal identity proof, or use blanket
  force-add. Keep existing qualified upstream-template handling intact.
- Stale evidence, an unrelated staged path or an unclassified staging failure
  must not produce a commit or advance the record. Preserve unrelated index and
  worktree content; never reset user staging to recover. Keep existing staged
  and unstaged tracked-deletion/rename and absent-path evidence semantics.

Build owns the staging/evidence path in `dot_local/bin/executable_dbsctrctl`
and its public-CLI regressions in `tests/test_dbsctrctl.py`; also run the
existing completion-reconciliation tests. If exact helper-byte pins change,
verify their existing owners and requalify the affected approved workloads.
Do not change a check's semantics or success threshold to refresh a pin. A
material scope or evidence-format change returns to Discovery.

## Remaining slice boundaries

- **Amendment:** Keep the schema-1 result keys, existing success statuses and
  exit codes (0 success, 1 blocked, 75 recovery required). Keep the existing
  broad reason for compatibility and add a bounded classified reason when
  known: for example, inactive selection, changed applicability, stale
  approval or inconsistent durable custody. Unknown failures retain the safe
  fallback. Distinguish fresh preflight from recovery; do not retry an uncertain
  mutation. Test a sentinel private input on stdout and stderr. Preserve the
  [amendment's](initiative-authority-amendment.md) consent and replay rules.
- **Begin:** New work starts clean at its verified comparison base. For a new
  task the suggested tracking ref is the verified base; for a published-feature
  follow-up it is the verified published feature. Never guess `main` or `master`,
  retarget an existing branch, stash dirt or grant a new registration mode.
  Test dirty, missing, wrong and changed-during-confirmation states; no new
  record, import, staged change or misleading preflight success.
- **Published PR:** Use the existing [published-feature contract](published-feature-followup.md)
  (INT-100–103). Give actionable guidance when no active cycle can reconcile;
  do not imply every missing active pointer identifies a PR. No standalone
  registration extension, reopened cycle, branch rewrite or implicit remote
  operation. Exercise the existing route with matched/mismatched heads, an
  advanced base, unchanged original records and unchanged draft/ready state.
- **Orphan scope:** Keep corrupt records, reused identifiers/paths, ambiguous
  ownership and target-associated active cycles blocking. Branch-name
  inequality alone is insufficient. Test with an unrelated active orphan,
  a target-associated record, an unresolvable record, and native prune side
  effects. Do not prune, recreate admin directories, retire records, or change
  the strict automatic-removal blockers as a way to pass inspection.
- **Process coverage:** Keep the existing same-user scope and its native
  ownership constraints. Verify a holder whose cwd is outside the checkout;
  also exercise cwd inside, deleted-but-open files, unavailable permissions or
  namespaces, inventory limits/timeouts and a changed target. An empty listing,
  suppressed stderr, a warning-path prefix or exit 0 alone is not completeness
  evidence. If complete target coverage cannot be demonstrated, report the
  existing unavailable result. No read, reconfiguration or unmount of unrelated
  filesystems, new privileges, process signalling or hook bypass.

## Gates and validation

Use the existing [CORE-SOURCE plan](../../../initiatives/dbsctr-workflow-convergence/CORE-SOURCE.plan.json)
for each separate draft PR. Domain, Behavior, Spec, Contract, Test-driven
implementation, Refactor, Review/Integrate and Maintain/Retire are required.
Release is not applicable (no separate package); Deploy and Operate belong to
the distribution rollout. Gate results are pending; no exceptions are granted.
Review the context README and record actual outcomes in the CHANGELOG at
completion. Build runs the relevant Git/CLI fixtures, module checks and
repository-owned publication/instruction checks, then full current-head CI.
Source qualification, publication, verified merge and installed qualification
are distinct. Public artifacts and fixtures use synthetic identities only.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | Required: the six contract rows assign the CLI, native tool and operator responsibilities. |
| Interaction / state | Required: the tracked-file sequence below distinguishes a staged change from a finished gate. |
| Data/trust | Required: the sequence and process/orphan rows identify what counts as evidence and when to refuse. |
| Schema | Not applicable: no persistent schema change is selected; the existing amendment result owns its shape. |
| Dependency/deployment | The Initiative orders slices; the distribution rollout owns the target acceptance table. |
| Quantitative | Not applicable: no performance or population claim. |

| Input | Checked by | Permitted transition |
|---|---|---|
| Explicit names and current files | CLI with existing path policy and Git tracking provenance | Bind current blobs to required gate evidence |
| Matching evidence and intended index | Git staging and CLI path/blob checks | Create a candidate commit |
| Verified commit matches approved paths and blobs | CLI and private cycle ledger | Record the Gate Commit once |
| Missing proof or mismatched bytes at any step | CLI | Refuse; retain evidence, unrelated work and the original ledger |

**Text Equivalent:** The operator selects paths. Git establishes tracking and
contents; the helper checks the selected files against bound evidence before
recording a commit. Staging alone is not completion. Likewise a missing
checkout or partial process listing cannot authorize removal. The lifecycle
maintainer updates these tables when the input authority or refusal changes.
