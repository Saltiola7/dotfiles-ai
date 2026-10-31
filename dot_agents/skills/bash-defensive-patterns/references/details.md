# Bash defensive patterns: worked decisions

Read only the sections relevant to the current shell contract. Examples target
Bash 3.2+ unless explicitly qualified; they do not establish POSIX sh support or
GNU/BSD utility parity. Commands that change files or processes remain within
the current task's authorization.

## Shell options and status boundaries

Select shell options deliberately, especially in sourced code. `set -e` does not
exit for every nonzero status: conditionals, `!`, lists, pipelines, functions and
subshells have important exceptions. `ERR` follows related exceptions. `pipefail`
changes pipeline semantics; `nounset` can break legitimate optional inputs.

Use explicit checks where the result determines correctness:

```bash
if generate_report "$input_file" "$output_file"; then
    printf '%s\n' 'Report generated' >&2
else
    report_status=$?
    printf 'Report generation failed (%s)\n' "$report_status" >&2
    exit "$report_status"
fi
```

Retain a failed command's status before logging another command. Do not combine
a fallible substitution with `local`, `readonly` or `export`, whose own status
can hide the failure:

```bash
find_runtime() {
    local runtime_path
    runtime_path=$(command -v python3) || return 1
    printf '%s\n' "$runtime_path"
}
```

When output travels through `tee` or another formatter, preserve the intended
producer status using the selected shell's pipeline facilities. A process
substitution's producer status is not automatically the consuming command's
status; use a checked intermediate result or explicitly owned process when that
failure matters.

## Owned temporary state and signals

Do not repurpose `TMPDIR`: other commands and callers may depend on its original
meaning. This executable-script example creates one owned directory; its cleanup
does not select or delete unrelated paths:

```bash
#!/usr/bin/env bash

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/report-work.XXXXXX") || exit 1

cleanup() {
    local original_status="$1"
    if [[ -n "${work_dir:-}" && -d "$work_dir" ]]; then
        rm -rf -- "$work_dir" || printf '%s\n' 'Temporary cleanup failed' >&2
    fi
    return "$original_status"
}

trap 'cleanup "$?"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf '%s\n' 'temporary content' > "$work_dir/input.txt" || exit 1
```

Adapt signal codes and cleanup policy to callers; a sourced library should not
replace its caller's traps or call `exit` unexpectedly. If cleanup failure is
itself material, define its precedence without concealing the original failure.
The `mktemp` form and `rm --` support still need the selected platform authority.

## Arguments, paths and parsing

Quote data expansions and preserve argv boundaries with arrays in Bash:

```bash
copy_args=(-p)
copy_args+=("$source_file" "$destination_file")
cp "${copy_args[@]}"
```

This assumes the source cannot be interpreted as an option; otherwise use a
supported `--`, normalize an owned relative path, or the utility's documented
argument mechanism. Quoting alone does not prevent option interpretation.

Validate option values before reading them:

```bash
output_file=''
jobs=1

usage() {
    printf 'Usage: %s --output PATH [--jobs N]\n' "$0"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -o|--output)
            [[ $# -ge 2 && -n "$2" ]] || {
                printf '%s\n' 'Missing output path' >&2
                exit 2
            }
            output_file=$2
            shift 2
            ;;
        -j|--jobs)
            [[ $# -ge 2 && "$2" =~ ^[1-9][0-9]*$ ]] || {
                printf '%s\n' 'Jobs must be a positive integer' >&2
                exit 2
            }
            jobs=$2
            shift 2
            ;;
        --) shift; break ;;
        -h|--help) usage; exit "$?" ;;
        *) printf '%s\n' 'Unknown option or argument' >&2; exit 2 ;;
    esac
done

[[ -n "$output_file" ]] || { printf '%s\n' 'Output is required' >&2; exit 2; }
```

Select a range/budget for `jobs` from the actual workload. Named `--input=value`
forms can use `${1#*=}`; validate the resulting value and unknown names under the
same contract. Do not log an arbitrary unknown argument if it may contain a secret.

For script location, decide whether symlink invocation and sourced-file location
matter before using `${BASH_SOURCE[0]}` plus `dirname`/`pwd -P`. Those utility
options and symlink semantics are platform-specific.

## Reading records and arrays

`mapfile` and `readarray` require Bash 4+. A Bash 3.2 line-reader can use:

```bash
lines=()
while IFS= read -r line || [[ -n "$line" ]]; do
    lines+=("$line")
done < "$checked_input_file"
```

This preserves a final unterminated line but is a text-record pattern, not a
filename encoding. Use NUL-delimited records for arbitrary filesystem names when
the selected producer and shell support them. Do not parse `ls` output. Check
producer success separately before consuming an intermediate file when required.

## Required child outcomes and interruption

Retain only owned, unreaped PIDs. Bare `wait` can return success after a child
fails; collect each required result and still reap the other children:

```bash
#!/usr/bin/env bash

child_pids=()

stop_children() {
    local child_index child_pid
    for child_index in "${!child_pids[@]}"; do
        child_pid=${child_pids[$child_index]}
        kill -TERM "$child_pid" 2>/dev/null || :
    done
    for child_index in "${!child_pids[@]}"; do
        child_pid=${child_pids[$child_index]}
        wait "$child_pid" 2>/dev/null || :
    done
}

on_interrupt() {
    trap '' INT TERM
    stop_children
    exit "$1"
}

trap 'on_interrupt 130' INT
trap 'on_interrupt 143' TERM

worker alpha &
child_pids+=("$!")
worker beta &
child_pids+=("$!")

overall_status=0
for child_index in "${!child_pids[@]}"; do
    if wait "${child_pids[$child_index]}"; then
        :
    else
        child_status=$?
        if [[ "$overall_status" -eq 0 ]]; then
            overall_status=$child_status
        fi
    fi
    unset "child_pids[$child_index]"
done
exit "$overall_status"
```

The illustration defines `worker` in the consuming program. It handles direct
children; descendants, process groups, graceful-shutdown deadlines and escalation
need the owning launcher contract. A timeout or signal must not imply that all
external work stopped. Avoid broad `pkill`/`killall` matching unrelated processes.

## Filesystem writes, ownership and reruns

Check existence, readability, directory types and destination ownership where
they are real preconditions. A preflight existence check followed by `mv` is not
race-free no-clobber protection. Use the platform's supported atomic no-replace
mechanism if concurrent creation is part of the contract.

Write replacement content on the target filesystem before renaming:

```bash
atomic_write() {
    local target="$1"
    local candidate
    candidate=$(mktemp "${target}.XXXXXX") || return 1
    if ! cat > "$candidate"; then
        rm -f -- "$candidate"
        return 1
    fi
    if ! mv -- "$candidate" "$target"; then
        rm -f -- "$candidate"
        return 1
    fi
}
```

This allows replacement and illustrates same-filesystem rename only. Define
symlink, ownership, permissions, ACL/xattr, concurrent-writer and durability
requirements before using it. It does not promise preservation of old metadata
or crash durability. Interactive deletion flags differ across GNU/BSD systems;
an unattended script needs an explicit bounded deletion contract.

For idempotency, compare intended state before a change, then verify its result.
An existing directory or configuration file is not evidence that its mode,
owner or contents meet the requirement. Avoid silently overwriting live edits.

## Logging, preview and dependencies

Prefer `printf` with fixed format strings. Select output streams, timestamps and
verbosity according to the caller; redact credentials, tokens and sensitive paths
or arguments. `set -x` and naive `$*` logging can expose secrets.

A dry run should expose reviewed intended effects without executing them. Render
argument boundaries accurately and redact sensitive values; a printed command is
not proof that the actual argv or eventual execution will match.

Use `command -v` for selected dependencies and report missing capabilities. Do not
install packages, change `PATH` globally or replace the selected shell merely to
make a pattern run. Test the chosen GNU/BSD utilities and shell versions, actual
failure/exit behavior, cleanup, interruption and concurrent child outcomes.
