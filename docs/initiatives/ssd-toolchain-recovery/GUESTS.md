# Guest recovery, upgrades and fresh provisioning

Operator decision INT-024 defers all remaining guest work. The requirements and
failed-boot evidence below are retained, not completed or waived as passing.
Do not repair, upgrade, restart or freshly provision guests in the current scope.

Home: dotfiles_ai_distribution. Profile and Product Intent: matching PROFILE.md
and PRODUCT.md. Risk: elevated. Targets: the existing managed Fedora guests;
portable CentOS rendering remains a compatibility concern, not authorization to
upgrade an unregistered remote machine.

## Current source and baseline

Source: dot_local/bin/executable_sandbox-vm,
private_dot_config/dotfiles-ai/sandbox.json.tmpl, lima/workspace.yaml.tmpl under the
same directory, and guest tool/service installer templates. Existing authority:
tests/test_lima_sandbox.py plus affected distribution/native runtime tests.

Private recovery records show both guests execute V2 and Codex; personal mounts
were reconciled and Atuin/PostgreSQL active. Boot provisioning previously failed
on chezmoi conflicts. Mode-only drift was repaired; successful complete boot
provisioning and remaining content drift still need fresh proof.

## Behavior

| Given | When | Required outcome |
|---|---|---|
| Existing relocated VM disk | Guest boots | Disk, mounts and guest identities preserved; boundary marker present |
| Managed mount declarations | Native reconciliation runs | Exact host source and explicit guest mountPoint agree |
| Content drift | Provisioning compares source/deployed state | Classify before apply; no blanket force over unknown changes |
| Available guest package/tool updates | Maintenance runs | Local target updated, required services and development tools pass checks |
| Empty disposable guest | Current bootstrap runs | Working V2/native tool installation without old migration journal or preexisting admission |
| Repeated boot/apply | Provisioning reruns | Idempotent success with no noninteractive TTY conflict |
| Production-mounted repository | Guest is verified | No production files, locks, images or deployments changed |

## Contracts and validation

Separate guest OS packages, native OpenCode/Codex ownership, service containers and
project virtual environments in the inventory. Native updater lane owns tool
installer choice; Python lane owns project environment activation. No guest action
may update the host or copy host histories/credentials into guest state.

Use native Lima status/shell commands and inspect bounded cloud-init failures,
system/user failed services, mount identity, Git read-only roots and required
service health. Do not treat Lima READY alone as successful provisioning.
Exercise one full boot/provision cycle after reconciled content changes and a
second idempotence check. Fresh provisioning uses disposable state and verifies
native launch, configuration, external-state policy appropriate to that guest,
and no legacy migration prerequisite.

Preserve current disks/configuration and failed provisioning evidence for rollback;
do not overwrite them with a new template. Restarts already authorized but primary
serializes service interruption and verifies local PostgreSQL/Atuin afterward.
System-wide upgrades require a production-consumer check; uncertain coupling is a
hold, not a reason to cross the existing exclusion.

Kernel/review/deploy/operate/maintain required; release N/A. Before Build: exact
drift/consumer inventory, qualified native installation choice, fresh-machine
contract reconciled with original V2 distribution, committed applicability plan.
Existing boot repairs may proceed independently; installer activation depends on
native-tool-updates and shared writes must be serialized.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: host/guest/project ownership explicit |
| Interaction | required: boot/reconcile/reboot/idempotence ordering above |
| State | required: behavior table includes existing and empty guests |
| Data/trust | not_applicable: no cross-boundary credential/history transfer |
| Schema | not_applicable: existing Lima and chezmoi formats reused |
| Dependency/deployment | required: WORKSTREAMS.md activation table |
| Quantitative | not_applicable: no coverage count asserted |

**Text Equivalent:** existing guests retain disks and state; drift is classified
before apply, full boot succeeds and repeats cleanly. Empty guests must bootstrap
without migration evidence. Native-update ownership precedes installer changes.
Owner: distribution maintainer; canonical source: this contract; update on guest
support, installer or boundary changes.
