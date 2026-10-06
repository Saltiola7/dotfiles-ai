# SSD toolchain recovery and maintenance

## Approved ownership

The operator approved this context map on 2026-10-06. Dotfiles owns host tool
declarations and Python installation. Dotfiles-ai owns Herdr Host recovery,
guest provisioning, OpenCode preferences, hibernation qualification and V2
delivery. Each Python project owns its non-production dependency changes.
Coordinator Discovery inventories project-specific consumers before promoting
separate project slices; it does not own their implementation.

## Outcomes and constraints

- Restore relocated external state and exact conversations with existing layout.
  Preserve credentials, histories, migration archives, failed attempts and new V2
  work. Never restore an old database over current work.
- Intentional redundant PPC worktree DVC deletions remain intentional. Check
  metadata and links without full data pulls or cache garbage collection.
- All durable machine setup uses chezmoi. Codex uses its existing custom updater
  exclusively; remove redundant installations only after verifying ownership.
- Reconcile host and guest tools, including Kitty, Lima, Python and 1Password.
  Updates are permitted, but version output alone cannot establish data health.
- Preserve Python minor-version pins while updating patch releases. Exclude
  enterprise-seo-tools entirely and all production environments. SDS changes are
  limited to base/development environments; preserve GKE and shared production
  inputs. Resolve and exercise package compatibility before activation.
- Configure browser MCP servers disconnected by default and manually connectable.
  Restore Tab next-agent and Shift+Tab previous-agent bindings using native V2 IDs.
- Prefer official Herdr integration and an existing hibernation implementation.
  Hibernate only OpenCode after fifteen minutes idle and unfocused. Never suspend
  working, focused or blocked sessions. Draft and exact scroll-position loss are
  accepted; loss of exact conversation identity is not accepted.
- Restarts are authorized with recovery evidence. Permission boundaries remain
  enforced; configured-deny changes require explicit operator approval.
- Complete the existing V2 delivery under its original Initiative and cycle.
  This Initiative does not duplicate or broaden that registered slice. Fresh V2
  provisioning requires reopened Discovery; migration evidence is not bootstrap
  evidence. Never rerun the completed host migration controller.

## Evidence and remaining readiness

Private operational evidence remains outside Git. Recovery verified all original
conversation identities in their original panes. Host uv lookup and a stale
personal-guest repository mount were reconciled. Both guests execute admitted V2
and managed Codex. These checks do not establish whole-toolchain completion.

Remaining questions are technical qualification, not missing user intent:
safe signed Herdr Host replacement; guest content drift and boot provisioning;
external service/state coverage; Python production-consumer classification;
hibernation exact-session recovery; and fresh-machine V2 admission.

The OpenCode preferences slice has a behavior contract, Engineering Profile and
validation plan; its launch feasibility remains subject to native preflight.
Other slices remain Discovery-owned. No launch receipt is implied by this scope
map. Existing contexts are reused; project-specific Python slices
must reference each owning repository before implementation.

## Validation

Use bounded read-only service/mount/runtime checks for recovery. For managed
configuration, review targeted rendered diffs, preserve unrelated settings and
validate resulting configuration. For Python, qualify isolated candidates with
dependency checks and affected runtime/tests before replacing environments.
Hibernation requires exact native-session restoration and state-eligibility
checks. Herdr Host needs signature, registration, volume identity and live probe
checks. Keep source qualification, deployment and operator UI evidence distinct.
