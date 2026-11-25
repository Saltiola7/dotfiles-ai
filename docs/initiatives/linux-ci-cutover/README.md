# Linux CI cutover

Status: two of three slices delivered; `rhel-surface-lanes` is ready for
build. `macos-workstation-retirement` made the source Linux-native — the
Try Omarchy VM is the AI workstation, the darwin agent stack and the lima
subsystem are deleted — and the cutover then moved the validation plane to
Linux hosted runners. No job in this repository requires a macOS runner.
What remains is the RHEL-family surface lane and the aarch64 parity lane.

## Why now

At Discovery the retirement initiative had removed every macOS-only managed
surface and verified the replacement services live on the VM, yet
`.github/workflows/test.yml` still selected `macos-26` for the full suite.
The macOS fleet admitted 1–2 jobs at a time and reclaimed runners mid-run
throughout the qualification history of this quarter (steps that never
concluded, log blobs missing, zero test failures). GitHub-hosted Linux
runners admit an order of magnitude more concurrency with no observed
reclamation. The longest-running qualification lanes stop being the
eviction maximum once they run there.

## Context map

| Context | Home | Change |
|---|---|---|
| dbsctr_v3_lifecycle | Saltiola7/dotfiles-ai | full-suite workflow matrix → Linux runners; qualification test fixes; cutover ordering |
| dotfiles_ai_distribution | Saltiola7/dotfiles-ai | RHEL-family surface lane (quadlet, systemd user-unit and install-script rendering) and platform profile truth |

Related initiatives, deliberately not duplicated here:

- `macos-workstation-retirement` — predecessor; removed the darwin and
  lima machinery and made the VM the verified workstation.
- `openshell-pilot` — agent sandboxing on rootless podman; resumes from
  its recovered authority on the Linux substrate (see INT-012).
- `rhel-remote-workspace` (coordinator repository, company scope) — the
  cross-repo RHEL remote-workspace authority; this initiative only reads
  its target as a validation reference (INT-011).

## Statements

| ID | Kind | Summary |
|---|---|---|
| INT-001 | requirement | Full suite runs on GitHub-hosted Linux runners (ubuntu-24.04, x86_64); partitions keep the complete collection; no second worktrunk axis. |
| INT-002 | constraint | The same-attempt receipt verifier and aggregate lane-coverage checks are preserved unchanged; only full-run reruns satisfy them. |
| INT-003 | requirement | The uv setup step uses cache and retry so a tool fetch cannot kill a partition before tests run. |
| INT-004 | decision | Branch-protection required contexts are replaced exactly once at cutover by the owner; strict require-up-to-date and enforce_admins are preserved. |
| INT-005 | requirement | The durable qualification fixes (per-architecture codex wrapper fixture pin; load-tolerant capture-latest bound; widened smoke-benchmark runaway guard) and the completion-binding `input_capture_unavailable` triage land with the cutover so the new matrix starts green. |
| INT-006 | decision | PR #315 closes as superseded once its durable fixes are folded; its macOS-lane qualification is not completed. |
| INT-007 | requirement | A RHEL-family surface lane in `registry.access.redhat.com/ubi10/ubi` container jobs qualifies quadlet generation, systemd user-unit rendering and install scripts on affected changes. UBI 10 is the only lane image. |
| INT-008 | requirement | An aarch64 parity lane runs the full suite on the hosted arm64 Linux runner (`ubuntu-24.04-arm`, free for public repositories); the replacement workstation is aarch64. |
| INT-009 | decision | Substrate policy: RHEL-grade primitives first — rootless podman, quadlet, systemd user units, SELinux where native — distro deltas isolated, no core dependence on rolling-release-only behavior, floating tooling pinned. |
| INT-010 | decision | Portable isolation baseline: rootless podman with user namespaces and seccomp; SELinux volume labeling and custom types are the RHEL enhancement layer; custom policy generation stays deferred. |
| INT-011 | constraint | The operational RHEL remote workspace (shared with a colleague) is a read-only-first validation reference coordinated through the rhel-remote-workspace authority; this initiative changes nothing on it. |
| INT-012 | constraint | OpenShell agent-session work continues in the `openshell-pilot` initiative, amended for the Linux-native substrate with a pinned current release; its acceptance feeds RRW-H03. Deferred here, not duplicated. |
| INT-013 | constraint | Non-goals: paid or larger runners; weakening the receipt verifier; re-introducing a lima path on macOS (superseded by the retirement); pm-kernel internals; any mutation of the RHEL remote workspace. |
| INT-014 | risk | Protection-window mismatch during context replacement can block merges; mitigated by the owner-performed single edit ordered with the cutover merge. |
| INT-015 | risk | Shared Linux runners contend; folded timing bounds and runaway guards carry over and partitions size for headroom. |
| INT-016 | decision | UBI 10 is the only lane image (owner decision 2026-11-24). An earlier draft named UBI 9, which disagreed with the cross-repository RHEL remote-workspace decision and with the image the merged remote-user workflow runs. |
| INT-017 | decision | The aarch64 parity lane reports without failing the pull request until the owner adds it to the required contexts. |
| INT-018 | decision | The lanes live in their own workflow files; the full-suite workflow and its five required contexts stay as the cutover left them. |

## Delivery record

| Slice | State | Evidence |
|---|---|---|
| `linux-matrix-rewrite` | delivered | PR #331, merge `0824bbe1`: workers and the aggregate verifier on `ubuntu-24.04`, four partitions, receipt verifier unchanged. The owner replaced nine required contexts with five Linux contexts; the default branch runs Linux-only. |
| `qualification-fixes-fold` | delivered | In the same merge: `72264967` codex wrapper fixture pin, `7eb71f13` capture-latest timing bound, `7921ca48` smoke-benchmark runaway guard, and the capture-path failure fix in `record-evidence`. PR #315 is closed as superseded. |
| `rhel-surface-lanes` | ready | Not started. Contract: [`features/rhel-surface-lanes.md`](../../specs/dotfiles_ai_distribution/features/rhel-surface-lanes.md). |

## Validation strategy

1. `linux-matrix-rewrite`: the rewritten matrix is green on the exact head
   in one attempt with the receipt verifier intact; no job requests a
   macOS runner (`grep`-provable in the workflow file).
2. `qualification-fixes-fold`: every folded fix green; the completion-
   binding failure reproduced and disposed as defect fix or reasoned
   load-tolerance with evidence.
3. `rhel-surface-lanes`: the UBI 10 surface lane is green on the exact head
   and on a change that does not touch a surface path it does not run; the
   aarch64 parity lane reports its result without failing the pull request;
   the distribution profile records the lane image and platform truth.
4. Cutover ordering (owner-gated): merge the cutover PR, replace the
   required-context set once, verify the default-branch run is Linux-only,
   then close #315 as superseded.

## Engineering Profile overrides

Risk: **elevated** (public repository compatibility, CI migration, live
protection change). Delivery intent: **merge** (the protection edit and
default-branch verification are the owner's deployment step). Base profiles
under `docs/specs/*/PROFILE.md` otherwise stand; the distribution profile's
platform section is updated by `rhel-surface-lanes`.
