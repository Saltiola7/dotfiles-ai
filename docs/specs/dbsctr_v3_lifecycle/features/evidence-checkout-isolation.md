# Protect the checkout during evidence execution

Discovery contract, INT-124–125. Owner: lifecycle maintainer; critical risk,
Python and Security. `record-evidence` runs validators, including formatters
with repository-wide scope. `--path` selects Gate Commit outputs; it does not
describe all validation inputs and is not a filesystem boundary.

| Step | Required behavior |
|---|---|
| Capture | Freeze the actual candidate: HEAD, index including staged edits, unstaged overlay, modes, tracked absence and relevant nonignored untracked inputs. Reproduce the Git views the command uses; a clean copy of HEAD is insufficient. Respect private/ignored-data and source/toolchain binding rules. |
| Admit | Establish host-enforced write isolation for the command **and its descendants**. They can use private scratch, but cannot modify original working files (including untracked files), the real index, common Git state/refs, or lifecycle custody through any path. A linked worktree or a change of working directory alone is insufficient. If fidelity or isolation is unavailable, refuse before starting the command and explain why. |
| Execute | Use the approved literal command in the isolated candidate; preserve timeout, bounded output, environment identity and existing runtime-evidence output channel. The parent remains the sole canonical evidence writer. A command cannot gain credentials or mutation permissions it did not already have. |
| Accept | Hash the candidate inputs and recheck the original candidate before attaching evidence. Report mutations to candidate source/index even if the child exits zero. A command that passes only after fixing the scratch candidate supplies no passing evidence for the original. Ordinary disposable test output in approved scratch is allowed. Failed/unavailable execution retains its real disposition and downstream invalidation rules. |

Test a real formatter-style fixture with staged and unstaged versions of one
file, an untracked candidate input and unrelated dirty work. Exercise a child
writing by absolute path, a hook subprocess, an unavailable confinement
mechanism, nonzero and zero exits after modifying scratch, timeout and original
input drift. Compare original bytes, modes, index, refs and unrelated work.
Run one read-only passing authority on the same candidate to prove this is not
merely a blanket refusal. Missing host capability is a blocker for that host,
not permission for a live-checkout fallback or automatic restoration.

Use the existing [evidence bindings](workflow-evidence-bindings.md) and gate
transitions. No installation or new runner service follows from this source
contract. Old envelopes retain their historical meaning.

The Linux source implementation requires a non-setuid, system-owned
`/usr/bin/bwrap`, libseccomp, and host policy that permits the required
namespaces. It does not change host policy or fall back to the live checkout.
The validator runs with a read-only host view, an isolated network and PID
namespace, and writable private scratch. Host Unix sockets are unavailable.
This is write isolation, not a confidentiality boundary for files the caller
can already read. Use scratch for generated output and tools that need a
writable cache. Ignored files are not copied into the candidate. Unsupported
index or file layouts are refused rather than approximated.

## Visual Evidence

Boundary, interaction and data/trust: **required**, the table identifies the
parent, child, writable scratch and protected state in execution order.
State and schema: **not applicable**, existing gate dispositions and envelope
owners suffice. Dependency/deployment: the [handoff](../../../initiatives/dbsctr-workflow-convergence/BUILD-HANDOFF.md#publication-and-evidence)
owns source sequencing; no selected host backend is claimed. Quantitative:
**not applicable**, no throughput claim.

**Text Equivalent:** Only the parent can attach evidence. The child runs on a
faithful candidate with enforced write isolation, or is not run at all. A
modified candidate cannot pass for the original. The lifecycle maintainer
updates this table when execution, capture or write guarantees change.
