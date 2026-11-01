# Runtime boundaries

Read the relevant section for the selected execution model. Match APIs to the
project's exact Python version and operating system; these are review decisions,
not a requirement to migrate to Python 3.14.

## Start methods and worker state

Python 3.14 changed the POSIX default away from `fork`; macOS and Windows use
`spawn`. Inspect the actual runtime/platform rather than relying on inherited
globals. With `spawn` or `forkserver`, qualify imports, initialization, picklable
payloads and context-compatible locks. An explicit `fork` choice needs evidence
for the application's threads and native libraries. Keep parent-owned network
connections and database pools out of worker payloads.

Worker recycling can help a measured leak, but changes startup costs and resource
initialization. Check support and start-method compatibility for the selected API;
do not use recycling to hide failed cleanup. Preserve results and stop conditions
when workers fail during a batch.

Primary reference: [multiprocessing contexts and programming guidelines](https://docs.python.org/3.14/library/multiprocessing.html).

## Subinterpreters

`InterpreterPoolExecutor` requires Python 3.14+. Workers run in separate
interpreters within threads, with independent imports/runtime state. Callables,
arguments and results are serialized; mutable Python objects are not shared as
ordinary thread-owned references. Qualify native-extension support and any
process-wide native state rather than assuming interpreter isolation is a security
sandbox. There is no process-pool terminate/kill API for an individual interpreter.

Primary reference: [concurrent.futures executors](https://docs.python.org/3.14/library/concurrent.futures.html).

## Shared memory and IPC

Name the allocation owner, every attached handle, synchronization discipline and
last-reader lifetime. Close each handle; assign one unlink owner when the block is
no longer needed. Release exported views before closing their backing memory.
Closing a handle and unlinking the underlying allocation are different operations,
with platform-specific effects.

`SharedMemory(track=...)` was added in Python 3.13. Unrelated Python processes can
have separate resource trackers, so the first exiting tracker can unlink memory
that another process still needs. Use `track=False` only when an identified owner
already performs bookkeeping; do not disable tracking as a generic leak fix.
Bound queue/pipe payloads and drain required producer output before joins to avoid
deadlocks. Abrupt termination while using queues or locks needs explicit recovery.

Primary reference: [shared-memory lifetime and tracking](https://docs.python.org/3.14/library/multiprocessing.shared_memory.html).

## External subprocesses

With `Popen`, a `communicate(timeout=...)` exception does not kill the child.
An owner that chooses termination must then drain/wait and preserve the original
failure. `run(timeout=...)` kills and waits for its child, but process creation and
descendant cleanup have their own platform limits. Do not claim a hard wall-clock
deadline or whole-process-tree shutdown from a child-only operation.

Pipe deadlocks and output volume are separate concerns: `communicate()` drains
pipes but buffers output in memory. Large or unbounded output requires an owned,
bounded streaming or file strategy. Prefer argument lists and validate executable
selection and inputs under the project's existing command contract.

Primary reference: [subprocess pipe and timeout behavior](https://docs.python.org/3.14/library/subprocess.html#subprocess.Popen.communicate).
