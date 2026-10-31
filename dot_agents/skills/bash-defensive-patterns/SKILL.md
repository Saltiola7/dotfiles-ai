---
name: bash-defensive-patterns
description: Design and review shell execution, cleanup, signal handling, subprocess status and portability for substantive Bash changes, preserving the project's dialect, supported versions and validation authority.
---

# Bash Defensive Patterns

Use for changed shell execution semantics, subprocess orchestration, filesystem
operations or substantial script refactoring. A trivial text edit need not load
the detailed patterns.

## Establish the execution contract

- Read the shebang, callers, tests and deployment targets. Distinguish executable
  scripts from sourced libraries, and Bash from POSIX sh or zsh.
- Preserve the selected minimum shell and utility versions. macOS `/bin/bash`
  may be 3.2; Bash 4+ features are conditional, not permission to install a shell.
- Identify expected exit codes, output streams, signal behavior, partial-success
  policy, filesystem ownership and rerun behavior before changing them.
- Keep project-selected tests and linting. ShellCheck diagnostics and suppressions
  remain evidence under that authority; loading this skill installs nothing.

## Decisions that matter

| Concern | Preserve or establish |
|---|---|
| Errors | Explicit status checks at important boundaries; failures remain visible |
| Shell options | Choose `errexit`, `nounset`, `pipefail` and traps for the actual caller contract |
| Arguments | Quoted expansions, arrays for argv, validated missing option values |
| Temporary state | A checked, owned task-specific directory and bounded cleanup |
| Concurrency | Owned child PIDs, every required child status, cancellation and reaping |
| Files | Explicit overwrite/symlink policy, compatible utilities and atomicity limits |
| Reruns | Idempotent intended effects, with real error reporting |
| Logs / preview | Useful diagnostics and argument boundaries without secret values |

Strict mode is contextual. `set -e` has conditional, pipeline, function and
subshell exceptions; neither it nor an `ERR` trap proves every failure is handled.
Separate `local`/`export` declarations from fallible command substitutions so the
declaration's status does not hide the command's failure.

Use arrays for Bash argument vectors; use an appropriate POSIX representation
when sh is selected. Avoid `eval` or reconstructed command strings for ordinary
argument forwarding. `[[ ... ]]`, arrays and process substitution are Bash
features, not portable sh syntax.

Preserve caller-owned `TMPDIR`, `HOME`, `PATH` and other environment authorities.
Use a distinct temporary variable, check creation, and remove only owned state.
Treat paths beginning with `-`, whitespace, glob characters and symlinks according
to the selected utility and filesystem contract.

Bare `wait` does not aggregate failed child statuses. Retain PIDs, wait for each,
and propagate required failures. Forward interruption and reap owned children;
cleanup is not a reason to convert a failure or signal into success.

## Read detail when needed

Read [detailed patterns](references/details.md) for contextual shell options,
temporary-state cleanup, argv/parsing, child-status collection, filesystem writes,
idempotency, logging and dependency checks. Examples are scoped illustrations;
adapt them to the actual shell, utilities and authorization.

Validate meaningful error, signal, rerun and compatibility paths through the
project's configured authority. Report tested targets, actual statuses and any
unavailable platform evidence. Syntax checking alone does not prove behavior.

Return the affected contract, smallest justified change, actual checks and
remaining limitations to the existing primary. This skill owns no lifecycle,
installation, commit or deployment workflow.
