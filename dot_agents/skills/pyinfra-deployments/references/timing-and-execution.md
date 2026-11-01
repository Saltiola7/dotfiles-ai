# Pyinfra Timing and Execution

The official v3.10.0 sources below ground these details; they do not select or
upgrade the project's runtime. Confirm older or newer behavior through the
installed help and matching API/source when it changes a decision.

## Preparation is real execution of local Python

Pyinfra loads inventory and data, connects to selected hosts, prepares operations,
executes them and disconnects. During preparation, the deploy file runs locally
once per host. Normal facts query target state and cache their results. Operations
use that state to establish their ordering and whether work is proposed.

Preparation is not a complete stored list of shell commands. At execution time,
pyinfra evaluates each operation again to generate its commands. Under the normal
strategy, an operation finishes across its hosts before the next operation runs;
do not assume a whole deploy completes on one host before starting another.
Inspect selected concurrency settings when a rolling change needs that guarantee.

Deploy imports, inventory construction, local calls and custom facts can have
their own effects. `--dry` does not make arbitrary Python safe to execute or
prevent host connections and fact reads. Review those inputs before running them.

## Use the right condition at the right time

A Python branch on host metadata such as OS or group can choose appropriate
operations. A branch on mutable state that an earlier operation will change sees
preparation-time state and can skip necessary work on the first run.

Prefer declaring the desired state directly when the operation already handles
absence or equality. For an effect that depends on a prior actual change, use an
execute-time callable supported by the selected version: for example,
`_if=config_operation.did_change`, not `_if=config_operation.did_change()`.
`will_change` describes the proposal; it is not proof that an operation ran.

Operation output is unavailable before execution. Consume it through supported
runtime callbacks or result handling rather than reading `stdout` immediately in
deploy code. Do not assume wrapping a cached fact in a lambda independently
refreshes it; verify the fact's cache and operation-update semantics when fresh
state is essential.

## Preview without inventing stronger guarantees

For the selected version, inspect `--dry`, `--debug-operations`, `--diff`, host
limits and exclusions. Quote host patterns so the local shell does not expand
them. Confirm the effective selection rather than inferring it from a group name.

Dry and debug-operation output describe proposed operations and affected hosts,
not every literal command that will execute. `-vv` exposes commands during actual
execution; it is not a way to obtain a harmless complete shell preview. Text-file
diff support does not prove package, service or arbitrary shell effects.

In v3.10.0, `--json` emits structured stdout; a deploy without `--yes`, or with
`--dry`, remains a proposal. Do not generalize that behavior to an unchecked
version. Preserve stderr and the real process status; JSON availability or parse
success does not establish deployment success. Inventory data and high verbosity
can expose secrets, so capture only relevant non-secret evidence.

## Convergence and recovery

Declarative operations compare desired state with available facts; imperative
operations such as `server.shell`, `server.script` and `python.call` normally run
each time unless explicitly conditioned. Justify their repeated effects and
failure boundaries. A second clean dry run supports convergence only for its
actual inputs, fact coverage and selected hosts.

After a failure, retain which hosts and operations completed. An operation can
have partially changed a host before failing. Inspect actual state and any
application migration contract before retrying; retries are not rollback, and
ignored errors are not recovery. Keep service health and persistent-data checks
separate from pyinfra's execution status.

## Official references

- [Version-pinned deployment model](https://github.com/pyinfra-dev/pyinfra/blob/v3.10.0/docs/deploy-process.md)
- [Version-pinned operation guidance](https://github.com/pyinfra-dev/pyinfra/blob/v3.10.0/docs/using-operations.md)
- [Version-pinned CLI guide](https://github.com/pyinfra-dev/pyinfra/blob/v3.10.0/docs/cli.md)
  and [CLI implementation](https://github.com/pyinfra-dev/pyinfra/blob/v3.10.0/src/pyinfra_cli/cli.py)
- [Global arguments](https://docs.pyinfra.com/en/3.x/arguments.html) and
  [versioned documentation index](https://docs.pyinfra.com/en/3.x/llms.html)
