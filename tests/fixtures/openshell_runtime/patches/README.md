# Experimental workload Unix socket denial

This is a source-only patch for the operator-selected optional OpenShell trial.
It is not a built runtime, a qualified image, an upstream release, or an agent
activation route. Normal Codex and OpenCode sessions do not consume these files.

The comparison baseline is NVIDIA OpenShell `v0.1.6`, commit
`ac7f615cd12d5cc49cb16eb1f5f10ffeb1e90f47`. The upstream tag was resolved through
the [GitHub tag reference](https://api.github.com/repos/NVIDIA/OpenShell/git/ref/tags/v0.1.6),
then the exact commit's file and blob identities were checked. `source.json`
records the repository, immutable source URLs, Git blob IDs, byte counts, SHA256
hashes, patch hash, expected patched-source hash, and distinct experimental
identity `openshell-v0.1.6+dotfiles-ai.child-unix-deny.1`.

`upstream/child_seccomp.rs` is the complete, unchanged 21,098-byte preimage.
`upstream/LICENSE` is the unchanged 11,431-byte upstream Apache-2.0 license.
Both retain NVIDIA attribution and stay below the combined 1 MiB source budget.
They support offline application checks; this directory is not an upstream clone
or build tree. The original source is not installed or executed by those checks.

## Source change

The patch changes only
`crates/openshell-sandbox/src/linux/child_seccomp.rs`. In `prepare`, it adds two
conditional `EPERM` rules using the existing scalar-argument helper: deny
`socket(AF_UNIX, ...)` and `socketpair(AF_UNIX, ...)`, regardless of type and
creation flags. It updates the module contract and adds one isolated Rust test.
Existing process, signal, capability, namespace, descriptor, and Internet socket
hardening remain in place.

The filter is installed only in workload children. The trusted runtime must keep
its own Unix transport outside this filter. Socket creation denial does not
revoke an existing descriptor: the existing close-on-exec sweep for descriptors
above 2 and verified pipe/PTY standard streams remain essential. Do not replace
this change with a filter installed in the entire container or a wrapper that
runs after OpenShell's final filter.

The Rust test uses the existing test-binary subprocess pattern. The outer test
process checks that Unix socket creation works before and after the child. Only
the isolated child's test thread installs the irreversible filter; a second
child inherits it without reinstalling it. Both children test STREAM, DGRAM and
SEQPACKET against all CLOEXEC/NONBLOCK flag combinations for both syscalls, plus
nonzero upper domain bits. Internet socket creation and pipe IPC are positive
controls. Existing thread/process creation tests remain applicable. These tests
are source additions; they have not been compiled or run on Linux here.

## Offline checks and limits

From the dotfiles-ai checkout, use its already provisioned test environment:

```sh
.venv/bin/python -m pytest -q tests/test_openshell_child_patch.py
```

These checks validate attribution, size bounds, pinned Git/SHA256 provenance,
single-file patch scope, exact application, expected output hash, reversal,
duplicate application refusal, and refusal of missing or changed hunk context.
They require local Git and perform no downloads. The tests apply the patch only
to a disposable copy of the vendored preimage. A successful `git apply` alone is
not a source-identity check; source hashes must also match `source.json`.

Blank context lines in the patch use Git's accepted empty-line representation,
without a literal space prefix. This preserves context matching and the exact
patched bytes while passing the repository's trailing-whitespace checks. No
whitespace-ignoring option or repository whitespace exception is required.

Passing these checks proves text application only. It does not prove Rust type
checking, kernel syscall denial, descriptor isolation, trusted control-channel
availability, the full launch matrix, or either agent's compatibility. A macOS
source check cannot replace Linux execution. No toolchain installation, build,
VM startup, image replacement, provider access, or deployment is part of this
artifact's validation.

After a separately reviewed build baseline and admitted Linux environment exist,
the upstream test suite must include the new isolated test and existing child
hardening tests. For an already prepared complete Linux upstream checkout:

```sh
cargo test --locked -p openshell-sandbox linux::child_seccomp::tests -- --test-threads=1
```

This command is a future validation instruction, not evidence that it ran. Keep
the complete upstream filter/broker regression suite and the pilot's native
launch, descriptor, networking, editing, pause/resume, and recovery matrix. Test
initial and native exec with and without PTYs, descendants, descriptor passing
and acquisition, actual pathname/abstract socket attempts, restart/reconnect,
and independently observed trusted controller access before and after denial.
Both actual agents require their later compatibility matrix; broad Unix denial
can break legitimate client IPC.

## Build identity and maintenance

The initial comparison patch stays on the approved v0.1.6 generation. NVIDIA
[v0.1.7](https://github.com/NVIDIA/OpenShell/releases/tag/v0.1.7) retains the
relevant socket behavior but also updates vulnerable dependencies. Review and
select the actual build baseline before any native trial; this source delta
does not authorize building an older release or silently switching generations.

Any future experimental runtime must record its full upstream commit, exact
patch hash, build inputs/toolchain, binary hash, and OCI manifest/config digests.
It must not reuse an unchanged NVIDIA release identity. An upstream change to
this file, child launch order, descriptor handling, or internal transport requires
rebase review and renewed applicable evidence. Passing patch checks does not
qualify a substituted source file or waive these checks.

The authoritative scope remains
[the pilot runtime specification](../../../../docs/specs/dotfiles_ai_distribution/features/openshell-pilot.md#additional-isolation-investigation).
Storage admission precedes every VM experiment. No native qualification or agent
activation is claimed by this patch package.
