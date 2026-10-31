# Bats patterns: selected-project examples

Examples illustrate Bats behavior after the project selects Bats and compatible
helpers. They do not authorize installing tools or replacing an existing test
authority. Resolve syntax and options against the selected Bats version:

```bash
command -v bats
bats --version
bats --help
```

Use the project's package/environment authority for an explicitly authorized
setup. Preserve its dependency pins and CI actions; no global installation or
upstream installer execution is implied by this reference.

## Test layout and executable boundaries

A typical existing layout has an executable in `bin/`, `.bats` files in `tests/`,
and optional `tests/test_helper.bash` plus `tests/fixtures/`. Adapt to the project;
these names are examples, not a required directory migration.

```bash
#!/usr/bin/env bats

setup() {
    export SCRIPT="${BATS_TEST_DIRNAME}/../bin/example-cli"
}

@test "missing argument returns usage failure" {
    run "$SCRIPT"
    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "valid input creates expected output" {
    output_path="$BATS_TEST_TMPDIR/result.txt"
    run "$SCRIPT" --output "$output_path" valid-input
    [ "$status" -eq 0 ]
    [ -f "$output_path" ]
    [ "$(cat "$output_path")" = 'expected content' ]
}
```

The executable and expected contract come from the consuming project. Use `load`
for a deliberate test helper/library; sourcing an arbitrary executable can run
its main body and affect the test environment. Test environment changes by
deliberately sourcing the library in a controlled shell when that is its API.

## Status, streams and pipelines

`run` captures the subprocess exit code in `$status` and combined output in
`$output`/`${lines[@]}`. It returns zero to allow assertions. Its subprocess does
not preserve variable assignments in the parent test.

```bash
@test "command fails with the documented status" {
    run "$SCRIPT" --invalid-option
    [ "$status" -eq 2 ]
    [[ "$output" == *"invalid option"* ]]
}

@test "multiline output remains ordered" {
    run printf 'line1\nline2\nline3\n'
    [ "$status" -eq 0 ]
    [ "${lines[0]}" = 'line1' ]
    [ "${lines[1]}" = 'line2' ]
    [ "${lines[2]}" = 'line3' ]
}
```

If supported by the selected version, `run --separate-stderr` exposes distinct
stderr fields; `run --keep-empty-lines` preserves empty records. Implicit status
arguments such as `run -0` and `run !` are also version-dependent alternatives.

Do not write `run command | formatter`: the pipe is parsed outside `run`, and
the formatter does not receive the captured output as intended. Use a selected
version's `bats_pipe` or an explicitly invoked, controlled shell pipeline with
the intended producer-status handling. A reporter or `tee` must not mask failure.

## Per-test and shared fixtures

Use Bats-managed temporary directories appropriate to the resource lifetime:
`BATS_TEST_TMPDIR`, `BATS_FILE_TMPDIR` or `BATS_SUITE_TMPDIR` when supported.
Preserve caller-owned `TMPDIR`. Each test should own its paths and external state.

```bash
setup() {
    work_dir="$BATS_TEST_TMPDIR/work"
    mkdir -p "$work_dir" || return 1
    cp "$BATS_TEST_DIRNAME/fixtures/input.txt" "$work_dir/input.txt" || return 1
}

@test "fixture is processed without changing the original" {
    run "$SCRIPT" "$work_dir/input.txt" "$work_dir/output.txt"
    [ "$status" -eq 0 ]
    diff "$work_dir/output.txt" "$BATS_TEST_DIRNAME/fixtures/expected.txt"
}
```

For a selected Bats version without the needed managed variable, assign a
task-specific `mktemp` directory with an explicit failure check, then export it;
teardown removes only that owned directory. Do not combine fallible substitutions
with `local` or `export`, or delete an unvalidated caller-provided path.

Use `setup_file`/`teardown_file` only for truly shared resources. Declare their
ownership, failure cleanup and parallel-test exclusion. Avoid sharing writable
fixtures merely to make a suite faster.

## Dependencies and skip semantics

Use the built-in `skip` for an explicitly optional capability:

```bash
@test "optional jq formatting example" {
    if ! command -v jq >/dev/null 2>&1; then
        skip 'optional jq example: jq unavailable'
    fi
    run jq -r '.key' <<<'{"key":"value"}'
    [ "$status" -eq 0 ]
    [ "$output" = 'value' ]
}
```

A required dependency's absence remains missing/unavailable validation under
the project gate; skipping the test cannot establish that required behavior.
Preserve original failures and avoid broad skip/xfail policies for green CI.

## Files, permissions and platform coverage

Use fixed-format `printf` for byte-exact fixture creation. Assert content, size,
mode, owner or absence only when that property belongs to the contract. Select
GNU versus BSD `stat` options from the real target, rather than treating either
form as portable. An optional platform probe is not evidence for another OS.

Permission-denial integration tests require a suitable unprivileged identity,
ownership and filesystem semantics. Root, ACLs, mounts and container mappings can
change a `chmod 000` result. Restore test-owned modes in teardown; if the required
identity cannot be exercised, report the gap instead of manufacturing a denial.

Run the executable under each claimed shell explicitly. A Bash script is not a
POSIX sh script simply because Bats can launch both. Preserve minimum versions,
GNU/BSD utilities, external dependencies and the distinction between syntax and
behavior. Do not install another shell to avoid a supported-target failure.

## Concurrent child outcomes

Wait for each required PID; a final bare wait can return success despite child
failure. This self-contained assertion checks the failure path without a service:

```bash
@test "a failed required child fails the operation" {
    run bash -c '
        pids=()
        (exit 0) & pids+=("$!")
        (exit 17) & pids+=("$!")
        status=0
        for pid in "${pids[@]}"; do
            if wait "$pid"; then :; else
                child_status=$?
                if [[ "$status" -eq 0 ]]; then status=$child_status; fi
            fi
        done
        exit "$status"
    '
    [ "$status" -eq 17 ]
}
```

For actual asynchronous filesystem work, assert both every required child result
and the intended files. Define signal forwarding, ownership, deadlines and reaping
separately. File existence alone cannot establish successful concurrent execution.

## Helpers and narrow mocks

A shared assertion helper should preserve checked-command failure:

```bash
assert_file_equals() {
    local file="$1"
    local expected="$2"
    local actual
    [[ -f "$file" ]] || return 1
    actual=$(cat "$file") || return 1
    [[ "$actual" = "$expected" ]]
}
```

For external commands, prefer a deterministic test-owned stub executable placed
in a test-local `PATH`. Use a quoted heredoc or a fixed stub fixture so data is
not expanded into executable shell source. Configure stub output/status through
arguments or dedicated environment variables; keep real credentials absent.

Function mocks must be loaded/exported into the actual child environment when
that is how the tested code resolves them. Check calls, arguments and failure
semantics, not just canned output. Keep real provider/API compatibility tests
separate from local seam tests.

Generate large fixtures with a shell-compatible loop or a selected tool; do not
assume `seq` exists on every target. Independent per-test directories allow rerun
and parallel isolation without clearing unrelated shared state.

## Project-selected execution and CI

Invoke the existing project command and its selected paths. For a project using
Bats directly, current examples include `bats tests/`, `bats --tap tests/` or
`bats --verbose-run tests/`; use recursive selection when required by the real
layout. Verify options against the selected version's help.

Parallel execution uses `--jobs N` in current Bats and requires its selected
parallel backend. Use it only with independent fixtures and bounded resource
budgets. Do not silently add a backend, change CI schedules, replace pinned
actions or add a different test framework.

Retain actual command status when saving TAP or other reports. Report passed,
failed, skipped and excluded scope separately; test counts and an empty suite
are not proof of complete required coverage. Existing QA owns acceptance.

Primary references: [Bats test semantics](https://bats-core.readthedocs.io/en/stable/writing-tests.html)
and [CLI usage](https://bats-core.readthedocs.io/en/stable/usage.html). Resolve
version-sensitive behavior against the project's selected release.
