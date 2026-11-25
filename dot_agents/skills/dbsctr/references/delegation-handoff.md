# Plan delegation from the work

Discovery includes this handoff without an operator prompt. Build consumes it
from the approved artifacts; the operator should not have to assign helpers.

1. Give each task an outcome, target, prerequisite evidence, writable paths
   and shared resources. Record the validation authority, intended output
   and who may deliver it. Name dependencies by task, not by session ID.
2. Group tasks that are ready together. Keep one writer for an overlapping
   path, generated output, fixture, or shared resource. A cycle in the graph
   or an unknown owner is blocked: give the unresolved edge and the decision
   needed. Keep a small change with one writer when splitting offers no gain.
3. Recommend separate sessions for independently useful work with its own
   checkout and owner. State which evidence allows each fork to start.
   A fork inherits context, not an executable grant or a reserved worktree.
   Preserve the controller's serial-per-target limit until more concurrency
   is qualified. The existing execution DAG governs eligible read-only work.
4. Match the task to tools actually available to that role. In Discovery,
   delegate research and explicitly owned documentation. In Build, give an
   eligible coding helper its checkout, owned and off-limits paths and test
   selection. If a permission is denied, return findings to the primary.
   Do not retry the operation with another tool. Unavailable capability is
   not a failed test.
5. Return the change and evidence reference, tested revision/tree and inputs,
   command, environment/toolchain, result, and known omissions. Reuse a
   qualified receipt when policy proves it still applies. A text summary
   is useful for diagnosis; it is not gate evidence. A changed input needs
   fresh validation. Local test success cannot replace required CI.
6. Report delivered count over the reviewed slice count, each slice's state,
   reason and next action. Reuse the Initiative tally when available. A
   draft PR can satisfy draft delivery; a dependent requiring a merge waits
   for verified inclusion. Route CI feedback to its owning writer and apply
   the existing repair limit.

For example, a schema writer in one repository and a caption writer in a
second can proceed independently if their target policies allow it. A reader
that needs both merged waits for both revisions even if both drafts exist.
If two proposed writers instead need the same fixture, draw an ordering
edge or give it to a single owner before dispatch.

The existing primary retains restricted lifecycle and forge operations.
Use end-to-end child writers and a single inherited approval only after the
native writer and Initiative grant are qualified for the selected mode and
target. Discovery recommendations do not make that qualification true.
