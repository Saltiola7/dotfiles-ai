# Build handoff — host-independent validation

## Slice `host-independent-tests`

| Field | Value |
|---|---|
| Context and Profile | `dbsctr_v3_lifecycle`, committed `PROFILE.md` |
| Risk | `routine` |
| Delivery | Draft pull request to `main`; no installed qualification |
| Gates | Domain, Behavior, Spec, Contract, Test-Driven Implementation, Refactor, Review/Integrate and Maintain/Retire are required. Release, Deploy and Operate are reasoned `not_applicable` in the [contract](../../specs/dbsctr_v3_lifecycle/features/host-independent-tests.md#acceptance-and-gates). |
| Depends on | Nothing |
| Lifecycle helper | Unchanged, so the CLI benchmark digest must not change |

The contract is normative. This page owns the write closure and the validation
commands.

### Write closure

Discovery documents. They are committed on the Discovery branch and reach the
Build branch through the Initiative import, not by being rewritten:

- `docs/initiatives/host-independent-validation/MANIFEST.json`
- `docs/initiatives/host-independent-validation/README.md`
- `docs/initiatives/host-independent-validation/BUILD-HANDOFF.md`
- `docs/specs/dbsctr_v3_lifecycle/features/host-independent-tests.md`
- `docs/specs/dbsctr_v3_lifecycle/README.md`
- `docs/specs/dotfiles_ai_distribution/README.md`
- `docs/specs/writing_skills/README.md`

Source changes Build makes:

| Path | Change |
|---|---|
| `tests/test_dbsctrctl.py` | The draft-PR reuse test no longer reads the developer's configuration root and keeps every reuse assertion |
| `tests/test_portable_distribution.py` | The rendering test supplies the existing target state in a disposable home, and gains the case that an unrelated local key is preserved |
| `tests/test_writing_skills.py` | The writing-commands capability test uses the opt-in and runs the named executable with an isolated home |
| `tests/test_dbsctr_rnd.py` | The session-list capability test uses the same opt-in and runs from a disposable home and working directory |
| `.github/workflows/test.yml` | The full-suite partition step sets the opt-in to the absolute path of the OpenCode it installed in the same job. No other step changes. |
| `docs/specs/dbsctr_v3_lifecycle/CHANGELOG.md` | One entry for the completed cycle |

A context README changes in Build only if one of its statements stops matching
the delivered behaviour.

Out of scope, with or without a small reason: the lifecycle helper, the R&D
worker, both OpenCode installers, `tests/ci_shard.py`, the rendering `modify_`
script, every other test, and any new fixture in `tests/conftest.py`.

### Constraints

- Each repaired test fails for its original cause before its repair. Record the
  red run, then repair, then record the green run.
- The opt-in is a test input only. It must not be read by any production code
  and must not change the worker's `OPENCODE_BIN` behaviour.
- A set opt-in never yields a skip. An unset one yields a skip whose reason
  names the variable and `1.19.4`.
- The test resolves the executable only from the opt-in, never from `PATH`.
- Check the contract's Mermaid diagram in the rendered pull request. A syntax or
  rendering failure blocks the visual evidence; do not replace it with a claim.
- Report the four host conditions in public artifacts only in synthetic terms.

### Validation

Run from the Build checkout with the project's selected interpreter:

```text
uv run --frozen --group test pytest tests/test_dbsctrctl.py tests/test_portable_distribution.py
uv run --frozen --group test pytest tests/test_writing_skills.py tests/test_dbsctr_rnd.py
uv run --frozen --group test pytest tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers
  tests/test_opencode_control_plane.py tests/test_dbsctr_lifecycle.py
dbsctrctl initiative-check --manifest docs/initiatives/host-independent-validation/MANIFEST.json --json
```

Also run both capability tests three ways: with the opt-in unset, with it naming
a 1.19.4 executable, and with it naming a 2.x executable. Only a 1.19.4 host can
produce the passing case locally; where no such executable exists, record that
case as unavailable and rely on the pull request's partitions for it. Never
record an unavailable case as passed.

After Final Push, read the partition receipts of the pull request and report
both capability tests as passed, never skipped, with the push result.

### Risks

- **A weakened required check.** If the workflow entry is wrong, both capability
  tests skip in CI and the V1 contract stops being enforced. The partition
  receipt check above is the control.
- **Hidden drift on a developer machine.** The opt-in skip is visible and the
  known drift is recorded as INT-007 with the V2 migration as owner.
- **A repaired test that stops testing its subject.** Keep every existing
  assertion of the four tests; add, do not replace.

### Open decisions

None. Three choices are left to Build because they do not change behaviour:
how the reuse test isolates its configuration root, how the rendering test
supplies the existing target file, and how the workflow resolves the absolute
path of its installed OpenCode.

A material finding returns to Discovery before the contract changes. In
particular, Build stops if it needs any non-test code change beyond the one
workflow environment entry; that raises the risk to `elevated`.

### Recommended Build agent

One Build primary on the operator's default route. The slice is Python tests,
one workflow entry and documents, and needs no specialist route.

### Launch

Build obtains a fresh `dbsctrctl initiative-receipt` for the slice, runs
`dbsctrctl begin` with explicit Initiative arguments and `--preflight` in a
Build checkout at the current default, and presents the scope, risk, target and
launch digest for approval. The committed Discovery branch is the
`--initiative-source`. Registration is the operator's approval to give; nothing
on this page supplies it.
