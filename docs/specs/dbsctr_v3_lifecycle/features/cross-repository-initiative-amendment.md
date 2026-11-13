# Retained cross-repository Initiative authority

## Scope and ownership

Extend `initiative-amend` for an already registered Build slice whose coordinator
Discovery repository differs from its implementation repository. The operator
selects an existing clean native authority checkout and retains it through the
consumer cycle. The lifecycle maintainer owns this critical-risk source repair.
Use the existing CLI, applicability plan, locks, evidence custody and exact-digest
approval. No alternate registration, record rewrite, import engine or network
operation is introduced.

The original [same-repository amendment](initiative-authority-amendment.md)
contract remains unchanged. Cross-repository amendments use entry/launch version 2;
version 1 retains its existing meaning. Source delivery does not authorize managed
helper activation or application of a consumer amendment.

## Behavior and authority

- Given a native active cycle and a new committed ready receipt for the same
  Initiative/context/slice, preflight may bind a retained coordinator checkout.
  Its canonical native directory/common-Git/worktree identities, exact HEAD,
  origin repository, manifest and all referenced document blobs/modes must be
  verified locally. The coordinator repository must equal the original receipt's
  coordinator and differ from the implementation repository. An independent clone
  of the same repository cannot select version 2 instead of version 1. Native
  custody binds device/inode/owner identities for the checkout, common Git
  directory and worktree Git directory, so replacement at identical paths is
  rejected. The implementation repository and delivery identity do not change.
- Given that exact plan and renewed operator approval, append one amendment and
  reopen all required gates, preserving original registration, receipt, approval,
  source baseline, recorded commits, evidence, failed results and history.
- Given changed authority identity, HEAD, origin, selected working/index bytes,
  unavailable objects or a missing retained checkout, preflight/apply/read/status/
  Gate Commit/completion must fail closed. No previous receipt fallback, implicit
  fetch, login, replacement clone or fabricated success is permitted.
- Given a cross-repository amendment, coordinator documents remain coordinator
  owned. They are not imported into the implementation repository or published
  with it. The Build checkpoint binds its unchanged Engineering Profile locally;
  full foreign document closure is separately bound and revalidated by the
  immutable amendment envelope. A recorded nonempty-gate commit and fresh evidence
  are still required before completion.
- Same-digest replay, stale approval, chain validation, private preimages/outcomes,
  bounded diagnostics, atomic replacement and lock behavior retain the existing
  amendment contract. External source paths stay in private evidence only.
- Historical inventory from another linked checkout validates the local profile
  at the immutable source commit captured in the approved amendment's
  `checkout.head`, with its recorded blob/mode. The caller's current HEAD/profile
  is not historical authority. Missing source objects, malformed or moving
  revision selectors and a wrong recorded blob still refuse. Live amendment
  selection continues to require its actual current clean profile. Retained
  coordinator custody and every existing envelope/history check remain mandatory;
  no Cycle Record is repaired or rewritten to accommodate an unrelated checkout.

## Versioned data and validation

Version-2 launch plans add an `authority` object with canonical retained directory,
native identity digest, coordinator repository, exact source commit, and sorted
foreign `{path,blob,mode}` closure (manifest plus receipt artifacts). `closure`
continues to mean the locally checkpointed document set: the Build Engineering
Profile at its recorded blob/mode. No data key or CLI argument is added. Entry
version 2 requires launch version 2 and this complete authority object; version 1
must not contain it. Unknown or mixed versions fail closed.

Tests use disposable independent Git repositories and the public CLI. Cover
preflight without cycle/Git mutation; exact apply/replay; status after progress;
local checkpoint without foreign document import; original failed-evidence
retention and stale-evidence refusal; authority deletion, HEAD/origin changes,
dirty selected worktree/index, unavailable objects, forged custody, wrong
coordinator/context/slice, and stale approval. Existing version-1 amendment and
completion regressions remain required. Hosted CI is integration evidence;
managed activation and real consumer amendment remain separate approvals.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | required: ownership table below; which repository owns each artifact? |
| Interaction | required: transition table below; when does consent permit mutation? |
| State | required: transition table below; what happens when authority disappears? |
| Data/trust | required: ownership table; what crosses the repository boundary? |
| Schema | required: ownership table and versioned data contract above |
| Dependency/deployment | required: retained authority dependency in transition table |
| Quantitative | not_applicable: no performance or numerical comparison claim |

| Owner | Bound artifact | Mutation boundary |
|---|---|---|
| Coordinator checkout | Exact commit, manifest and foreign document closure | Read only; must remain available and unchanged |
| Original Build checkout | Engineering Profile, source, gates and checkpoint | Ordinary gated Build changes; no foreign document import |
| Private cycle store | Versioned plan, preimage, envelope and outcome | Exact approved amendment only |
| Operator | Exact amendment digest | Consent is caller-asserted, never authenticated by an argument |

| Current state / event | Required action | Result |
|---|---|---|
| Active cycle; new ready authority | Verify both native repositories and closures; preflight | Retained private plan, unchanged cycle |
| Exact approved plan | Revalidate; persist preimage/outcome; append amendment | Same cycle, required gates pending |
| Amended cycle; ordinary gated progress | Verify retained authority and fresh evidence; record local checkpoint | Completion eligible only after all required gates pass |
| Missing or changed retained authority | Refuse read/mutation/completion | Preserve state; operator recovery needed |
| Historical inventory from another checkout | Verify local profile at approved immutable source commit; retain all other guards | Same record remains valid independently of caller's later profile |

**Text Equivalent:** Coordinator owns and retains foreign normative documents;
Build owns its profile, source and gates. Private evidence binds both without
copying coordinator documents into public Build Git. Preflight changes no cycle.
Exact approval permits only amendment and gate reopening. Every later operation
requires the retained authority; loss blocks rather than selecting another source.
Historical local profile proof uses the approved source commit, not caller HEAD.
Canonical source: this feature. Owner: lifecycle maintainer. Update these tables
when custody, versioning, approval or completion boundaries change.
