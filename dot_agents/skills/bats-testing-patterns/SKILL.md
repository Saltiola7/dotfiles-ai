---
name: bats-testing-patterns
description: Design and debug Bats fixtures, subprocess assertions, shell compatibility and integration tests when the project selects Bats or explicitly evaluates it.
---

# Bats Testing Patterns

Use for Bats test design or a selected Bats evaluation. Existing pytest/subprocess,
shunit2 or other project authorities remain valid. Loading guidance does not
select a new test framework, install dependencies or rewrite CI.

## Resolve the test contract

Read the script's executable/sourced contract, selected Bats version and helpers,
shell targets, operating systems and existing test command. Test behavior through
that authority; use supported helpers instead of assuming an add-on is loaded.

Distinguish success/failure status, stdout/stderr, filesystem effects, environment
changes, signals, required child outcomes and authorized external dependencies.
`run` captures a command's result and itself succeeds so assertions can follow.
Inspect `$status`; output matching alone does not establish command success.

## Choose the relevant pattern

| Concern | Method |
|---|---|
| CLI behavior | `run` the executable; assert the relevant status, streams and effects |
| Sourceable function | Load a deliberate library with controlled setup; preserve caller state |
| Fixtures | Prefer Bats-owned per-test directories and isolated data |
| Mocks | Replace a narrow dependency seam; verify real integration separately |
| Compatibility | Execute only claimed dialect/version/platform combinations |
| Concurrent work | Wait for every required PID and preserve failure |
| Shared resources | Explicit ownership and cleanup; parallel execution only when independent |

Use Bats-owned `BATS_TEST_TMPDIR` when supported by the selected version rather
than rewriting caller-owned `TMPDIR`. If a custom directory is necessary, check
`mktemp` before exporting its path; `local`/`export` can mask substitution failures.

Keep assertions close to the behavior that matters. Check failure semantics and
recovery as well as happy paths, without duplicating implementation details.
Fixtures should distinguish missing input, invalid input and actual authorization
failure where those outcomes have different contracts.

## Evidence limits

- A missing required tool or unsupported target remains a capability gap. Use
  `skip` only for explicitly optional coverage, with its reason visible.
- Permission-denial tests need an appropriate unprivileged identity and filesystem;
  `chmod 000` does not reliably deny an administrator or every mount type.
- A Bash-only script is not required to run under sh/dash. Bats itself runs in
  Bash; a subprocess target establishes the script's actual dialect coverage.
- A mock proves the selected seam's behavior, not provider compatibility, host
  privilege, cluster acceptance or deployment readiness.
- Bare `wait` can hide failed children. Successful file creation does not prove
  every background operation succeeded.

## Supporting patterns

Read [detailed patterns](references/details.md) for `run` status/stream handling,
fixtures and lifecycle, mocks, permissions, concurrent children, helper functions
and project-selected CI. Consult the selected Bats `--help` before using versioned
flags or optional parallel/reporting dependencies.

Preserve existing CI pinning, schedules, framework and installation authority.
Run the affected project command; report actual passed/failed/skipped scope and
unavailable required evidence. Return findings to the existing primary and QA;
this skill owns no new gate, commit or deployment workflow.
