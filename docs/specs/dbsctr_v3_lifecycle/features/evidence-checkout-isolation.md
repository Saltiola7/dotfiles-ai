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

## Repository-local symbolic links

`EVIDENCE-SYMLINKS-001` is a critical-risk Python and Security source slice
under the [Engineering Profile](../PROFILE.md). A tracked Linux systemd
enablement link exposed a capture limitation: the host namespace probe passed,
but the regular-file-only inventory refused the checkout before validation.
Keep that link in the consumer repository. Fix capture in the shared helper.

| Given | When | Required outcome |
|---|---|---|
| A tracked relative symlink directly resolves to a captured regular file | A validator reads the checkout | Reproduce the link as a symlink with its literal target; preserve the index entry and capture the working overlay separately. |
| A supported link or its target changes during validation | The helper evaluates a result | Admit no passing evidence for the original candidate if the original inputs drift or the validator leaves changed candidate inputs. |
| A link target is absolute, escapes the checkout, depends on an uncaptured path, resolves through another link, or is not a captured regular file | The helper evaluates capture | Refuse before launch. Never follow the link to copy target data or flatten the link into a regular file. |
| Capture or sandbox setup is unsupported | The helper reports the refusal | Keep the unavailable result and existing error category. Add a bounded reason without paths, link text, or sandbox internals. |

Preserve staged link modes and blob identities in native Git views. For the
working overlay, bind link kind and target bytes independently of regular-file
contents; normalize for containment checks, not for reconstruction. Apply the
same capture and recheck rules to staged additions, unstaged target changes,
and tracked deletions. Only tracked working-tree links are added to the
supported layout; untracked symlinks, link-valued parent directories, split
indexes and submodules remain unsupported. Do not broaden Gate Commit output
path eligibility when admitting links as checkout inputs. Keep the existing
Bubblewrap and seccomp policy, historical evidence and record schema.

One Build owner changes the helper, this contract and focused regression
tests. First reproduce the failure using a synthetic systemd-style relative
link. Then prove native Git and working-overlay fidelity, refusal of unsupported
links before child startup, link mutation/drift rejection, and continued
write isolation in the existing descendant and formatter regressions. Use
local Linux and the existing Ubuntu CI authority; no new CI or host policy.

Kernel, Review/Integrate and Maintain/Retire are required. Release, Deploy and
Operate are not applicable to the source-only draft PR. After protected merge,
separately approve managed installation and first-consumer qualification on
Linux. Then retry the blocked evidence gate in the existing consumer cycle
without dropping its unavailable receipt. No Forgejo dependency, Mac deployment,
or change to the consumer repository's service link belongs to this slice.

## Visual Evidence

Boundary, interaction and data/trust: **required**, the capture table identifies the
parent, child, writable scratch and protected state in execution order.
State: **required**, the symbolic-link table shows admission and rejection.
Schema: **not applicable**, the extension does not change record schemas.
Dependency/deployment: **required**, follow the source, managed installation
and consumer retry order above and the existing
[handoff](../../../initiatives/dbsctr-workflow-convergence/BUILD-HANDOFF.md#publication-and-evidence).
Quantitative: **not applicable**, no throughput claim.

**Text Equivalent:** Only the parent can attach evidence. The child runs on a
faithful candidate with enforced write isolation, or is not run at all. A
modified candidate cannot pass for the original. The symbolic-link table is
the canonical capture-state view for this extension: admit a tracked relative
link to a captured regular file without flattening it; refuse unsupported
targets before launch and reject passing evidence on link or target drift.
Separate source delivery, installation and consumer retry in that order. The
lifecycle maintainer updates these views when execution, capture, write
guarantees or rollout ordering changes.
