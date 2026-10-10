# SSD toolchain recovery and maintenance

## Approved ownership

The operator approved this context map on 2026-10-06. Dotfiles owns host tool
declarations and Python installation. Dotfiles-ai owns Herdr Host recovery,
guest provisioning, OpenCode preferences, hibernation qualification and V2
delivery. Each Python project owns its non-production dependency changes.
Coordinator Discovery inventories project-specific consumers before promoting
separate project slices; it does not own their implementation.

## Outcomes and constraints

Latest operator steering: finish host reliability investigation and bounded
migration-checkout cleanup. Hibernation, Python, guests and the other recorded
deferrals remain paused. Prepare [Host diagnostics](HOST-DIAGNOSTICS.md), but do
not implement or deploy without fresh readiness and exact-plan approval. Cache
release stopped after location re-creation; preserve referenced checkouts. See
[closure findings](findings/host-cleanup-closure.md) and the historical
[session focus](findings/current-session-focus.md).
INT-047 additionally selects [harness/Herdr independence](HARNESS-HERDR-INDEPENDENCE.md):
ordinary coding and lifecycle preflight do not depend on Herdr presentation or
Host metadata. Explicit recovery retains operation-specific preservation and pacing.
Preserve unfinished Host-promotion work; a permanent helper is not itself an
operator goal or a prerequisite for native executable migration.

- Restore relocated external state and exact conversations with existing layout.
  Preserve credentials, histories, migration archives, failed attempts and new V2
  work. Never restore an old database over current work.
- Intentional redundant PPC worktree DVC deletions remain intentional. Check
  metadata and links without full data pulls or cache garbage collection.
- All durable configuration and external-state routing use chezmoi. Native
  installers own OpenCode and Codex executable updates on the invoked platform.
  This supersedes the original custom-Codex-updater-only direction. Qualify the
  transition before retiring existing ownership; see [Native updates](NATIVE-UPDATES.md).
- Reconcile all installed managed packages/applications and guest tools, not just
  the tools named earlier. Updates are desired, but version output alone cannot
  establish data health; resolve retired declarations before any blanket apply.
- Preserve Python minor-version pins while updating patch releases. Exclude
  enterprise-seo-tools entirely and all production environments. SDS changes are
  limited to base/development environments; preserve GKE and shared production
  inputs. Use latest stable dependencies permitted by existing constraints,
  including allowed major versions. Resolve and exercise compatibility before activation.
- Configure browser MCP servers disconnected by default and manually connectable.
  Restore Tab next-agent and Shift+Tab previous-agent bindings using native V2 IDs.
- Hibernation is deferred under INT-041 after native coordination investigation;
  the operator declines changes to Herdr/OpenCode themselves for this feature now.
  Retain the OpenCode-only, fifteen-minute idle/unfocused, exact-session and
  working/focused/blocked exclusion requirements for resumption. Draft and exact
  scroll-position loss remain accepted. See [qualification](HIBERNATION.md).
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

## Complete session context coverage

| Scope | Detailed Discovery contract |
|---|---|
| Every installed managed package/application, shell/mise/uv and Python patch ownership | [Host tools](HOST-TOOLS.md) |
| State-root services, authentication, history, Git worktrees and intentional DVC omissions | [External state](EXTERNAL-STATE.md) |
| Signed Herdr Host replacement-volume registration and conversation preservation | [Herdr recovery](HERDR-RECOVERY.md) |
| Both managed guests, boot drift, upgrades and fresh V2 provisioning | [Guests](GUESTS.md) |
| Native OpenCode/Codex updates and chezmoi/external-state compatibility | [Native updates](NATIVE-UPDATES.md) |
| Non-production personal/client/tool/guest Python environments and SDS boundaries | [Python upgrades](PYTHON-UPGRADES.md) |
| Original V2 migration closure, preferences delivery and lifecycle/source reconciliation | [Delivery closure](DELIVERY-CLOSURE.md) |
| Deferred OpenCode hibernation, retained qualification and activation prerequisites | [Hibernation qualification](HIBERNATION.md) |

[Gates](GATES.md) records profile authorities and promotion gaps across all slices.
These contracts cover the full session scope; technical qualification still governs
which slices can become Build-ready. Hibernation is not a completion blocker for
the remaining non-deferred work.

## Validation

Use bounded read-only service/mount/runtime checks for recovery. For managed
configuration, review targeted rendered diffs, preserve unrelated settings and
validate resulting configuration. For Python, qualify isolated candidates with
dependency checks and affected runtime/tests before replacing environments.
Hibernation requires exact native-session restoration and state-eligibility
checks. Herdr Host needs signature, registration, volume identity and live probe
checks. Keep source qualification, deployment and operator UI evidence distinct.

## Resumption and delegation

[Workstreams](WORKSTREAMS.md) assigns research boundaries, required outputs,
deployment ordering and readiness gaps. User intent is settled; installer and
runtime qualification remain evidence tasks. Captured or discovering slices do
not authorize Build launch. The registered preferences cycle retains its imported
authority; this revision does not silently broaden that cycle.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: the approved ownership table in WORKSTREAMS.md is sufficient |
| Interaction | not_applicable: native-update validation ordering is explicit in NATIVE-UPDATES.md |
| State | required: readiness table in WORKSTREAMS.md |
| Data/trust | not_applicable: preservation constraints are explicit; no new transfer is authorized |
| Schema | not_applicable: existing Initiative manifest schema is reused |
| Dependency/deployment | required: dependency table in WORKSTREAMS.md |
| Quantitative | not_applicable: no measured comparison informs the ownership decision |
