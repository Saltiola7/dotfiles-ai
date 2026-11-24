# Host-independent validation

Status: ready for Build as one routine, test-only slice,
`host-independent-tests`. Discovery was completed on 2026-11-24 from measured
causes. Nothing is implemented. INT-009 is deferred to the OpenCode V2
migration.

## Why now

Four tests pass in configured CI and fail on a developer machine that holds
ordinary local state. Two read operator-private state: a policy file in the
configuration directory, and the real OpenCode configuration. Two execute the
installed `opencode` with `--pure`, a V1 flag that every OpenCode 2.x version
observed rejects.

The last two are not noise. The R&D worker depends on the same flag on its
reserve, launch and cleanup paths, and CI stays green only by installing V1.
The repository's native installer asserts a `v2` binary and its managed V1
installer runs on x86_64 only, while the distribution profile names an aarch64
Linux machine as the sole workstation target. That gap was recorded nowhere.

Until now a developer could make the suite green on such a machine only by
changing the machine. The rule in the
[contract](../../specs/dbsctr_v3_lifecycle/features/host-independent-tests.md)
makes the result depend on the repository rather than on who runs it, and keeps
CI as the enforcer of the capability.

## Context map

| Context | Home | Responsibility |
|---|---|---|
| `dbsctr_v3_lifecycle` | Saltiola7/dotfiles-ai | Home of the rule and of the slice's cycle; the draft-PR reuse test |
| `dotfiles_ai_distribution` | Saltiola7/dotfiles-ai | The rendering test; the R&D worker's capability guard; the CI pin that CI opts in with |
| `writing_skills` (README-based profile) | Saltiola7/dotfiles-ai | The writing-commands capability test |

Adjacent boundaries, deliberately not changed:

- `opencode_control_plane` supplies one test-helper import and already states
  in its Profile that it probes version-dependent interfaces. Its authority
  does not change.
- The [OpenCode V2 migration](../opencode-rolling-stable/README.md) owns the
  disposition of the recorded gap. This Initiative does not edit its manifest,
  so no in-flight launch digest is disturbed.

The operator approved this map on 2026-11-24.

## Decisions

- **Record the V2 gap; do not silence it.** Making the two capability tests
  pass on a V2 machine would hide a real incompatibility. The gap is recorded
  with impact, safe behaviour, owner and review condition, and the V2 migration
  owns its disposition.
- **Opt-in qualification, not automatic skipping.** A capability test runs only
  when `DBSCTR_OPENCODE_NATIVE_TEST_EXECUTABLE` names an already-qualified
  executable, following the existing `DBSCTR_GRAPHIFY_NATIVE_TEST_EXECUTABLE`
  precedent. A developer machine without the opt-in sees a visible skip. An
  automatic skip by detected version was rejected because it would hide drift
  silently. Keeping hard failures was rejected because it would leave the
  suite red on the sole workstation target.
- **Known tests plus one written rule.** The slice repairs the four identified
  tests and states the rule once. A census of every test and a suite-wide
  isolation fixture are out of scope; they can follow as separate work if the
  rule turns out to be widely violated.
- **A new Initiative.** `linux-ci-cutover` owns CI lanes and the V2 migration
  owns the runtime. Neither is the home of a cross-context test-authoring rule.

## Statements

| ID | Kind | Summary |
|---|---|---|
| INT-001 | requirement | The four tests never fail because of the developer machine's state |
| INT-002 | requirement | Tests do not read operator-private state from the real home |
| INT-003 | requirement | Version-sensitive capability tests run only under an opt-in that names a qualified executable |
| INT-004 | requirement | Every CI job that enforces a capability sets the opt-in |
| INT-005 | decision | One variable, `DBSCTR_OPENCODE_NATIVE_TEST_EXECUTABLE`, following the Graphify precedent |
| INT-006 | requirement | Repaired tests keep what they verify |
| INT-007 | risk | The R&D worker needs the V1-only `--pure` flag, and CI's V1 pin conceals it |
| INT-008 | decision | The V2 migration owns the disposition; its manifest is not edited here |
| INT-009 | requirement, deferred | A V2 session-discovery route for the worker and an aligned pin |
| INT-010 | constraint | The rule is stated once; context READMEs point to it |
| INT-011 | non-goal | No suite-wide isolation fixture, census or `modify_` script change |
| INT-012 | non-goal | No change to the helper, the worker, the installers or the worker's enablement |
| INT-013 | risk | An opt-in skip can hide drift on a developer machine |
| INT-014 | constraint | Public artifacts carry no private identity, machine path, configuration or host inventory |

## Validation strategy

1. `dbsctrctl initiative-check --manifest docs/initiatives/host-independent-validation/MANIFEST.json --json`
   passes. It is re-run after any manifest change, because a changed digest
   invalidates earlier readiness.
2. Each cause was confirmed by changing one input: the configuration root, the
   home directory, the OpenCode version. Build repeats the four red runs before
   the repair and retains them as private evidence.
3. After the repair, on a machine with all three conditions present, two tests
   pass and two skip with the named reason. With the opt-in set, both capability
   tests pass on 1.19.4 and fail on a 2.x executable or a missing path. Setting
   the opt-in never produces a skip.
4. The pull request's own full-suite partitions report both capability tests as
   passed, never skipped. This is observed with the push result and is not a
   gate result.
5. The repository's publication and instruction contracts pass on the exact
   candidate artifact set, including the new documents.

## Engineering Profile overrides

| Field | This slice |
|---|---|
| Context and Profile | `dbsctr_v3_lifecycle`, committed `PROFILE.md`; no Profile value changes |
| Affected scope | Four test files, one environment entry in the full-suite workflow, one CHANGELOG entry, and the README statements that point to the contract |
| Risk | `routine`: localized, reversible, no production code, no sensitive data, no security boundary |
| Delivery intent | `draft_pr`: a source-only draft pull request to `main` |
| Modules | Python |
| Gate statuses | Eight required gates; Release, Deploy and Operate are reasoned `not_applicable`, as listed in the contract |

Risk rises to `elevated` if Build must change any non-test code beyond the one
workflow environment entry.

## Delivery and activation boundary

- The slice is delivered through the existing lifecycle: a fresh receipt,
  preflight, and plan-specific approval before registration. See the
  [handoff](BUILD-HANDOFF.md) for the write closure and validation commands.
- The lifecycle helper is unchanged, so the CLI benchmark digest is unchanged,
  and no installed qualification or rollout applies.
- The repository's publication authority runs over every new document before
  the receipt. Public artifacts use synthetic examples and name no private
  identity, machine path, configuration or host inventory.
- This Initiative does not implement INT-009, migrate the R&D worker, or move
  the CI pin. Those belong to the V2 migration.
