# AI Workstation Distribution Slice

## Outcome

The AI source extends its standalone Linux model with a Fedora ARM64 workstation
role while retaining existing macOS, Lima guest, and remote-user-environment
behavior. The role owns only OpenCode, Codex CLI, Herdr, DBSCTR, and related
configuration.

## Contracts

- The workstation role is distinct from Lima `guest` and standalone remote-user
  roles and does not enable Lima provisioning, launchd, host services, Hermes,
  R&D scheduling, knowledge services, or database services by implication.
- Personal shell, terminal, Atuin, Git, SSH, desktop, package, and cache targets
  are ignored. Cross-source managed-target intersection is empty.
- OpenCode, Codex CLI, and Herdr use checksum-pinned official Fedora ARM64
  artifacts and wrappers that verify exact versions before execution.
- The configured state root is on the validated guest data mount. Its sentinel,
  ownership, mode, and atomic write probe must pass before AI state is used.
- OpenCode XDG data/state and Codex home are scoped by their wrappers rather than
  exported shell-wide. Managed config projection never owns auth or sessions.
- Herdr starts on demand and installs its OpenCode integration without a macOS
  LaunchAgent or speculative Linux service.
- OpenCode and Codex authenticate locally. Install, render, update, and rollback
  neither require nor copy credentials.
- Source rollback preserves private state. Incompatible state is retained under
  an operator-reviewed name before a fresh root is created; it is never deleted
  automatically.

## Concurrency

Do not launch while another active `dotfiles_ai_distribution` cycle owns the
workstation role discriminator, ignore rules, Linux installers, or distribution
tests. Reconcile that cycle first, then revalidate this slice's manifest digest.

## Validation

Run the complete AI repository suite, render all supported platforms, verify
Linux checksums and wrapper versions, prove zero personal-source target overlap,
exercise missing/safe/unsafe state roots, and smoke OpenCode, Codex CLI, Herdr,
and DBSCTR in the real Fedora workstation.
