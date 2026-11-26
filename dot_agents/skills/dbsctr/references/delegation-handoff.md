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

## Same-repository workers in ordinary Plan and Build

In Plan, Discovery presents the whole selected plan for one review, including
blocked slices. In Build, DBSCTR reads that durable plan. For batch dispatch,
verify that the installed grant covers the exact plan and draft delivery.
If batch authorization is unavailable, report that limitation before launch.
An approved planning document alone cannot register cycles.

On an enrolled host, carry the exact claims, approved-at and expiry from
`draft-worker-batch preview` into `accept --approval agent-confirmed` only
after the operator approves that digest. Resume with `build --grant` rather
than creating another session. Inside a registered worker use `dbsctrctl
draft-worker-batch scope` to read its reviewed inputs. Outside Herdr, report
the native session ID and checkout for each slice. Inside Herdr, attach a
named Herdr tab to each reported top-level Build session. Announce the slice, tab and branch
even when opening tabs without focus. Confirm Build mode, native session ID,
workdir, branch and base before registration. Give shell calls the explicit
workdir. Timing is optional. Each worker owns one Cycle Record.

After interruption, reopen the original session by session ID and read its
checkout and Cycle Record before continuing. Verify gate evidence and the
published head before accepting delivery. Publish drafts serially; if main
advances, reconcile and verify fresh exact-candidate CI before protected merge.

For top-level slice workers, select the route from the orchestrating agent.
From `build-claude`, start each worker as `build-claude` with an explicit
`google-vertex/claude-sonnet-5-5@default` model override and medium variant;
the orchestrator keeps its Opus default. From native `build`, start `build`
with `openai/gpt-6.2-sol` and medium variant. Verify agent, provider, model
and variant by session readback before handing off the slice. Do not invoke
a model-pinned slash command that would override the worker selection.
