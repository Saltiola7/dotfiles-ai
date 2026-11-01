# Scoped mutmut execution

Read this only when the project selects mutmut. These are locally maintained
integration notes, not a bundled upstream skill or a promise that every mutmut
version supports every option.

## Bind the version and workspace

Resolve the installed command through the project's existing environment. Check
`mutmut --version` and `mutmut run --help` there. If mutmut is absent, report that
execution is unavailable and retain the proposed experiment; installation is a
separate dependency decision.

The current mutmut documentation describes a POSIX fork-based engine. Native
Windows needs a suitable selected environment such as WSL. Mutmut 3+ primarily
mutates function bodies; do not claim coverage of module-level executable code
from that experiment. Do not downgrade a project's engine to gain another
execution model without an explicit migration decision.

Current mutmut builds a `mutants/` copy for execution. Nevertheless, inspect the
selected version and use an isolated workspace: `mutmut apply` and the browse
interface can write a mutant into source. Use a displayed diff to understand a
change before applying it. Do not apply mutants in the user's working checkout.
Retain before/after source identity and intentional overlays; recovery should
discard only an owned disposable experiment, not reset unrelated work.

## Configure a small target

The following is an illustrative current configuration for a hypothetical
`src/ledger` package. Resolve actual paths and verify this syntax against the
project's pinned version before changing its configuration:

```toml
[tool.mutmut]
source_paths = ["src/ledger/"]
pytest_add_cli_args_test_selection = ["tests/unit/test_ledger.py"]
```

TOML path collections are arrays. Older versions use `paths_to_mutate`; current
versions deprecate that name in favor of `source_paths`. Preserve a working
older configuration unless migration is in scope. Options supported only by
newer documentation must not be silently added to older projects.

Use the normal project's test command first with the same selected tests. Then,
where the installed engine supports it, a quoted mutant-name pattern can bound
execution, for example `mutmut run 'ledger.rules*'`. A pattern is not proof of
the executed scope: reconcile the actual mutant names and import paths in the
report. Verify that tests import the mutated copy rather than an installed or
original checkout. Copy only required local fixtures and configuration into the
experiment through version-supported `also_copy` settings; leave live service
tests outside a selected isolated unit experiment.

Use a project-owned bounded runner for the total campaign and its worker tree.
Individual-mutant timeouts are distinct from total elapsed budget. On interrupt,
verify worker cleanup and preserve partial results. Do not assume a shell
timeout killed descendants or that resumable cached results remain valid after
dependencies, fixtures, tests, source, selection or configuration change.

## Interpret engine optimizations and failures

- Test association, stack-depth filtering and covered-line-only mutation change
  which tests and mutants are considered. Record those choices. A lower stack
  limit can exclude a test that would detect a mutation; a coverage filter leaves
  uncovered behavior unassessed.
- Source/test/fixture/environment changes can invalidate cached evidence. Preserve
  the old report and requalify the affected experiment instead of trusting a
  cached green result after a warning. Only clear artifacts owned by the isolated
  experiment when a clean run is needed.
- Current optional `fork`/`forkserver` isolation settings still depend on POSIX
  fork. Imports and test collection can leave threads, event loops, patched
  sockets or native contexts in inherited state. Reproduce hangs or crashes in
  the selected environment before interpreting them as a behavioral result;
  `forkserver` is not an unconditional guarantee of clean fixture state.
- A mutmut `killed` label can include a pytest internal error. Inspect the actual
  failure and distinguish an assertion kill from an unusable test run. Keep type
  checker rejection separate from assertion strength; do not switch the project's
  checker merely to enable an engine filter.
- Broad exclusions, stack-depth reductions and `no mutate` pragmas require an
  explained scope or semantic reason. They must not manufacture a target score.
  Pragma support varies by version, so verify syntax rather than adding guessed
  block or region forms.

## Primary sources

- [mutmut documentation](https://mutmut.readthedocs.io/en/latest/) — current
  commands, configuration, process isolation and supported filtering.
- [mutmut configuration implementation](https://github.com/boxed/mutmut/blob/main/src/mutmut/configuration.py)
  — inspect the matching release for option names and cache semantics.
- [mutmut outcome implementation](https://github.com/boxed/mutmut/blob/main/src/mutmut/stats.py)
  — inspect the matching release before interpreting an exit status.

Recheck these assumptions when the project upgrades mutmut, Python, pytest,
native dependencies or the test environment. Engine setup and static review are
distinct from a completed mutation campaign.
