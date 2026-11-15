# Omarchy Validation Pipeline

Discovery artifact for cycle `OST-002`. Extends the Omarchy attack-surface
toolchain (OST-001, `omarchy-security-toolchain.md`) from a static tool set
into a staged validation pipeline with a semantic router, a rootless lab lane,
and a reachability runtime. Machine-neutral and employer-neutral: target
identities, registers and drill evidence stay private and out of this source.

## Domain and Engineering Profile

Bounded context: `dotfiles_ai_distribution` (existing). Adjacent contexts: the
pinned security-toolkit runtime (owns SAST/secret/OSV scanners), the vendored
skill catalog (owns routing guidance), and operator-owned target estates
(enterprise environments and the personal homelab — target-only, never hosts).
Owner: project maintainers. Modules: Shell, Security, Python. Risk: elevated
(offensive tooling surface grows with radio/firmware/Android classes; a new
rootless container lab lane; an extended hash-locked runtime). Delivery intent:
draft pull request. Platform: the Omarchy (Arch Linux) fleet, x86_64 and
aarch64, per-machine opt-in through the existing default-off gate.

Ubiquitous language:

- **Validation pipeline** — ordered stages from static audit to private
  evidence: (1) static audit, (2) reachability proof, (3) local validation,
  (4) external probe, (5) evidence record.
- **Stage router** — `attack-surface-probe` guidance mapping intent to stage,
  tool, and install owner; the semantic layer. No second router skill.
- **Lab lane** — rootless podman on Omarchy running vulnerable targets (target
  repositories' compose stacks; `ubi9`/`ubi10` images for OS-package classes).
  Scanners never run inside the lab; containers are targets only.
- **Capability matrix** — per-stage table: intent → tool → install owner
  (pinned runtime | pacman/BlackArch | target repo) → degraded path.
- **Reachability runtime** — uv-managed, hash-locked generation beside
  Semgrep CE/Gitleaks/OSV-Scanner owning Python reachability tooling
  (pip-audit class; CodeQL deferred pending license review).
- **Escape hatch** — recorded fallback for full-OS/kernel-level targets:
  extend the existing Lima guest pattern; Incus is explicitly rejected.

Trust boundaries: public source → Omarchy host (existing gate + strap pin
unchanged); lab lane → host (rootless, user-namespaced, no host mounts, no
lab systemd units); pinned runtime generations → global environment (existing
runtime.md ownership rules); evidence → private storage only (registers and
drill reports live in operator sessions, never in this repository).

## Behavior

- Given a static finding needing validation, the stage router names the stage,
  candidate tools, their install owners, and the degraded path when a tool is
  absent; it never installs anything.
- Given stage 3, guidance selects the lab lane: the target's own compose
  stack or a UBI image; no capability flags are added to lab containers
  because containers are targets, not scanners.
- Given stage 4, guidance requires explicit per-target authorization and the
  existing default-deny rules; enterprise estates are reachable targets only.
- Given a tool absent from the host, the capability matrix routes to its owner:
  pacman/BlackArch for the curated set, the pinned runtime for Python
  reachability, or the target repository for lab stacks — reported as a gap,
  never auto-repaired.
- Given the curated-list change, installable membership is verified on both
  architectures before landing; tools absent from repositories move to the
  pinned runtime instead of the pacman list.
- Given any pipeline activity, findings and raw output flow to private
  evidence; nothing in this source names targets, employers, or registers.

## Interfaces and Contracts

Curated pacman list extension (all dual-arch verified at build; absent
members move to the reachability runtime):

| Class | Packages |
|---|---|
| Personal — WiFi/LAN | aircrack-ng, bettercap |
| Personal — firmware/IoT | binwalk, mitmproxy |
| Personal — Android | android-tools, apktool |
| Work — k8s audit | kube-bench, kube-hunter |
| Work — supply chain | cosign, checkov |
| Lab lane | podman, podman-compose |

Pipeline module: `attack-surface-probe/references/pipeline.md` — stage model,
capability matrix, lab patterns (`podman compose`, `podman run ubi9`), Lima
escape-hatch note. `security-toolkit/references/routing.md` gains the
validation-stage rows; no new router skill is introduced.

Reachability runtime: security-toolkit `runtime.md` profile gains a
hash-locked generation (uv, binary-only, metrics/version policy per existing
rules); update flow follows the existing generation conventions with prior
generations preserved.

Invariants: the gate stays default-off on every host and nothing
auto-installs; docker (Omarchy-owned) is untouched; no Incus anywhere; the
pinned scanners keep exclusive ownership of Semgrep CE/Gitleaks/OSV-Scanner;
no drills, reports, or target evidence in this cycle — environment setup only.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: stage/ownership table below |
| Interaction | required: ordered stage transitions below |
| State | required: capability presence states below |
| Data/trust | required: trust boundaries above and evidence flow below |
| Schema | not_applicable: flat guidance/config inventory; no persistent relational domain |
| Dependency/deployment | required: install-owner columns above |
| Quantitative | not_applicable: no threshold or trend decision |

| Stage | Owner/prerequisite | Result and trust boundary |
|---|---|---|
| 1 Static audit | Pinned runtime (existing) | Findings in private evidence; no target contact |
| 2 Reachability proof | Reachability runtime + manual trace | Reachability claim becomes verified or refuted |
| 3 Local validation | Lab lane: rootless podman, target stack/UBI | PoC outcome confined to user-namespaced containers |
| 4 External probe | Curated set + explicit per-target authorization | Default-deny; enterprise estate target-only |
| 5 Evidence record | Operator session; register row update | Private; never this repository |

**Text Equivalent:** Static findings flow through a five-stage pipeline owned
by guidance artifacts rather than code. Stages 1–2 run inside the pinned
runtimes; stage 3 confines vulnerable software to rootless lab containers that
are targets only; stage 4 fires curated tools at explicitly authorized targets;
stage 5 writes private evidence. Absent capabilities route to their install
owner and are reported, never auto-installed. Canonical sources: this spec,
the toolchain feature doc, the pipeline module, and the runtime profile.
Owner: project maintainers; refresh when stage semantics, tool ownership, or
authorization rules change.

## Non-Goals

Incus or any full-OS container daemon (Lima extension is the recorded escape
hatch); drills, drill reports, or any target evidence in this source; hosting
tooling inside enterprise estates; GUI plumbing; a second router skill;
CodeQL adoption (deferred, separate license review); auto-update of images or
the BlackArch base.

## Validation and Completion

Authorities: `pytest` (list membership, dual-arch render gating, config
defaults, skill delivery), `bash -n` rendered variants, the skill validator,
and the repository's public-content authority for the new guidance files.
Build-time availability verification: every candidate package checked on both
architectures via the official package APIs; absentees relocate to the
reachability runtime with the decision recorded. No host enablement,
installation, scan, or drill runs inside the cycle; per-machine enablement is
a separate operator action. Implementation readiness holds: every material
scope, interface, risk, and validation question was resolved in operator
interviews (2026-11-15) and is encoded above.
